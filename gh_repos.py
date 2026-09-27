import urllib.request, json

api_url = "https://api.github.com/search/repositories?q=perimeter+intrusion+detection+video&sort=stars&per_page=5"
headers = {"User-Agent": "Python/3.14"}
req = urllib.request.Request(api_url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        for item in data.get('items', [])[:5]:
            print(item.get('full_name'), "-->", item.get('html_url'))
except Exception as e:
    print("Error:", e)
