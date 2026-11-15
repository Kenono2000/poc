import urllib.request
import re

with open('debug_categories.json', 'r', encoding='utf-8') as f:
    text = f.read()

urls = re.findall(r'https?://[^\s\"<>]+', text)
for u in sorted(set(urls)):
    if any(k in u for k in ['api', 'article', 'content', 'graphql', 'json', 'idisciple']):
        print(u)
