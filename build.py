import requests

SOURCE = "http://pl.ru-tv.site/9f456976/7bceee90/tv.m3u"

r = requests.get(SOURCE)
lines = r.text.splitlines()

out = ["#EXTM3U"]

for line in lines:
    if "TR" in line or "Turkey" in line:
        continue

    if "#EXTINF" in line:
        line = line.replace('group-title="My channels"', 'group-title="🇷🇺 Russia"')

    out.append(line)

open("playlist.m3u","w",encoding="utf-8").write("\n".join(out))
