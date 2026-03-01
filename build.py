#!/usr/bin/env python3
"""
Televizo-friendly M3U builder (100% deterministic grouping):
- Uses group-title if present
- Else assigns group by rules from RULES_FILE (regex -> group)
- If still unknown -> "Другие"
- Deduplicate by URL
- Optional adult/XXX exclude
- Sort by preferred group order then channel name

Env vars:
  SOURCE_M3U_URL   optional
  EXTRAS_FILE      default: extras.m3u
  OUTPUT_FILE      default: playlist.m3u
  EXCLUDE_ADULT    default: 1 (1=yes, 0=no)
  RULES_FILE       default: rules.txt
"""

from __future__ import annotations
import os, re, urllib.request
from dataclasses import dataclass
from typing import List, Optional, Tuple

ADULT_GROUP_PAT = re.compile(r'\b(XXX|Adult|Porn|Erotic)\b', re.IGNORECASE)
ADULT_NAME_PAT  = re.compile(r'\b(Brazzers|Hustler|Penthouse|Redtube|Porn|XXX)\b', re.IGNORECASE)

# Guruhlar tartibi (xohlasang o'zgartir)
GROUP_ORDER = [
    "Узбекистан",
    "Казахстан",
    "Армения",
    "Беларусь",
    "Таджикистан",
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
    "Другие",
]

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
    if "," in extinf:
        return extinf.split(",", 1)[1].strip()
    return ""

def normalize_url(u: str) -> str:
    return (u or "").strip()

def build_header() -> str:
    return "#EXTM3U\n"

def group_rank(g: str) -> int:
    try:
        return GROUP_ORDER.index(g)
    except ValueError:
        return GROUP_ORDER.index("Другие") if "Другие" in GROUP_ORDER else 9999

def set_group_title(extinf: str, group: str) -> str:
    group = (group or "Другие").replace('"', "'")
    if re.search(r'group-title="[^"]*"', extinf):
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:", f'#EXTINF: group-title="{group}" ', 1)

def is_adult(e: Entry) -> bool:
    if ADULT_GROUP_PAT.search(e.group or ""):
        return True
    if ADULT_NAME_PAT.search(e.name or ""):
        return True
    return False

# ---------------- RULES (100% deterministic) ----------------

Rule = Tuple[re.Pattern, str]

def load_rules(path: str) -> List[Rule]:
    """
    rules.txt format (one per line):
      <GROUP> || <REGEX>

    Example:
      Спорт || \b(match|setanta|eurosport|ufc)\b
      Кино  || \b(kinoteatr|amedia|film|movie)\b

    Notes:
    - Lines starting with # are comments
    - Regex is case-insensitive automatically
    """
    rules: List[Rule] = []
    if not os.path.exists(path):
        return rules

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "||" not in line:
                continue
            group, pattern = [x.strip() for x in line.split("||", 1)]
            if not group or not pattern:
                continue
            rules.append((re.compile(pattern, re.IGNORECASE), group))
    return rules

def match_group_by_rules(name: str, rules: List[Rule]) -> Optional[str]:
    n = (name or "").strip()
    if not n:
        return None
    for pat, grp in rules:
        if pat.search(n):
            return grp
    return None

def ensure_group(extinf: str, name: str, rules: List[Rule]) -> str:
    # 1) provider group-title
    g = _get_attr(extinf, "group-title")
    if g:
        return g.strip()

    # 2) other attrs (sometimes exist)
    g = _get_attr(extinf, "tvg-group") or _get_attr(extinf, "category")
    if g:
        return g.strip()

    # 3) STRICT deterministic: rules file
    g = match_group_by_rules(name, rules)
    if g:
        return g.strip()

    # 4) If unknown -> Others (we do NOT guess randomly)
    return "Другие"

# ---------------- M3U IO ----------------

def parse_m3u(text: str, rules: List[Rule]) -> List[Entry]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: List[Entry] = []
    cur: Optional[str] = None

    for ln in lines:
        if ln.startswith("#EXTINF:"):
            cur = ln
            continue
        if ln.startswith("#"):
            continue

        if cur:
            name = _get_attr(cur, "tvg-name") or _get_name_from_extinf(cur) or "Unknown"
            group = ensure_group(cur, name, rules)
            fixed_extinf = set_group_title(cur, group)
            out.append(Entry(extinf=fixed_extinf, url=ln, group=group, name=name))
            cur = None

    return out

def download(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
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

def main() -> int:
    src_url = os.environ.get("SOURCE_M3U_URL", "").strip()
    extras_file = os.environ.get("EXTRAS_FILE", "extras.m3u").strip()
    out_file = os.environ.get("OUTPUT_FILE", "playlist.m3u").strip()
    exclude_adult = os.environ.get("EXCLUDE_ADULT", "1").strip() != "0"
    rules_file = os.environ.get("RULES_FILE", "rules.txt").strip()

    rules = load_rules(rules_file)

    src_entries: List[Entry] = []
    if src_url:
        src_entries = parse_m3u(download(src_url), rules)

    extra_entries: List[Entry] = []
    if extras_file and os.path.exists(extras_file):
        extra_entries = parse_m3u(read_file(extras_file), rules)

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

    merged.sort(key=lambda x: (group_rank(x.group), (x.group or "").lower(), (x.name or "").lower()))

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(build_header())
        for e in merged:
            f.write(e.extinf.rstrip() + "\n")
            f.write(e.url.rstrip() + "\n")

    unknown = sum(1 for e in merged if e.group == "Другие")
    print(
        f"OK: wrote {out_file} with {len(merged)} channels "
        f"(src={len(src_entries)}, extras={len(extra_entries)}, exclude_adult={exclude_adult}, rules={len(rules)}, unknown={unknown})."
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
