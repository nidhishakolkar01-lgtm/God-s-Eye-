import urllib.request, json

repos = [
    "nandita2553037-cpu/sih26187-ibvap",
    "parthameshingawale-eng/ibvap",
    "Riddhi23133/IBVAP_Border_surveillance",
    "MadhuSudhan-ally/Smart-CCTV-Intrusion-and-Theft-Detection-with-Alarm-and-Email-SMS-Alerts-using-YOLOv5",
    "musahthegreat/CCTV-Anomaly-Intrusion-Detection-System"
]

headers = {"User-Agent": "Mozilla/5.0"}

for r in repos:
    for branch in ["main", "master"]:
        api = f"https://api.github.com/repos/{r}/git/trees/{branch}?recursive=1"
        try:
            req = urllib.request.Request(api, headers=headers)
            with urllib.request.urlopen(req) as resp:
                tree = json.loads(resp.read().decode("utf-8")).get("tree", [])
                vids = [item["path"] for item in tree if item["path"].lower().endswith(('.mp4', '.avi', '.m4v', '.mkv'))]
                print(f"Repo {r} ({branch}): {len(vids)} videos -> {vids}")
                break
        except Exception:
            continue
