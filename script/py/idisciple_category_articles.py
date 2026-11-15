#!/usr/bin/env python3
"""List all article URLs for an iDisciple category.

Given a category URL such as
    https://www.idisciple.org/categories/integrity-and-character
this script resolves the category through the site's public Umbraco
Delivery API (the same API the website itself uses), then pages through
every article in that category and prints the full article URLs, e.g.
    https://www.idisciple.org/articles/needing-a-pat-on-the-back/

Usage:
    python idisciple_category_articles.py <category_url> [-o OUTPUT] [--limit N]

    <category_url>   e.g. https://www.idisciple.org/categories/integrity-and-character
    -o, --output     optional file path (.txt or .csv) to write the URLs to
    --limit          optional max number of article URLs to collect

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
import csv
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_PATH = "/umbraco/delivery/api/v2/content"
PAGE_SIZE = 100  # items per API request
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

try:  # optional, but the most reliable transport against this site's bot protection
    from curl_cffi import requests as _cffi_requests
except ImportError:  # pragma: no cover - environment dependent
    _cffi_requests = None


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


def get_category(client: ApiClient, slug: str) -> dict:
    data = client.get_content(
        filters=["contentType:iDiscipleCategory", f"contentSlug:{slug}"],
        take=1,
    )
    items = data.get("items") or []
    if not items:
        raise RuntimeError(f"Category not found for slug: {slug!r}")
    return items[0]


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
        description="List all article URLs for an iDisciple category URL.",
    )
    parser.add_argument("category_url", help="e.g. https://www.idisciple.org/categories/integrity-and-character")
    parser.add_argument("-o", "--output", help="Optional output file (.txt or .csv)")
    parser.add_argument("--limit", type=int, default=None, help="Max number of article URLs to collect")
    args = parser.parse_args()

    try:
        base, locale, slug = parse_category_url(args.category_url)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    client = ApiClient(base, locale)

    try:
        category = get_category(client, slug)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Category: {category.get('name')}  (slug: {slug}, locale: {locale})", file=sys.stderr)

    results = list(iter_article_urls(client, category["id"], args.limit))
    print(f"Found {len(results)} article(s).", file=sys.stderr)

    if args.output:
        if args.output.lower().endswith(".csv"):
            with open(args.output, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["url", "title"])
                writer.writerows(results)
        else:
            with open(args.output, "w", encoding="utf-8") as fh:
                for url, _ in results:
                    fh.write(url + "\n")
        print(f"Wrote {len(results)} URL(s) to {args.output}", file=sys.stderr)
    else:
        for url, _ in results:
            print(url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
