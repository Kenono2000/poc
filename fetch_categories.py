import urllib.request
import ssl

url = "https://www.idisciple.org/categories"
req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    },
)
ctx = ssl.create_default_context()
with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
    html = resp.read().decode("utf-8", errors="replace")

with open(r"C:\src\poc\categories.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Fetched", len(html), "chars")
