#!/usr/bin/env python3
import os, re, urllib.request
from dataclasses import dataclass
from typing import List, Optional, Tuple

GROUP_ORDER = [
    "Узбекистан","Спорт","Кино","Развлекательные","Информационные",
    "Музыка","Детские","Познавательные","XXX","Другие"
]

ADULT = re.compile(r'(xxx|adult|porn)', re.I)

@dataclass
class Entry:
    extinf: str
    url: str
    group: str
    name: str

def _attr(s, k):
    m = re.search(rf'{k}="([^"]*)"', s)
    return m.group(1) if m else ""

def _name(ext):
    return ext.split(",",1)[1].strip() if "," in ext else "Unknown"

def set_group(ext, group):
    if 'group-title="' in ext:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', ext)
    return ext.replace("#EXTINF:", f'#EXTINF: group-title="{group}" ', 1)

def load_rules(path):
    rules=[]
    if not os.path.exists(path): return rules
    for ln in open(path,encoding="utf-8"):
        ln=ln.strip()
        if not ln or ln.startswith("#"): continue
        if "||" not in ln: continue
        g,p=[x.strip() for x in ln.split("||",1)]
        rules.append((re.compile(p,re.I),g))
    return rules

def match(name,rules):
    for r,g in rules:
        if r.search(name): return g
    return "Другие"

def parse(text,rules):
    out=[]; cur=None
    for ln in text.splitlines():
        ln=ln.strip()
        if not ln: continue
        if ln.startswith("#EXTINF:"):
            cur=ln; continue
        if ln.startswith("#"): continue
        if cur:
            name=_attr(cur,"tvg-name") or _name(cur)
            group=_attr(cur,"group-title") or match(name,rules)
            out.append(Entry(set_group(cur,group),ln,group,name))
            cur=None
    return out

def download(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    return urllib.request.urlopen(req).read().decode("utf-8","ignore")

def rank(g):
    return GROUP_ORDER.index(g) if g in GROUP_ORDER else 999

def main():
    url=os.getenv("SOURCE_M3U_URL","").strip()
    rules=load_rules("rules.txt")
    text=download(url) if url else ""
    entries=parse(text,rules)

    seen=set(); merged=[]
    for e in entries:
        if ADULT.search(e.name): continue
        if e.url in seen: continue
        seen.add(e.url); merged.append(e)

    merged.sort(key=lambda x:(rank(x.group),x.name.lower()))

    with open("playlist.m3u","w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in merged:
            f.write(e.extinf+"\n"+e.url+"\n")

    print("Playlist built:",len(merged))

if __name__=="__main__":
    main()
