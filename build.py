#!/usr/bin/env python3
"""
Build a Televizo-friendly M3U playlist:
- downloads a source M3U (your provider link)
- optionally merges an extra local M3U (extras.m3u)
- removes duplicate URLs
- removes adult/XXX groups by default (to keep the list family-friendly)
- sorts by group-title then channel name

Usage (GitHub Actions):
  python build.py

Env vars:
  SOURCE_M3U_URL   (required)  e.g. http://pl.ru-tv.site/.../tv.m3u
  EXTRAS_FILE      (optional)  default: extras.m3u
  OUTPUT_FILE      (optional)  default: playlist.m3u
  EXCLUDE_ADULT    (optional)  default: 1  (1=yes, 0=no)
"""
from __future__ import annotations
import os, re, sys, urllib.request
from dataclasses import dataclass
from typing import Iterable, List, Tuple, Optional, Dict

ADULT_GROUP_PAT = re.compile(r'\b(XXX|Adult|Porn|Erotic)\b', re.IGNORECASE)
ADULT_NAME_PAT  = re.compile(r'\b(Brazzers|Hustler|Penthouse|Redtube|Porn|XXX)\b', re.IGNORECASE)

@dataclass
class Entry:
    extinf: str
    url: str
    group: str
    name: str

def _get_attr(extinf: str, key: str) -> str:
    m = re.search(rf'{re.escape(key)}="([^"]*)"', extinf)
    return (m.group(1) if m else "").strip()

def _get_name_from_extinf(extinf: str) -> str:
    # After last comma
    if ',' in extinf:
        return extinf.split(',', 1)[1].strip()
    return ""

def parse_m3u(text: str) -> List[Entry]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: List[Entry] = []
    cur: Optional[str] = None
    for ln in lines:
        if ln.startswith('#EXTINF:'):
            cur = ln
        elif ln.startswith('#'):
            continue
        else:
            if cur:
                group = _get_attr(cur, "group-title")
                name = _get_attr(cur, "tvg-name") or _get_name_from_extinf(cur) or "Unknown"
                out.append(Entry(extinf=cur, url=ln, group=group, name=name))
                cur = None
    return out

def download(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    # try utf-8 first, fallback cp1251
    for enc in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", errors="replace")

def read_file(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    for enc in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", errors="replace")

def is_adult(e: Entry) -> bool:
    if ADULT_GROUP_PAT.search(e.group or ""):
        return True
    if ADULT_NAME_PAT.search(e.name or ""):
        return True
    return False

def normalize_url(u: str) -> str:
    return u.strip()

def build_header() -> str:
    # Televizo understands standard M3U header
    return "#EXTM3U\n"


# Preferred group order (for Televizo-like navigation)
GROUP_ORDER = [
    "Казахстан",
    "Армения",
    "Беларусь",
    "Таджикистан",
    "Узбекистан",
    "Грузия",
    "Азербайджан",
    "Германия",
    "Румыния",
    "Израиль",
    "Балтика",
    "Америка",
    "4K",
    "Турция",
    "Польша",
    "Молдова",
    "Греция",
    "Болгария",
    "Испания",
    "Информационные",
    "Кино",
    "Развлекательные",
    "Познавательные",
    "Украина",
    "Спорт",
    "Музыка",
    "Детские",
    "XXX",
]

def group_rank(g: str) -> int:
    if not g:
        return 10_000
    try:
        return GROUP_ORDER.index(g)
    except ValueError:
        return 9_999

def main() -> int:
    src_url = os.environ.get("SOURCE_M3U_URL", "").strip()
    # SOURCE_M3U_URL is optional; if missing we only use extras.m3u
    src_entries = []
    if src_url:
        src_text = download(src_url)
        src_entries = parse_m3u(src_text)

    extras_file = os.environ.get("EXTRAS_FILE", "extras.m3u").strip()
    out_file = os.environ.get("OUTPUT_FILE", "playlist.m3u").strip()
    exclude_adult = os.environ.get("EXCLUDE_ADULT", "0").strip() != "0"


    # Load extras (optional)
    extra_entries: List[Entry] = []
    if extras_file and os.path.exists(extras_file):
        extra_entries = parse_m3u(read_file(extras_file))

    all_entries = src_entries + extra_entries

    # Deduplicate by URL (keep first)
    seen: set[str] = set()
    merged: List[Entry] = []
    for e in all_entries:
        u = normalize_url(e.url)
        if not u or u in seen:
            continue
        if exclude_adult and is_adult(e):
            continue
        seen.add(u)
        merged.append(e)

    # Sort by group then name (case-insensitive)
    merged.sort(key=lambda x: (group_rank(x.group), (x.group or "").lower(), (x.name or "").lower()))

    # Write output
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(build_header())
        for e in merged:
            f.write(e.extinf.rstrip() + "\n")
            f.write(e.url.rstrip() + "\n")

    print(f"OK: wrote {out_file} with {len(merged)} channels (src={len(src_entries)}, extras={len(extra_entries)}, exclude_adult={exclude_adult}).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
