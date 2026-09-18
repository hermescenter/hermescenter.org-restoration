"""Export the News & Press restoration package (repo hermescenter/hermescenter.org-restoration).

    python tools/export_restoration.py <dest-dir>

Produces:
  site/    static review site (relative links, works from file:// or any static host) + stampa.html
  media/   every file the posts use: wp-content/uploads/... keeps the ORIGINAL hermescenter.org path,
           third-party documents under external/<host>/<file name> (rehosted locally by policy; full original URL in media.json)
  data/    posts.json/.csv, per-post post.json + content.html (links in their ORIGINAL absolute form),
           media.json, categories.json, tags.json, missing.json
"""
import csv, hashlib, html, json, mimetypes, re, runpy, shutil, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DEST = Path(sys.argv[1]).resolve()
HC = "https://www.hermescenter.org/"
ROME = ZoneInfo("Europe/Rome")

g = runpy.run_path(str(ROOT / "tools" / "build_review.py"))      # builds review/ and gives us the items
items, REVIEW = g["items"], ROOT / "review"
id2slug = {it["id"]: it["slug"] for it in items}
page_slugs = {p["file"][:-5].lower() for p in g["pages"]}

# ------------------------------------------------ original URLs of files the crawl saved without host
orig_by_path = {}
def learn(url):
    if not re.match(r"^https?://", url or "", re.I) or "web.archive.org" in url or re.match(r"^https?://(www\.)?hermescenter\.org", url, re.I):
        return
    sp = urlsplit(url)
    p = unquote(sp.path).strip("/").lower()
    if p:
        orig_by_path.setdefault(f"{sp.netloc.lower()}/{p}", url)
        orig_by_path.setdefault(p, url)
for f in (ROOT / "data" / "wayback" / "articles").glob("*.html"):
    for u in re.findall(r'(?:href|src)="(https?://[^"]+)"', f.read_text(encoding="utf-8", errors="replace")):
        learn(html.unescape(u))
for r in csv.DictReader(open(ROOT / "data" / "documenti_esterni.csv", encoding="utf-8-sig")):
    learn(r["url_originale"])
for u in re.findall(r"(https?://\S+?)(?:\s|\|)", (ROOT / "recovered" / "README.md").read_text(encoding="utf-8")):
    learn(u)

_ext_names = {}
def ext_rel(url):
    """external/<host>/<file name>: short enough for Windows (260-char paths) once unzipped.
    Deep original paths are not needed here, the full URL is kept in media.json."""
    sp = urlsplit(url)
    name = unquote(sp.path.rstrip("/").rsplit("/", 1)[-1]) or "index"
    stem, dot, ext = name.rpartition(".")
    h = hashlib.sha256(url.encode()).hexdigest()[:8]
    if len(name) > 70:
        name = f"{(stem if dot else name)[:50].rstrip(' ._-')}-{h}{'.' + ext if dot else ''}"
    rel = f"external/{sp.netloc.lower().removeprefix('www.')}/{name}"
    if _ext_names.setdefault(rel.lower(), url) != url:                 # same name, different document
        rel = f"external/{sp.netloc.lower().removeprefix('www.')}/{h}-{name}"
    return rel

def original_of_served(served):
    """served = 'archive/...' or 'recovered/...' -> (original_url or None, media_rel)"""
    rel = re.sub(r"_(docx?|xlsx?|pptx?|odt|rtf)$", r".\1", served.split("/", 1)[1], flags=re.I)   # x_doc -> x.doc
    m = re.match(r"(?i)wp-content/uploads/(.+)$", rel)
    if m:
        return HC + "wp-content/uploads/" + m.group(1), "wp-content/uploads/" + m.group(1)
    key = rel.lower()
    first = rel.split("/")[0]
    url = orig_by_path.get(key)
    if not url and "." in first and "/" in rel:                     # archive/<host>/<path>
        url = orig_by_path.get(key) or f"https://{rel}"
    if url:
        sp = urlsplit(url)
        return url, ext_rel(url)
    return None, f"external/_host-sconosciuto/{rel}"

