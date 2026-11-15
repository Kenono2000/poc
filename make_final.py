import json, re, unicodedata

with open(r"C:\src\poc\nuxt_data.json", "r", encoding="utf-8") as f:
    flat = json.load(f)

def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace(" ", "-")
    return s

slugs = []
for idx in flat[173]:
    item = flat[idx]
    if isinstance(item, dict) and "name" in item:
        slugs.append(slugify(flat[item["name"]]))

with open(r"C:\src\poc\category_slugs.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(slugs) + "\n")

print(f"{len(slugs)} slugs written to category_slugs.txt")
