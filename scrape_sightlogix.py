import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get('https://www.sightlogix.com/video-examples/', headers=headers)
print('SightLogix Status:', r.status_code)
vids = re.findall(r'https://[^"\'\s]+\.(?:mp4|webm)', r.text)
print('Found direct videos:', len(vids))
for v in set(vids):
    print(' ', v)

# Also check for embedded wistia / vimeo / youtube / wp-content video links
wp_vids = re.findall(r'https://www\.sightlogix\.com/wp-content/uploads/[^"\'\s]+\.mp4', r.text)
print('WP Videos:', len(wp_vids))
for v in set(wp_vids):
    print(' ', v)
