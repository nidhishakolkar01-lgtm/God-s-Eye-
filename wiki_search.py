import urllib.request, json

queries = ["border fence", "border crossing", "checkpoint", "military patrol", "border security", "surveillance camera"]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for q in queries:
    url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={urllib.parse.quote(q)}+filetype:video&gsrlimit=5&prop=imageinfo&iiprop=url|size|mime"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid, p in pages.items():
                title = p.get("title")
                info = p.get("imageinfo", [{}])[0]
                mime = info.get("mime")
                url_dl = info.get("url")
                size = info.get("size", 0) / (1024*1024)
                print(f"[{q}] {title} ({size:.1f} MB, {mime}) -> {url_dl}")
    except Exception as e:
        print(f"Error for {q}: {e}")
