import urllib.request, json

url = "https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=filemime:video+\"border+patrol\"&srnamespace=6&srlimit=10"
headers = {"User-Agent": "Mozilla/5.0"}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    for item in data.get("query", {}).get("search", []):
        print(item["title"])
