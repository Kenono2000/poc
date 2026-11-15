import json, re, unicodedata

with open(r"C:\src\poc\nuxt_data.json", "r", encoding="utf-8") as f:
    flat = json.load(f)

cat_list = flat[173]
print("total category entries:", len(cat_list))

def slugify(name: str) -> str:
    # normalize unicode, lowercase, replace spaces with dash
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)   # any non-alphanumeric -> dash (covers spaces, /, &, parens)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s

rows = []
for idx in cat_list:
    item = flat[idx]
    if not isinstance(item, dict) or "name" not in item:
        continue
    name = flat[item["name"]]
    route = flat[item["route"]]
    path = flat[route["path"]] if isinstance(route, dict) and isinstance(route.get("path"), int) else (route.get("path") if isinstance(route, dict) else None)
    rows.append((name, path))

# English entries are those whose route path ends with '/' (English slugs have trailing slash per payload observation)
# Spanish ones lack the trailing slash. Verify:
en = [(n, p) for n, p in rows if isinstance(p, str) and p.endswith("/")]
es = [(n, p) for n, p in rows if isinstance(p, str) and not p.endswith("/")]
print("English-style (trailing slash):", len(en))
print("Spanish-style (no trailing slash):", len(es))

print("\n--- ALL entries (name -> slugified) ---")
for n, p in rows:
    print(f"{n}  |  {slugify(n)}  |  {p}")

with open(r"C:\src\poc\categories_all.txt", "w", encoding="utf-8") as f:
    for n, p in rows:
        f.write(f"{n}\t{slugify(n)}\t{p}\n")
