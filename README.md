# Auto IPTV playlist (Televizo)

Bu repo avtomatik `playlist.m3u` yasaydi.

## 1) GitHub Secret qo'shing
Repo -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**

- `SOURCE_M3U_URL` = siz bergan link (masalan):  
  `http://pl.ru-tv.site/9f456976/7bceee90/tv.m3u`

## 2) Workflow pushga ruxsat bering
Repo -> **Settings** -> **Actions** -> **General** -> **Workflow permissions**:
- **Read and write permissions** ni tanlang
- **Save**

## 3) Fayllar
- `build.py` – playlist quradi
- `.github/workflows/update.yml` – har 6 soatda yangilaydi
- `extras.m3u` – sizning qo'shimcha kanallaringiz (xspf dan o'girildi)
- `playlist.m3u` – tayyor yakuniy playlist

> Eslatma: xavfsizlik uchun `XXX/Adult` bo'limlari default o'chirilgan.
