#!/usr/bin/env python3
"""Scrape all articles from an iDisciple category.

Given a category URL such as
    https://www.idisciple.org/categories/integrity-and-character
this script:
  1. Resolves the category through the site's public Umbraco Delivery API
  2. Pages through every article in that category
  3. Scrapes the full content (title, body, author) from each article page
  4. Outputs structured JSON with all scraped content

Usage:
    python idisciple_category_scraper.py <category_url> [options]

    <category_url>   e.g. https://www.idisciple.org/categories/integrity-and-character

Options:
    -o, --output     output JSON file path (default: idisciple_category_scraped.json)
    --out-dir        output directory for individual article JSON files
    --history        path to JSON history file to track scraped URLs (enables resume)
    --limit          optional max number of articles to scrape
    --delay          delay between article requests in seconds (default: 0.5)
    --force          re-scrape URLs even if they exist in history

Transport:
    The site sits behind bot protection that fingerprints TLS. Some Python
    builds (e.g. 3.11) get HTTP 403 from the standard library, while others
    pass. This script therefore tries two HTTP transports, in order:
      1. curl_cffi (impersonate="chrome")  -- if installed; most reliable
      2. urllib (standard library)         -- no dependencies
    If urllib works for your Python, no extra install is needed. If you hit
    HTTP 403, install curl_cffi (pip install curl_cffi) and rerun.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional, but the most reliable transport against this site's bot protection
try:
    from curl_cffi import requests as _cffi_requests
except ImportError:  # pragma: no cover - environment dependent
    _cffi_requests = None

# BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: BeautifulSoup4 is required. Install with: pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)

API_PATH = "/umbraco/delivery/api/v2/content"
PAGE_SIZE = 100  # items per API request
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# HTML scraping constants
MIN_BODY_CHARS = 80
BANNED_CLASS_PARTS = ("nav", "footer", "header", "aside", "sidebar", "related", "breadcrumb", "ad")
BANNED_TAGS = ("nav", "footer", "header", "aside")


def parse_category_url(url: str) -> tuple[str, str, str]:
    """Return (base_origin, locale, slug) from a category URL.

    Supports:
        https://www.idisciple.org/categories/integrity-and-character
        https://www.idisciple.org/es/categories/integridad-y-caracter
        https://www.idisciple.org/categories/integrity-and-character/page/3
    """
    parsed = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    parts = [p for p in parsed.path.split("/") if p]

    locale = "en-US"
    if parts and parts[0] == "es":
        locale = "es"
        parts = parts[1:]

    if not parts or parts[0] != "categories" or len(parts) < 2:
        raise ValueError(
            f"Not a category URL: {url!r}\n"
            "Expected something like https://www.idisciple.org/categories/<slug>"
        )

    slug = parts[1]
    base = f"{parsed.scheme}://{parsed.netloc}"
    return base, locale, slug


class ApiClient:
    """Client for the Umbraco Delivery API with transport fallback."""

    def __init__(self, base: str, locale: str = "en-US", retries: int = 3):
        self.base = base.rstrip("/")
        self.locale = locale
        self.retries = retries
        self.ctx = ssl.create_default_context()
        # Resolved lazily on the first request: "curl_cffi" or "urllib".
        self._transport: str | None = None

    def _headers(self) -> dict:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.locale != "en-US":
            headers["Accept-Language"] = self.locale
        return headers

    def _fetch_curl_cffi(self, url: str) -> bytes:
        resp = _cffi_requests.get(
            url,
            headers=self._headers(),
            impersonate="chrome",
            timeout=30,
        )
        if resp.status_code >= 400:
            raise urllib.error.HTTPError(url, resp.status_code, resp.reason, resp.headers, None)
        return resp.content

    def _fetch_urllib(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=30, context=self.ctx) as resp:
            return resp.read()

    def _fetch(self, url: str) -> bytes:
        """Fetch bytes, choosing once between curl_cffi and urllib.

        Preference order: curl_cffi (if installed) -> urllib. If the chosen
        transport is rejected with HTTP 403 (TLS fingerprint block), fall back
        to the other one and remember the working transport for the session.
        """
        order = []
        if self._transport:
            order = [self._transport]
        elif _cffi_requests is not None:
            order = ["curl_cffi", "urllib"]
        else:
            order = ["urllib"]

        last_err: Exception | None = None
        for name in order:
            if name == "curl_cffi" and _cffi_requests is None:
                continue
            try:
                data = self._fetch_curl_cffi(url) if name == "curl_cffi" else self._fetch_urllib(url)
            except urllib.error.HTTPError as exc:
                last_err = exc
                if exc.code == 403 and self._transport is None and len(order) > 1:
                    continue  # fingerprinted; try the other transport
                raise
            self._transport = name
            return data
        raise last_err if last_err else RuntimeError("no HTTP transport available")

    def get_content(self, filters: list[str], take: int, skip: int = 0) -> dict:
        params = [("filter", f) for f in filters]
        params += [("take", str(take)), ("skip", str(skip))]
        url = f"{self.base}{API_PATH}?{urllib.parse.urlencode(params)}"

        last_err: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                raw = self._fetch(url)
                return json.loads(raw.decode("utf-8", "replace"))
            except urllib.error.HTTPError as exc:
                # 4xx (other than a fingerprint 403 already handled) won't heal by retrying
                if exc.code != 403 or self._transport is not None:
                    raise RuntimeError(f"API request failed: {url}\nHTTP {exc.code}: {exc.reason}")
                last_err = exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_err = exc
            if attempt < self.retries:
                time.sleep(1.5 * attempt)
        raise RuntimeError(
            f"API request failed after {self.retries} attempts: {url}\n{last_err}\n"
            "Hint: the site may be blocking your Python's TLS fingerprint (HTTP 403). "
            "Install curl_cffi (pip install curl_cffi) and rerun."
        )


class ArticleScraper:
    """Scrapes individual article pages for content."""

    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from a URL."""
        if _cffi_requests is not None:
            resp = _cffi_requests.get(
                url,
                headers=self.session_headers,
                impersonate="chrome",
                timeout=30,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.reason}")
            return resp.text
        else:
            req = urllib.request.Request(url, headers=self.session_headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")

    def _clean_text(self, value: str) -> str:
        """Collapse whitespace and strip stray newlines."""
        lines = [re.sub(r"\s+", " ", line).strip() for line in value.split("\n")]
        return "\n".join(line for line in lines if line)

    def _extract_title(self, soup: BeautifulSoup) -> str:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
            if title:
                return title
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return og["content"]
        tag = soup.find("title")
        if tag:
            return tag.get_text(strip=True)
        return ""

    def _contains_banned(self, el: BeautifulSoup) -> bool:
        stack = [el]
        while stack:
            node = stack.pop()
            if node.name is not None and str(node.name).lower() in BANNED_TAGS:
                return True
            classes = " ".join(node.get("class") or []).lower()
            if any(part in classes for part in BANNED_CLASS_PARTS):
                return True
            stack.extend(node.find_all(True))
        return False

    def _extract_body(self, soup: BeautifulSoup) -> str:
        article = soup.find("article")
        if article is not None and len(self._clean_text(article.get_text(separator="\n", strip=True))) >= MIN_BODY_CHARS:
            for unwanted in article.find_all(["script", "style", "noscript", "svg", "iframe"]):
                unwanted.decompose()
            return self._clean_text(article.get_text(separator="\n", strip=True))

        main = soup.find("main")
        if main is not None and len(self._clean_text(main.get_text(separator="\n", strip=True))) >= MIN_BODY_CHARS:
            for unwanted in main.find_all(["script", "style", "noscript", "svg", "iframe"]):
                unwanted.decompose()
            return self._clean_text(main.get_text(separator="\n", strip=True))

        best: Optional[BeautifulSoup] = None
        best_text = ""
        for el in soup.find_all(["div", "section", "article", "main"]):
            if self._contains_banned(el):
                continue
            for unwanted in el.find_all(["script", "style", "noscript", "svg", "iframe"]):
                unwanted.decompose()
            text = self._clean_text(el.get_text(separator="\n", strip=True))
            if len(text) > len(best_text):
                best, best_text = el, text
        if best is not None and len(best_text) >= MIN_BODY_CHARS:
            return best_text
        return best_text

    def _extract_author(self, soup: BeautifulSoup, body: str) -> str:
        author = ""
        author_tag = soup.find("meta", attrs={"name": "author"})
        if author_tag and author_tag.get("content"):
            author = author_tag["content"].strip()
        if not author:
            match = re.search(r"Written by[:\-]?\s+(.+)", body, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
        return author

    def scrape_article(self, article_url: str) -> Dict[str, Any]:
        """Scrape a single iDisciple content page and return structured fields."""
        html = self._fetch_html(article_url)
        soup = BeautifulSoup(html, "html.parser")
        title = self._extract_title(soup)
        body = self._extract_body(soup)
        author = self._extract_author(soup, body)
        return {"url": article_url, "title": title, "body": body, "author": author}


def get_category(client: ApiClient, slug: str) -> dict:
    """Fetch category metadata from the API."""
    data = client.get_content(
        filters=["contentType:iDiscipleCategory", f"contentSlug:{slug}"],
        take=1,
    )
    items = data.get("items") or []
    if not items:
        raise RuntimeError(f"Category not found for slug: {slug!r}")
    return items[0]


def load_history(path: str) -> set:
    """Load previously scraped URLs from a JSON history file."""
    history_path = Path(path)
    if not history_path.exists():
        return set()
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        urls = data.get("urls") if isinstance(data, dict) else data
        if isinstance(urls, list):
            return {u for u in urls if isinstance(u, str)}
    except Exception:
        return set()
    return set()


def save_history(urls: set, path: str) -> None:
    """Persist scraped URLs to a JSON history file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"urls": sorted(urls)}, indent=2), encoding="utf-8")


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Convert a string to a safe filename."""
    # Remove or replace invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '', name)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe.strip('._')
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('._')
    return safe or "untitled"


def iter_article_urls(client: ApiClient, category_id: str, limit: int | None = None):
    """Yield (url, title) for every article in the category, paging the API."""
    skip = 0
    seen: set[str] = set()
    total = None

    while True:
        take = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - len(seen))
        if take <= 0:
            return

        data = client.get_content(
            filters=["contentType:iDiscipleArticle", f"category:{category_id}"],
            take=take,
            skip=skip,
        )
        total = data.get("total", total)
        items = data.get("items") or []
        if not items:
            return

        new = 0
        for item in items:
            path = (item.get("route") or {}).get("path") or ""
            if not path.startswith("/articles/"):
                continue
            url = client.base + path
            if url in seen:
                continue
            seen.add(url)
            new += 1
            yield url, item.get("name") or ""
            if limit is not None and len(seen) >= limit:
                return

        skip += len(items)
        if total is not None and skip >= total:
            return
        if new == 0:  # safety: no progress, avoid infinite loop
            return


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape all articles from an iDisciple category.",
    )
    parser.add_argument("category_url", help="e.g. https://www.idisciple.org/categories/integrity-and-character")
    parser.add_argument("-o", "--output", default=None,
                        help="Output JSON file path for combined results (default: <category_slug>_scraped.json)")
    parser.add_argument("--out-dir", default=None,
                        help="Output directory for individual article JSON files")
    parser.add_argument("--history", default=None,
                        help="Path to JSON history file to track scraped URLs (enables resume)")
    parser.add_argument("--limit", type=int, default=None, help="Max number of articles to scrape")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Delay between article requests in seconds (default: 0.5)")
    parser.add_argument("--force", action="store_true",
                        help="Re-scrape URLs even if they exist in history")
    args = parser.parse_args()

    try:
        base, locale, slug = parse_category_url(args.category_url)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    # Set default output filename based on category slug if not specified
    if args.output is None:
        args.output = f"{slug}_scraped.json"

    client = ApiClient(base, locale)
    scraper = ArticleScraper(delay=args.delay)

    # Load history if specified
    history: set = set()
    if args.history:
        history = load_history(args.history)
        if history:
            print(f"Loaded {len(history)} URLs from history file.", file=sys.stderr)

    try:
        category = get_category(client, slug)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    category_name = category.get("name", "Unknown")
    print(f"Category: {category_name}  (slug: {slug}, locale: {locale})", file=sys.stderr)

    # Collect article URLs
    all_article_urls = list(iter_article_urls(client, category["id"], args.limit))
    print(f"Found {len(all_article_urls)} article(s) in category.", file=sys.stderr)

    # Filter out already-scraped URLs if history is enabled
    if args.history and not args.force:
        article_urls = [(url, title) for url, title in all_article_urls if url not in history]
        skipped = len(all_article_urls) - len(article_urls)
        if skipped > 0:
            print(f"Skipping {skipped} already-scraped article(s).", file=sys.stderr)
    else:
        article_urls = all_article_urls

    if not article_urls:
        print("No new articles to scrape.", file=sys.stderr)
        return 0

    print(f"Scraping {len(article_urls)} article(s)...", file=sys.stderr)

    # Prepare output directory if specified
    out_dir: Optional[Path] = None
    if args.out_dir:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Individual articles will be saved to: {out_dir}", file=sys.stderr)

    # Scrape each article
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    newly_scraped: set = set()

    for i, (url, api_title) in enumerate(article_urls, 1):
        print(f"[{i}/{len(article_urls)}] Scraping: {url}", file=sys.stderr)
        try:
            data = scraper.scrape_article(url)
            # Use API title as fallback if scraping didn't find a title
            if not data["title"] and api_title:
                data["title"] = api_title
            results.append(data)
            newly_scraped.add(url)

            # Save individual article file if out-dir is specified
            if out_dir:
                filename = sanitize_filename(data["title"]) + ".json"
                article_path = out_dir / filename
                # Handle filename collisions
                counter = 1
                while article_path.exists():
                    filename = f"{sanitize_filename(data['title'])}_{counter}.json"
                    article_path = out_dir / filename
                    counter += 1
                article_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

            title_display = data['title'][:60] + "..." if len(data['title']) > 60 else data['title']
            print(f"  OK: {title_display}", file=sys.stderr)
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            print(f"  ERR: {exc}", file=sys.stderr)

        # Rate limiting
        if i < len(article_urls):
            time.sleep(args.delay)

    # Update history
    if args.history:
        history.update(newly_scraped)
        save_history(history, args.history)
        print(f"Updated history file: {args.history} ({len(history)} total URLs)", file=sys.stderr)

    # Write combined output
    output_data = {
        "category": {
            "name": category_name,
            "slug": slug,
            "locale": locale,
            "url": args.category_url,
        },
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_articles": len(results),
        "total_errors": len(errors),
        "articles": results,
        "errors": errors,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nScraped {len(results)} articles, {len(errors)} errors -> {args.output}", file=sys.stderr)
    if out_dir:
        print(f"Individual article files saved to: {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
