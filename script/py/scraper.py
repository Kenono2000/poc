"""iDisciple content scraper.

Fetches content (articles / devotionals / growth plans) published on
https://www.idisciple.org and extracts structured content (title, body, author).

Notes:
- The site is built on Nuxt.js (SPA shell). The content pages we target are
  server-rendered, so plain `requests` + `BeautifulSoup` works.
- If a page comes back with an empty body, use the backend API or a browser driver.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SITE_URL = "https://www.idisciple.org"
API_BASE = "https://api.idisciple.org"
DEFAULT_HISTORY_FILE = r"C:\src\poc\script\py\idisciple_history.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
REQUEST_DELAY_SECONDS = 0.5

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=MAX_RETRIES, backoff_factor=1.0, status_forcelist=list(RETRY_STATUS_CODES)
        )
    ),
)
SESSION.mount(
    "http://",
    HTTPAdapter(
        max_retries=Retry(
            total=MAX_RETRIES, backoff_factor=1.0, status_forcelist=list(RETRY_STATUS_CODES)
        )
    ),
)

MIN_BODY_CHARS = 80
BANNED_CLASS_PARTS = ("nav", "footer", "header", "aside", "sidebar", "related", "breadcrumb", "ad")
BANNED_TAGS = ("nav", "footer", "header", "aside")


def _fetch(url: str) -> str:
    """GET a URL with retries/timeouts; raise on final failure."""
    resp = SESSION.get(url, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.text


def _clean_text(value: str) -> str:
    """Collapse whitespace and strip stray newlines."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.split("\n")]
    return "\n".join(line for line in lines if line)


def _extract_title(soup: BeautifulSoup) -> str:
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


def _contains_banned(el: BeautifulSoup) -> bool:
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


def _extract_body(soup: BeautifulSoup) -> str:
    article = soup.find("article")
    if article is not None and len(_clean_text(article.get_text(separator="\n", strip=True))) >= MIN_BODY_CHARS:
        for unwanted in article.find_all(["script", "style", "noscript", "svg", "iframe"]):
            unwanted.decompose()
        return _clean_text(article.get_text(separator="\n", strip=True))

    main = soup.find("main")
    if main is not None and len(_clean_text(main.get_text(separator="\n", strip=True))) >= MIN_BODY_CHARS:
        for unwanted in main.find_all(["script", "style", "noscript", "svg", "iframe"]):
            unwanted.decompose()
        return _clean_text(main.get_text(separator="\n", strip=True))

    best: Optional[BeautifulSoup] = None
    best_text = ""
    for el in soup.find_all(["div", "section", "article", "main"]):
        if _contains_banned(el):
            continue
        for unwanted in el.find_all(["script", "style", "noscript", "svg", "iframe"]):
            unwanted.decompose()
        text = _clean_text(el.get_text(separator="\n", strip=True))
        if len(text) > len(best_text):
            best, best_text = el, text
    if best is not None and len(best_text) >= MIN_BODY_CHARS:
        return best_text
    return best_text


def _extract_author(soup: BeautifulSoup, body: str) -> str:
    author = ""
    author_tag = soup.find("meta", attrs={"name": "author"})
    if author_tag and author_tag.get("content"):
        author = author_tag["content"].strip()
    if not author:
        match = re.search(r"Written by[:\-]?\s+(.+)", body, re.IGNORECASE)
        if match:
            author = match.group(1).strip()
    return author


def scrape_article(article_url: str) -> Dict[str, Any]:
    """Scrape a single iDisciple content page and return structured fields."""
    html = _fetch(article_url)
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    body = _extract_body(soup)
    author = _extract_author(soup, body)
    return {"url": article_url, "title": title, "body": body, "author": author}


def load_history(path: str = DEFAULT_HISTORY_FILE) -> set:
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


def save_history(urls: List[str], path: str = DEFAULT_HISTORY_FILE) -> None:
    """Persist scraped URLs to a JSON history file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"urls": sorted(set(urls))}, indent=2), encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape iDisciple content.")
    parser.add_argument("--urls", nargs="*", help="Full content URLs to scrape.")
    parser.add_argument("--limit", type=int, default=None, help="Max items per run.")
    parser.add_argument("--out", default="idisciple_scraped.json")
    parser.add_argument("--history", default=DEFAULT_HISTORY_FILE, help="Path to JSON history file of scraped URLs.")
    args = parser.parse_args(argv)

    history = load_history(args.history)
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    processed = 0

    if args.urls:
        urls = [u if u.startswith("http") else f"{SITE_URL}/{u.strip('/')}/" for u in args.urls]
        for url in urls:
            if args.limit is not None and processed >= args.limit:
                break
            if url in history:
                print(f"SKIP: {url} (already scraped, found in history)")
                continue
            processed += 1
            try:
                data = scrape_article(url)
                results.append(data)
                print(f"OK: {url} :: {data.get('title')}")
            except Exception as exc:
                errors.append({"url": url, "error": str(exc)})
                print(f"ERR: {url} :: {exc}")
            time.sleep(REQUEST_DELAY_SECONDS)

    scraped_urls = [r.get("url") for r in results if r.get("url")]
    history.update(scraped_urls)
    save_history(sorted(history), args.history)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"scraped": results, "errors": errors}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Scraped {len(results)} items -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
