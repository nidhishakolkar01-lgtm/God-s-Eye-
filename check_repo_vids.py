import urllib.request, json

repos = [
    "raghavpli515/Sensitive-area-Intrusion-detection-system",
    "qbarthelemy/PyGOFPID",
    "tejas-koliyoor/Perimeter-Intrusion-Detection",
    "JKLover0909/Intruder_detection"
]

headers = {"User-Agent": "Mozilla/5.0"}

for r in repos:
    api = f"https://api.github.com/repos/{r}/git/trees/main?recursive=1"
    try:
        req = urllib.request.Request(api, headers=headers)
        with urllib.request.urlopen(req) as resp:
            tree = json.loads(resp.read().decode("utf-8")).get("tree", [])
            vids = [item["path"] for item in tree if item["path"].lower().endswith(('.mp4', '.avi', '.m4v'))]
            print(f"Repo {r}: {len(vids)} videos -> {vids[:5]}")
    except Exception as e:
        # Try master
        api = f"https://api.github.com/repos/{r}/git/trees/master?recursive=1"
        try:
            req = urllib.request.Request(api, headers=headers)
            with urllib.request.urlopen(req) as resp:
                tree = json.loads(resp.read().decode("utf-8")).get("tree", [])
                vids = [item["path"] for item in tree if item["path"].lower().endswith(('.mp4', '.avi', '.m4v'))]
                print(f"Repo {r} (master): {len(vids)} videos -> {vids[:5]}")
        except Exception as err:
            print(f"Failed {r}: {err}")
