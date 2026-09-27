import urllib.request, json

titles = ["File:CBP Media Briefing - Border Wall Project.webm", "File:CBX CROSS BORDER XPRESS.webm"]
for t in titles:
    url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&titles={urllib.parse.quote(t)}&prop=imageinfo&iiprop=url|size|mime"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode("utf-8"))
        pages = d.get("query", {}).get("pages", {})
        for _, p in pages.items():
            print(p.get("title"), p.get("imageinfo", [{}])[0].get("url"))
