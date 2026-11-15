"""Run idisciple_category_articles logic for every category and filter out empties.

Uses the script's own ApiClient/get_category/iter_article_urls (imported as a
module) so behavior matches running the script per category, but in one
process. Site slugs come from categories_all.txt (the site's own route paths).
"""
import importlib.util
import re
import sys
import time

spec = importlib.util.spec_from_file_location(
    "ica", r"C:\src\poc\script\py\idisciple_category_articles.py"
)
ica = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ica)

BASE = "https://www.idisciple.org"

# Load true site slugs from the route paths captured earlier
cats = []  # (name, slug)
with open(r"C:\src\poc\categories_all.txt", encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 3:
            continue
        name, _slug, path = parts
        m = re.match(r"^/configurations/categories/(.+)/$", path)
        if m:
            cats.append((name, m.group(1)))

print(f"Loaded {len(cats)} categories", file=sys.stderr)

client = ica.ApiClient(BASE, "en-US")

results = []  # (name, slug, count)
empty = []
errors = []

for i, (name, slug) in enumerate(cats, 1):
    last_seg = slug.split("/")[-1]  # leaf slug is what contentSlug matches
    try:
        category = ica.get_category(client, last_seg)
        # limit=1: we only need to know whether the category has any articles
        n = sum(1 for _ in ica.iter_article_urls(client, category["id"], limit=1))
        # If we found one, get the real count without limit for reporting? Too slow.
        results.append((name, slug, n))
        status = "HAS ARTICLES" if n > 0 else "EMPTY"
    except Exception as exc:
        errors.append((name, slug, str(exc)[:120]))
        results.append((name, slug, -1))
        status = f"ERROR: {str(exc)[:80]}"
    print(f"[{i:3}/{len(cats)}] {name:<45} {status}", file=sys.stderr)
    time.sleep(0.15)  # be polite

with open(r"C:\src\poc\category_check_results.tsv", "w", encoding="utf-8") as f:
    f.write("name\tslug\thas_articles\n")
    for name, slug, n in results:
        f.write(f"{name}\t{slug}\t{n}\n")

has = [(n, s) for n, s, c in results if c > 0]
none = [(n, s) for n, s, c in results if c == 0]
err = [(n, s) for n, s, c in results if c < 0]

print("\n==== SUMMARY ====")
print(f"total: {len(results)}  has-articles: {len(has)}  empty: {len(none)}  errors: {len(err)}")
print("\n---- CATEGORIES WITH ARTICLES ----")
for n, s in has:
    print(f"{n}\t{s}")
print("\n---- EMPTY CATEGORIES (filtered out) ----")
for n, s in none:
    print(f"{n}\t{s}")
if err:
    print("\n---- ERRORS ----")
    for n, s in err:
        print(f"{n}\t{s}")
