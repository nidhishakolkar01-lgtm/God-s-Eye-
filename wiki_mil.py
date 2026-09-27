import urllib.request, json

titles = [
    "File:719th Military Intelligence Battalion at Yawolsan, South Korea (1000117).webm",
    "File:Special Forces Conduct Training DOD 100067169.webm",
    "File:Khaan Quest 2026 (1012076).webm"
]

for t in titles:
    url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&titles={urllib.parse.quote(t)}&prop=imageinfo&iiprop=url|size|mime"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode("utf-8"))
        pages = d.get("query", {}).get("pages", {})
        for _, p in pages.items():
            info = p.get("imageinfo", [{}])[0]
            print(p.get("title"), f"{info.get('size', 0)/(1024*1024):.1f}MB", info.get("url"))
