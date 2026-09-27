import urllib.request, json

api_url = "https://api.github.com/search/repositories?q=CCTV+intrusion+detection+video&sort=stars&per_page=10"
headers = {"User-Agent": "Mozilla/5.0"}
req = urllib.request.Request(api_url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        for item in data.get('items', []):
            print(item.get('full_name'))
except Exception as e:
    print("Error:", e)
