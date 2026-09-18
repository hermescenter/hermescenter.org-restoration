"""Fetch raw (id_) Wayback copies of old posts: they keep the ORIGINAL link URLs that the crawl rewrote."""
import sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "wayback" / "articles"
OUT.mkdir(parents=True, exist_ok=True)

def fetch(slug):
    out = OUT / (slug.replace("/", "_") + ".html")
    if out.exists() and out.stat().st_size > 5000:
        return "cached"
    for ts in ("2023", "2021", "2019", "2016"):
        url = f"https://web.archive.org/web/{ts}id_/https://www.hermescenter.org/{slug}/"
        for attempt in range(3):
            try:
                data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "hermes-restore"}), timeout=90).read()
                if len(data) > 5000 and b"hermescenter" in data:
                    out.write_bytes(data)
                    return ts
                break
            except Exception:
                time.sleep(6 * (attempt + 1))
        time.sleep(3)
    return None

if __name__ == "__main__":
    slugs = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    ko = []
    for s in slugs:
        r = fetch(s)
        print(r or "KO", s, flush=True)
        if not r: ko.append(s)
        time.sleep(2)
    print("KO:", ko)
