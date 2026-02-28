import re
from urllib.request import urlopen

SOURCES = [
    ("Russia",      "https://iptv-org.github.io/iptv/countries/ru.m3u"),
    ("Uzbekistan",  "https://iptv-org.github.io/iptv/countries/uz.m3u"),
    ("Kazakhstan",  "https://iptv-org.github.io/iptv/countries/kz.m3u"),
    ("Kyrgyzstan",  "https://iptv-org.github.io/iptv/countries/kg.m3u"),
    ("Belarus",     "https://iptv-org.github.io/iptv/countries/by.m3u"),
    ("Ukraine",     "https://iptv-org.github.io/iptv/countries/ua.m3u"),
]

def fetch(url: str) -> str:
    with urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def ensure_group(extinf: str, group: str) -> str:
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')

def parse(m3u: str, group: str):
    lines = [l.strip() for l in m3u.splitlines() if l.strip()]
    i = 0
    out = []
    while i < len(lines) - 1:
        if lines[i].startswith("#EXTINF") and not lines[i+1].startswith("#"):
            out.append((ensure_group(lines[i], group), lines[i+1]))
            i += 2
        else:
            i += 1
    return out

def main():
    items = []
    for group, url in SOURCES:
        items.extend(parse(fetch(url), group))

    # URL bo'yicha takrorlarni olib tashlash
    seen = set()
    uniq = []
    for extinf, url in items:
        if url in seen:
            continue
        seen.add(url)
        uniq.append((extinf, url))

    out = ["#EXTM3U"]
    for extinf, url in uniq:
        out.append(extinf)
        out.append(url)

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

if __name__ == "__main__":
    main()