def classify(href):
    """A href/src as written in review pages -> dict(original, served, kind)."""
    h = html.unescape(href or "")
    if not h or h.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return {"kind": "raw", "original": h}
    if re.fullmatch(r"[a-z0-9_-]+\.html", h) and h[:-5] in id2slug:
        return {"kind": "post", "original": HC + id2slug[h[:-5]] + "/"}
    m = re.match(r"^https://web\.archive\.org/web/2024(?:im_)?/(.+)$", h)
    if m:
        return {"kind": "missing", "original": m.group(1)}
    if h.startswith(("/archive/", "/recovered/")):
        served = unquote(h[1:])
        if served.endswith(".html"):                                 # an archived web page, not a file
            p = served.split("/", 1)[1][:-5]
            if p.lower() in page_slugs and not p.split("/")[0].count("."):
                return {"kind": "page", "original": HC + p + "/"}
            url = orig_by_path.get(p.lower()) or orig_by_path.get(p.lower() + ".html")
            return {"kind": "page", "original": url}
        url, media_rel = original_of_served(served)
        return {"kind": "file", "original": url, "served": served, "media": media_rel}
    return {"kind": "external", "original": h}

# ------------------------------------------------ build package
for sub in ("site", "media", "data"):
    shutil.rmtree(DEST / sub, ignore_errors=True)
