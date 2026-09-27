import urllib.request, json

queries = [
    "\"thermal camera\"",
    "\"forward looking infrared\"",
    "\"FLIR\"",
    "\"perimeter security\"",
    "\"checkpoint\"",
    "\"night vision\""
]

for q in queries:
    url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=filemime:video+{urllib.parse.quote(q)}&srnamespace=6&srlimit=5"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = [item["title"] for item in data.get("query", {}).get("search", [])]
            print(f"[{q}] -> {items}")
    except Exception as e:
        print(e)
