import urllib.request, json

# Search GitHub repositories with intrusion detection / border surveillance videos
api_url = "https://api.github.com/search/code?q=filename:mp4+surveillance+border+OR+perimeter&per_page=10"
headers = {"User-Agent": "Python/3.14"}
req = urllib.request.Request(api_url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Total count: {data.get('total_count')}")
        for item in data.get('items', [])[:5]:
            print(item.get('name'), item.get('html_url'))
except Exception as e:
    print("Error:", e)