(DEST / "data" / "posts").mkdir(parents=True)
media = {}                                                          # media_rel -> record
def add_media(c, post_slug, role):
    rec = media.get(c["media"])
    if rec is None:
        src = ROOT / c["served"]
        dst = DEST / "media" / c["media"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        data = src.read_bytes()
        rec = media[c["media"]] = {
            "path": "media/" + c["media"], "original_url": c["original"],
            "origin": "hermescenter" if c["media"].startswith("wp-content/") else "esterno",
            "recovered": c["served"].startswith("recovered/"),
            "mime": mimetypes.guess_type(dst.name)[0] or "application/octet-stream",
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "used_by": []}
    if post_slug not in rec["used_by"]:
        rec["used_by"].append(post_slug)
    return rec

def iso_dates(published):
    if not published:
        return None, None
    d = datetime.fromisoformat(published.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), d.astimezone(ROME).strftime("%Y-%m-%d %H:%M:%S")

def meta_of(src, prop):
    m = re.search(rf'<meta[^>]+property="{prop}"[^>]+content="([^"]*)"', src.read_text(encoding="utf-8", errors="replace"))
    return html.unescape(m.group(1)) if m else None

def raw_originals(it, tag, attr, n):
    """Original URLs, in document order, from the raw Wayback copy of the post (same content, untouched links).
    Used only when the element count matches the zip copy exactly, so position i is the same element."""
    raw = ROOT / "data" / "wayback" / "articles" / (it["slug"].replace("/", "_") + ".html")
    if not raw.exists() or raw.stat().st_size < 5000:
        return None
    rb = g["extract"](raw)[3]
    if rb is None:
        return None
    vals = [e.get(attr) for e in rb.find_all(tag)]
    if len(vals) != n:
        return None
    base = HC + it["slug"] + "/"
    out = []
    for v in vals:
        v = html.unescape(v or "")
        m = re.match(r"^https?://web\.archive\.org/web/\d+[a-z_]*/(.+)$", v)
        v = m.group(1) if m else v
        out.append(urljoin(base, v) if v and not v.startswith(("mailto:", "tel:", "javascript:", "#")) else v)
    return out

def is_file_url(u): return bool(re.search(r"\.(pdf|docx?|odt|xlsx?|ods|pptx?|odp|rtf|zip|mp3|mp4|mov|mpeg|jpe?g|png|gif|webp|svg)$", urlsplit(u).path, re.I))

posts, missing, rel_site, aligned, site_bodies = [], [], {}, Counter(), {}
for it in sorted(items, key=lambda x: x["published"] or ""):
    body = BeautifulSoup(it["body"].decode_contents(), "lxml")
    sbody = BeautifulSoup(it["body"].decode_contents(), "lxml")          # same content for the review site
    atts, links_missing = [], []
    for tag, attr in (("a", "href"), ("img", "src"), ("source", "src"), ("video", "src"), ("audio", "src")):
        # embed links (p.embed) are <iframe> in the raw copy: leave them to the embed step below
        not_embed = lambda e: not (tag == "a" and e.find_parent("p", class_="embed"))
        els, sels = [e for e in body.find_all(tag) if not_embed(e)], [e for e in sbody.find_all(tag) if not_embed(e)]
        hints = raw_originals(it, tag, attr, len(els)) if els else None
        aligned["ok" if hints else ("mismatch" if els and (ROOT / "data" / "wayback" / "articles" / (it["slug"].replace("/", "_") + ".html")).exists() else "no-raw")] += 1
        for n, e in enumerate(els):
            v = e.get(attr)
            if not v:
                continue
            c = classify(v)
            hint = hints[n] if hints else None
            if hint and re.match(r"^(https?|mailto):", hint, re.I):
                if c["kind"] == "file" and not c["original"]:
                    c["original"] = hint
                    sp = urlsplit(hint)
                    up = re.match(r"(?i)^https?://(?:www\.)?hermescenter\.org/wp-content/uploads/(.+)$", hint)
                    if up:                                               # a Hermes upload the crawl filed elsewhere
                        c["media"] = "wp-content/uploads/" + unquote(up.group(1))
                    elif not c["media"].startswith("wp-content/"):
                        c["media"] = ext_rel(hint)
                elif c["kind"] in ("missing", "page", "external") and c.get("original") != hint:
                    c = {"kind": "missing" if is_file_url(hint) and re.match(r"^https?://(www\.)?hermescenter\.org/", hint, re.I) else "external", "original": hint}
            elif c["kind"] == "missing" and not is_file_url(c["original"]):
                c = {"kind": "page", "original": None}                  # crawler-mangled link, original unknown
            se = sels[n]
            if c["kind"] == "file":
                se[attr] = "../../media/" + quote(c["media"])
            elif c["kind"] in ("post", "raw"):
                pass                                                     # review-site link already right
            elif c["kind"] == "missing":
                se[attr] = "https://web.archive.org/web/2024/" + c["original"]
            elif c.get("original"):
                se[attr] = c["original"]
            else:
                se.attrs.pop(attr, None)
            if c["kind"] == "file":
                rec = add_media(c, it["slug"], tag)
                rel_site[v] = "media/" + c["media"]
                atts.append({"type": "immagine" if tag == "img" else "documento", "original_url": c["original"], "file": rec["path"]})
                e[attr] = c["original"] or v
                if not c["original"]:
                    e["data-restore-file"] = rec["path"]                 # host unknown: file kept, URL to decide
            elif c["kind"] == "missing":
                links_missing.append({"type": "immagine" if tag == "img" else "documento", "original_url": c["original"]})
                e[attr] = c["original"]
            elif c["kind"] in ("post", "page", "external") and c["original"]:
                e[attr] = c["original"]
            elif c["kind"] == "page":
                e.attrs.pop(attr, None)                                  # archived page of unknown origin: keep the text
            # drop the classes/attributes the review site added
            cls = [x for x in e.get("class", []) if x not in ("ext", "int", "missing", "doc") and not x.startswith("doc-")]
            if cls:
                e["class"] = cls
            else:
                e.attrs.pop("class", None)
            if e.get("title", "").startswith("Immagine non presente in locale"):
                del e["title"]
    # (after the link loop, so body/sbody keep the same element order during it)
    # embeds: the review site turned <iframe> into <p class="embed"><a>; restore the iframe with its original src
    raw = ROOT / "data" / "wayback" / "articles" / (it["slug"].replace("/", "_") + ".html")
    emb_b, emb_s = body.select("p.embed"), sbody.select("p.embed")
    if emb_b and raw.exists():
        rb = g["extract"](raw)[3]
        srcs = [re.sub(r"^https?://web\.archive\.org/web/\d+[a-z_]*/", "", html.unescape(i.get("src", ""))) for i in rb.find_all("iframe")] if rb else []
        if len(srcs) == len(emb_b):
            for pb, ps, src in zip(emb_b, emb_s, srcs):
                src = "https:" + src if src.startswith("//") else src
                pb.replace_with(BeautifulSoup(f'<iframe src="{html.escape(src)}" width="100%" height="400" frameborder="0" allowfullscreen></iframe>', "lxml").iframe)
                a = ps.find("a")
                a["href"] = src
                a.string = src[:90]
    # embeds without a raw copy: players back to <iframe>, embedded pages (WordPress oEmbed) to a plain link
    for pb in body.select("p.embed"):
        a = pb.find("a")
        src = a.get("href", "") if a else ""
        if re.search(r"//(www\.)?(youtube\.com|youtu\.be|player\.vimeo\.com|w\.soundcloud\.com|widget\.spreaker\.com|archive\.org)/", src):
            pb.replace_with(BeautifulSoup(f'<iframe src="{html.escape(src)}" width="100%" height="400" frameborder="0" allowfullscreen></iframe>', "lxml").iframe)
        elif src:
            pb.replace_with(BeautifulSoup(f'<p><a href="{html.escape(src)}">{html.escape(src)}</a></p>', "lxml").p)
    # featured image (og:image) if it is a Hermes upload we hold
    featured = None
    og = meta_of(it["src"], "og:image")
    if og and re.match(r"^https?://(www\.)?hermescenter\.org/wp-content/uploads/", og, re.I):
        rel = re.sub(r"^https?://(www\.)?hermescenter\.org/", "", og, flags=re.I)
        served = g["local"].get(unquote(rel).lower())
        if served and g["valid"](served):
            rec = add_media({"media": "wp-content/uploads/" + unquote(rel).split("wp-content/uploads/", 1)[1],
                             "served": served, "original": HC + unquote(rel)}, it["slug"], "featured")
            featured = {"original_url": HC + unquote(rel), "file": rec["path"]}
    date_gmt, date_rome = iso_dates(it["published"])
    mod_gmt, _ = iso_dates(meta_of(it["src"], "article:modified_time"))
    pid = it["id"]
    post = {
        "id": pid, "title": it["title"], "slug": it["slug"].split("/")[-1], "path": "/" + it["slug"] + "/",
        "original_url": HC + it["slug"] + "/", "old_urls": ["/" + a + "/" for a in it["aliases"]],
        "date_gmt": date_gmt, "date_europe_rome": date_rome, "modified_gmt": mod_gmt,
        "author": it["author"] or None, "language": it["lang"], "words": it["words"],
        "categories": g["cat_sort"](it["categories"]), "tags": it["tags"],
        "featured_image": featured, "attachments": atts, "missing": links_missing,
        "content_file": f"data/posts/{pid}/content.html",
        "source": {"type": "wayback-zip" if it["origin"] == "zip" else "wayback-live", "file": it["file"]},
    }
    site_bodies[pid] = sbody.body.decode_contents() if sbody.body else str(sbody)
    d = DEST / "data" / "posts" / pid
    d.mkdir()
    (d / "content.html").write_text(str(body.body.decode_contents() if body.body else body).strip() + "\n", encoding="utf-8")
    (d / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    posts.append(post)
    missing += [{"post": post["original_url"], **m} for m in links_missing]

def slugify(s): return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("/", "")).strip("-")
cats = Counter(c for p in posts for c in p["categories"])
tags = Counter(t for p in posts for t in p["tags"])
W = lambda name, obj: (DEST / "data" / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
W("posts.json", posts)
W("categories.json", [{"name": c, "slug": slugify(c) or "it", "posts": n} for c, n in cats.most_common()])
W("tags.json", [{"name": t, "slug": slugify(t), "posts": n} for t, n in sorted(tags.items(), key=lambda x: (-x[1], x[0].lower()))])
W("media.json", sorted(media.values(), key=lambda r: r["path"]))
W("missing.json", missing)
with open(DEST / "data" / "posts.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "date_europe_rome", "date_gmt", "title", "original_url", "old_urls", "categories", "tags", "language",
                "attachments", "missing", "featured_image", "content_file"])
    for p in posts:
        w.writerow([p["id"], p["date_europe_rome"], p["date_gmt"], p["title"], p["original_url"], " ".join(p["old_urls"]),
                    "; ".join(p["categories"]), "; ".join(p["tags"]), p["language"], len(p["attachments"]), len(p["missing"]),
                    (p["featured_image"] or {}).get("original_url", ""), p["content_file"]])

# ------------------------------------------------ static site with relative links into media/
shutil.copytree(REVIEW, DEST / "site")
def relink(text, up):
    def sub(m):
        v = html.unescape(m.group(2))
        if v.startswith(("/archive/", "/recovered/")):
            c = classify(v)
            if c["kind"] == "file" and c["media"] in media:
                return f'{m.group(1)}="{up}../media/{quote(c["media"])}"'
            if c.get("original"):
                return f'{m.group(1)}="{html.escape(c["original"])}"'
            return f'{m.group(1)}="#"'
        return m.group(0)
    return re.sub(r'\b(href|src)="([^"]+)"', sub, text)
for f in (DEST / "site").rglob("*.html"):
    text = relink(f.read_text(encoding="utf-8"), "../" if f.parent.name == "a" else "")
    if f.parent.name == "a" and f.stem in site_bodies:
        text = re.sub(r"(<article><h1>.*?</h1>).*(</article>)", lambda m: m.group(1) + "\n" + site_bodies[f.stem] + "\n" + m.group(2), text, flags=re.S)
    f.write_text(text, encoding="utf-8")

# printable dossier: every post, one per page, in date order
parts = []
for p in sorted(posts, key=lambda x: x["date_gmt"] or "", reverse=True):
    art = BeautifulSoup((DEST / "site" / "a" / f"{p['id']}.html").read_text(encoding="utf-8"), "lxml").select_one("article")
    for img in art.find_all("img"):
        if img.get("src", "").startswith("../../"):
            img["src"] = img["src"][3:]
    for a in art.find_all("a"):
        h = a.get("href", "")
        if h.startswith("../../"):
            a["href"] = h[3:]
        elif re.fullmatch(r"[a-z0-9_-]+\.html", h):
            a["href"] = "#" + h[:-5]                                    # link to another post: its section in this dossier
    parts.append(f'<section class="print-post" id="{p['id']}"><p class="pm">{(p["date_europe_rome"] or "")[:10]} · {html.escape(", ".join(p["categories"]))} · '
                 f'<code>{html.escape(p["original_url"])}</code></p>{art.decode_contents()}</section>')
(DEST / "site" / "stampa.html").write_text(f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hermes Center: News & Press 2008–2024 (dossier per la stampa)</title><link rel="stylesheet" href="style.css"></head>
<body class="dossier"><header class="top"><h1>Hermes Center: archivio News & Press 2008–2024</h1>
<p>{len(posts)} articoli ricostruiti dall'archivio del vecchio hermescenter.org, dal più recente. Documento per la revisione: usa Stampa → Salva come PDF.</p>
<p><a href="index.html">← indice di revisione</a></p></header><main>{''.join(parts)}</main></body></html>""", encoding="utf-8")

print(f"posts={len(posts)} media={len(media)} ({sum(r['bytes'] for r in media.values())/1e6:.1f} MB) "
      f"host_sconosciuto={sum(1 for r in media.values() if not r['original_url'])} missing={len(missing)} "
      f"categories={dict(cats)} tags={len(tags)} allineamento={dict(aligned)}")

# the generators themselves, for transparency
shutil.rmtree(DEST / "tools", ignore_errors=True)
(DEST / "tools").mkdir()
for name in ("build_review.py", "export_restoration.py", "fetch_wayback_raw.py"):
    shutil.copy(ROOT / "tools" / name, DEST / "tools" / name)
shutil.copytree(ROOT / "tools" / "review_assets", DEST / "tools" / "review_assets")
