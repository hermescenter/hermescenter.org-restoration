"""Build a local static review site of the old hermescenter.org content (review/).

Sections: News (incl. Press), /it/, Papers & Research, Chi siamo, Progetti.
Each item gets a clean page (content only, local images/documents) and a per-item
decision (ripristina / no / da valutare + note) kept in the browser and exportable as CSV.
Serve the repo root over HTTP and open /review/.
"""
import csv, html, json, posixpath, re, shutil
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parent.parent
SHOW = {"news"}          # sections published in the review site (others: it, papers, chi, progetti)
ARCH, DATA, REC, OUT = ROOT / "archive", ROOT / "data", ROOT / "recovered", ROOT / "review"
HC = re.compile(r"^https?://(?:www\.)?hermescenter\.org(?::80)?/?", re.I)
DOC = re.compile(r"\.(pdf|docx?|odt|xlsx?|ods|pptx?|odp|rtf|zip|mp3|mp4|mov|mpeg)$", re.I)
IMG = re.compile(r"\.(jpe?g|png|gif|webp|svg|ico)$", re.I)
MAGIC = (b"%PDF-", b"\xd0\xcf\x11\xe0", b"PK\x03\x04", b"{\\rtf", b"\x89PNG", b"\xff\xd8\xff", b"GIF8",
         b"RIFF", b"<svg", b"<?xml", b"ID3", b"\x00\x00\x00")
WAYBACK = "https://web.archive.org/web/2024/"

# ---------------------------------------------------------------- local files
local = {}                                   # lowercase path (also without leading domain dir) -> served path
for base, prefix in ((ARCH, "archive"), (REC, "recovered")):   # recovered/ overrides archive/
    for p in base.rglob("*"):
        if p.is_file() and not p.name.endswith(".md"):
            rel = p.relative_to(base).as_posix()
            keys = [rel.lower()]
            m = re.search(r"_(docx?|xlsx?|pptx?|odt|rtf)$", rel, re.I)    # the crawler saved x.doc as x_doc
            if m:
                keys.append((rel[: m.start()] + "." + m.group(1)).lower())
            if "/" in rel and "." in rel.split("/")[0]:
                keys.append(rel.split("/", 1)[1].lower())
            for k in keys:
                if prefix == "recovered" or k not in local:
                    local[k] = f"{prefix}/{rel}"

def valid(served):
    return (ROOT / served).read_bytes()[:8].startswith(MAGIC)

def url_of(served):
    return "/" + quote(served)

# ---------------------------------------------------------------- items
pages = json.loads((DATA / "pages.json").read_text(encoding="utf-8"))
by_file = {p["file"]: p for p in pages}
sections = json.loads((DATA / "sections.json").read_text(encoding="utf-8"))

CHI = re.compile(r"^(home/about-mission|about-us|members|contacts|it/chi-siamo|it/soci|it/contatti|simone-basso|donate|it/dona|privacy)")
PRO = re.compile(r"^(home/projects-technologies|projects|it/progetti|hermes-digital-democracy-unit|it/campagne-2|campagne|it/monitor|donazioni-campagna)")
PAP = re.compile(r"^home/papers-research")

items = []            # dicts: id, section, slug, file, src (path of html), meta
def add(section, slug, src, meta):
    items.append({"section": section, "slug": slug, "src": src, **meta})

# /it/ posts are news too (category "/it/"), except the two calls for collaborators
IT_NOT_NEWS = {"it/sei-un-ricercatore-o-una-ricercatrice", "it/cerchiamo-un-una-consulente-contabile-e-amministrativo"}
for key, sec in (("old|News+Press", "news"), ("old|Press", "news"), ("old|News", "news"),
                 ("old|IT (sezione /it/)", "it"), ("old|Altre categorie", "papers")):
    for i in sections[key]:
        cats = list(i["categories"])
        if sec == "it" and i["slug"] not in IT_NOT_NEWS:
            sec_i, cats = "news", sorted(set(cats) | {"/it/"})
        else:
            sec_i = sec
        add(sec_i, i["slug"], ARCH / i["zip_file"], {"file": i["zip_file"], "published": i["published"],
            "categories": cats, "postid": by_file[i["zip_file"]]["postid"], "origin": "zip"})

for f in sorted((DATA / "wayback" / "articles").glob("*.html")):
    slug = f.stem
    if any(it["slug"] == slug for it in items):
        continue
    s = f.read_text(encoding="utf-8", errors="replace")
    if len(s) < 5000:
        continue
    pub = re.search(r'article:published_time" content="([^"]+)"', s)
    cats = sorted(set(re.findall(r'rel="category tag">([^<]+)<', s)) | set(re.findall(r'article:section" content="([^"]+)"', s)))
    add("news", slug, f, {"file": f.relative_to(ROOT).as_posix(), "published": pub.group(1) if pub else "",
        "categories": cats, "postid": None, "origin": "wayback"})

seen_slugs = {it["slug"] for it in items}
for p in pages:
    f = p["file"]
    if p["kind"] not in ("page", "post") or (p["published"] or "0")[:10] >= "2024-07-01" or f[:-5] in seen_slugs:
        continue
    slug = f[:-5]
    sec = "chi" if CHI.match(slug) else "progetti" if PRO.match(slug) else "papers" if PAP.match(slug) else None
    if sec:
        add(sec, slug, ARCH / f, {"file": f, "published": p["published"], "categories": [], "postid": p["postid"], "origin": "zip"})

# ---------------------------------------------------------------- extraction
STRIP = ("script", "style", "noscript", "form", "#comments", ".comments", "#respond", ".navigation", ".nav-links",
         ".post-navigation", ".sharedaddy", ".jp-relatedposts", ".addtoany_share_save_container", ".wp-block-buttons",
         ".entry-meta", ".entry-footer", "p.data", "#wm-ipp-base", "#wm-ipp", ".edit-link")

def extract(src):
    soup = BeautifulSoup(src.read_text(encoding="utf-8", errors="replace"), "lxml")
    og = soup.find("meta", property="og:title")
    h = soup.select_one(".entry-title") or soup.select_one("#content h1") or soup.find("h1")
    title = (h.get_text(" ", strip=True) if h else "") or (og["content"] if og else "") or src.stem
    title = re.split(r"\s+[|—–-]\s+(?:HERMES|Hermes)", title)[0].strip()
    tags = sorted({a.get_text(strip=True) for a in soup.select('a[rel~="tag"]') if "category" not in a.get("rel", [])})
    author = soup.select_one(".author a, .byline a, a[rel=author]")
    body = (soup.select_one(".entry-content") or soup.select_one("#content-project .section")
            or soup.select_one("#content .section") or soup.select_one("#content"))
    if body is None:
        return title, tags, None, None
    for sel in STRIP:
        for e in body.select(sel):
            e.decompose()
    for e in body.find_all(["h1"]):
        if e.get_text(strip=True) == title:
            e.decompose()
    for c in body.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    return title, tags, (author.get_text(strip=True) if author else ""), body

# ---------------------------------------------------------------- build
def item_id(slug): return re.sub(r"[^a-z0-9_-]+", "__", slug.lower()).strip("_")[:150]

for it in items:
    it["title"], it["tags"], it["author"], it["body"] = extract(it["src"])
    it["text"] = it["body"].get_text(" ", strip=True) if it["body"] else ""
    it["id"] = item_id(it["slug"])
    raw = it["src"].read_text(encoding="utf-8", errors="replace")
    it["is_attach"] = bool(re.search(r'<article[^>]+class="[^"]*type-attachment', raw))
    rel_cats = {html.unescape(c).strip() for c in re.findall(r'rel="category tag"[^>]*>([^<]+)<', raw)}
    if rel_cats:
        it["categories"] = sorted(rel_cats | ({"/it/"} & set(it["categories"])))
    else:
        it["categories"] = [c for c in it["categories"] if c not in it["tags"] and c != "English"]
    if not it["postid"]:
        m = re.search(r'<article[^>]+id="post-(\d+)"', raw)
        it["postid"] = m.group(1) if m else None

# pages exist under several URLs (home/about-mission/people/members/x == members/x): dedupe by postid
# (the oldest theme has no postid: for institutional pages the title identifies the page)
groups, key_of = defaultdict(list), {}
for it in items:
    keys = [(it["section"], "id", it["postid"] or it["slug"])]
    if it["section"] in ("chi", "progetti"):
        keys.append((it["section"], "t", it["title"].lower()))
    k = next((key_of[x] for x in keys if x in key_of), keys[0])
    for x in keys:
        key_of.setdefault(x, k)
    groups[k].append(it)
kept = []
for g in groups.values():
    best = max(g, key=lambda x: (len(x["text"]), x["slug"].count("/")))
    best["aliases"] = sorted({x["slug"] for x in g} - {best["slug"]})
    kept.append(best)

# near-empty institutional pages: WordPress attachment pages (child of another page, one image) or empty in the archive
thin = [it for it in kept if it["section"] in ("chi", "progetti", "papers") and len(it["text"]) < 60
        and (it["body"] is None or len(it["body"].find_all("img")) <= 1)]
parents = {it["slug"] for it in kept}
attach = [it for it in kept if it["is_attach"]] + [
    it for it in thin if not it["is_attach"] and posixpath.dirname(it["slug"]) in parents and it["body"] is not None and it["body"].find("img")]
for it in thin:
    it["empty"] = it not in attach           # shown, flagged: the decision is the reviewer's
items = [it for it in kept if it not in attach and it["body"] is not None and it["section"] in SHOW]
slug2id = {}
for it in items:
    for s in [it["slug"], *it["aliases"]]:
        slug2id[s.lower()] = it["id"]

def resolve(it, url):
    """-> (href, kind, note): kind in item|local|wayback|external."""
    u = html.unescape(url.strip())
    if not u or u.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return u, "raw", ""
    orig = u
    if u.startswith("//"):
        u = "https:" + u
    if re.match(r"^https?://", u, re.I):
        if HC.match(u):
            path = unquote(HC.sub("", u).split("#")[0].split("?")[0]).strip("/")
            return resolve_path(path, "https://www.hermescenter.org/" + path)
        sp = urlsplit(u)
        p = unquote(sp.path).lstrip("/")
        if DOC.search(p) or IMG.search(p):
            for k in (f"{sp.netloc}/{p}".lower(), p.lower()):
                if k in local and valid(local[k]):
                    return url_of(local[k]), "local", orig
        return u, "external", ""
    base = it["file"][:-5] if it["origin"] == "zip" else it["slug"]
    path = posixpath.normpath(posixpath.join(base, unquote(u.split("#")[0].split("?")[0]))).lstrip("./")
    return resolve_path(path, "")

def resolve_path(path, orig):
    p = re.sub(r"_(docx?|xlsx?|pptx?|odt|rtf)$", r".\1", path.strip("/"), flags=re.I)   # crawler: x.doc -> x_doc
    if p.lower() in slug2id:
        return f"{slug2id[p.lower()]}.html", "item", ""
    m = re.search(r"wp-content/uploads/(.+)$", p)
    keys = [p.lower()] + ([f"wp-content/uploads/{m.group(1)}".lower()] if m else [])
    for k in keys:
        if k in local and (DOC.search(k) or IMG.search(k)):
            if valid(local[k]):
                return url_of(local[k]), "local", ""
    if DOC.search(p) or IMG.search(p):
        o = orig or ("https://www.hermescenter.org/" + (f"wp-content/uploads/{m.group(1)}" if m else p))
        return WAYBACK.replace("/2024/", "/2024im_/" if IMG.search(p) else "/2024/") + o, "wayback", ""
    for k in (p.lower() + ".html", p.lower() + "/index.html"):
        if k in local:
            return url_of(local[k]), "archive", ""
    return WAYBACK + (orig or "https://www.hermescenter.org/" + p + "/"), "wayback", ""

OUT.mkdir(exist_ok=True)
(OUT / "a").mkdir(exist_ok=True)

def fmt_date(d): return (d or "")[:10]

def lang(text):
    t = f" {text.lower()} "
    it_ = sum(t.count(w) for w in (" il ", " della ", " che ", " per ", " non ", " sono ", " delle ", " una "))
    en = sum(t.count(w) for w in (" the ", " and ", " of ", " to ", " is ", " that ", " for ", " with "))
    return "IT" if it_ > en else "EN" if en else "?"

SEC = {"news": "News & Press", "it": "/it/ (non news)", "papers": "Papers & Research", "chi": "Chi siamo", "progetti": "Progetti"}
ORDER = [s for s in SEC if s in SHOW]
for sec in ORDER:
    lst = [it for it in items if it["section"] == sec]
    if sec in ("news", "it", "papers"):
        lst.sort(key=lambda x: x["published"] or "", reverse=True)
    else:
        lst.sort(key=lambda x: x["slug"])
    for n, it in enumerate(lst):
        it["prev"] = lst[n - 1]["id"] if n else None
        it["next"] = lst[n + 1]["id"] if n + 1 < len(lst) else None

def page(it):
    body = it["body"]
    stats = Counter()
    for tag, attr in (("a", "href"), ("img", "src"), ("source", "src"), ("iframe", "src"), ("video", "src"), ("audio", "src")):
        for e in body.find_all(tag):
            for a in ("srcset", "sizes", "data-srcset", "loading", "decoding"):
                e.attrs.pop(a, None)
            v = e.get("data-lazy-src") or e.get("data-src") or e.get(attr)
            if not v:
                continue
            href, kind, _ = resolve(it, v)
            e[attr] = href
            if tag == "img":
                stats["img_" + kind] += 1
                if kind == "wayback":
                    e["class"] = e.get("class", []) + ["missing"]
                    e["title"] = "Immagine non presente in locale: caricata da Wayback"
            elif tag == "a":
                path = urlsplit(v).path
                if DOC.search(unquote(path)):
                    stats["doc_" + kind] += 1
                    e["class"] = e.get("class", []) + ["doc", "doc-" + kind]
                elif kind == "external":
                    e["target"] = "_blank"; e["rel"] = "noopener"; e["class"] = e.get("class", []) + ["ext"]
                elif kind == "item":
                    e["class"] = e.get("class", []) + ["int"]
            if tag == "iframe":
                e.replace_with(BeautifulSoup(f'<p class="embed">[contenuto incorporato] <a href="{html.escape(href)}" target="_blank" rel="noopener">{html.escape(href[:90])}</a></p>', "lxml").p)
    it["stats"] = stats
    it["lang"] = lang(it["text"])
    it["words"] = len(it["text"].split())
    orig = "https://www.hermescenter.org/" + it["slug"] + "/"
    aliases = "".join(f'<li><code>/{html.escape(a)}/</code></li>' for a in it["aliases"])
    cats = ", ".join(it["categories"]) or "–"
    nav = lambda i, lbl: f'<a href="{i}.html">{lbl}</a>' if i else f'<span class="off">{lbl}</span>'
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(it['title'])} · Revisione Hermes</title><link rel="stylesheet" href="../style.css"></head>
<body class="article" data-id="{it['id']}">
<header class="bar"><a href="../index.html#{it['section']}">← {SEC[it['section']]}</a><span class="grow"></span>{nav(it['prev'], '‹ prec.')} {nav(it['next'], 'succ. ›')}</header>
<main>
<aside class="meta">
  <div class="decide" data-id="{it['id']}">
    <span>Decisione:</span>
    <button data-v="ripristina">Ripristina</button><button data-v="valuta">Da valutare</button><button data-v="no">Non ripristinare</button>
    <textarea placeholder="Note (facoltative)"></textarea>
  </div>
  <dl>
    <dt>Data</dt><dd>{fmt_date(it['published']) or '–'}</dd>
    <dt>Categorie</dt><dd>{html.escape(cats)}</dd>
    <dt>Tag</dt><dd>{html.escape(', '.join(it['tags']) or '–')}</dd>
    <dt>Autore</dt><dd>{html.escape(it['author'] or '–')}</dd>
    <dt>Lingua</dt><dd>{it['lang']} · {it['words']} parole</dd>
    <dt>URL originale</dt><dd><code>{html.escape(orig)}</code> · <a href="{WAYBACK}{html.escape(orig)}" target="_blank" rel="noopener">Wayback ↗</a></dd>
    {f'<dt>Altri URL</dt><dd><ul>{aliases}</ul></dd>' if aliases else ''}
    <dt>Sorgente</dt><dd><code>{html.escape(it['file'])}</code>{' (scaricato da Wayback)' if it['origin']=='wayback' else ''}</dd>
    <dt>Allegati</dt><dd>{stats['img_local']} immagini locali{f", <b>{stats['img_wayback']} da Wayback</b>" if stats['img_wayback'] else ''}; {stats['doc_local']} documenti locali{f", <b>{stats['doc_wayback']} mancanti</b>" if stats['doc_wayback'] else ''}</dd>
  </dl>
</aside>
<article><h1>{html.escape(it['title'])}</h1>
{body.decode_contents()}
</article></main>
<script src="../app.js"></script></body></html>"""

for it in items:
    (OUT / "a" / f"{it['id']}.html").write_text(page(it), encoding="utf-8")

# ---------------------------------------------------------------- index
CAT_ORDER = ["News", "Press", "/it/"]
def cat_sort(cs): return sorted(cs, key=lambda c: (CAT_ORDER.index(c) if c in CAT_ORDER else 9, c.lower()))
def cat_class(c): return {"News": "news", "Press": "press", "/it/": "it"}.get(c, "other")

def row(it):
    s = it["stats"]
    badges = []
    if it.get("empty"): badges.append('<span class="b warn">vuota nell’originale</span>')
    if it["origin"] == "wayback": badges.append('<span class="b wb">da Wayback</span>')
    if s["img_wayback"] or s["doc_wayback"]: badges.append(f'<span class="b warn" title="allegati non locali">⚠ {s["img_wayback"] + s["doc_wayback"]}</span>')
    where = f'<code>/{html.escape(it["slug"])}/</code>'
    cats = "".join(f'<span class="c c-{cat_class(c)}">{html.escape(c)}</span>' for c in cat_sort(it["categories"])) or '<span class="c c-none">nessuna</span>'
    tags = f'<div class="t">tag: {html.escape(", ".join(it["tags"]))}</div>' if it["tags"] else ""
    return (f'<tr data-id="{it["id"]}" data-lang="{it["lang"]}" data-cat="{html.escape("|".join(it["categories"]))}">'
            f'<td class="d">{fmt_date(it["published"])}</td>'
            f'<td><a href="a/{it["id"]}.html">{html.escape(it["title"])}</a> {" ".join(badges)}<div class="u">{where}</div>{tags}</td>'
            f'<td class="cats">{cats}</td>'
            f'<td class="l">{it["lang"]}</td><td class="n">{s["img_local"] + s["img_wayback"]}</td><td class="n">{s["doc_local"] + s["doc_wayback"]}</td>'
            f'<td class="dec"><select><option value="">–</option><option value="ripristina">Ripristina</option><option value="valuta">Da valutare</option><option value="no">No</option></select></td></tr>')

blocks, toc = [], []
for sec in ORDER:
    lst = [it for it in items if it["section"] == sec]
    if sec in ("news", "it", "papers"):
        lst.sort(key=lambda x: x["published"] or "", reverse=True)
    else:
        lst.sort(key=lambda x: x["slug"])
    dates = sorted(fmt_date(x["published"]) for x in lst if x["published"])
    span = f"{dates[0][:4]}–{dates[-1][:4]}" if dates else ""
    toc.append(f'<a href="#{sec}">{SEC[sec]} <b>{len(lst)}</b></a>')
    blocks.append(f'<section id="{sec}"><h2>{SEC[sec]} <small>{len(lst)} contenuti · {span}</small></h2>'
                  f'<table><thead><tr><th>Data</th><th>Titolo</th><th>Categorie</th><th>Lingua</th><th title="immagini">Img</th><th title="documenti">Doc</th><th>Decisione</th></tr></thead><tbody>'
                  + "".join(row(it) for it in lst) + "</tbody></table></section>")

cat_count = Counter(c for it in items for c in it["categories"])
cat_count["(nessuna)"] = sum(1 for it in items if not it["categories"])
cats_all = cat_sort([c for c in cat_count if c != "(nessuna)" or cat_count[c]])
cat_opts = "".join(f'<option value="{html.escape(c)}">{html.escape(c)} ({cat_count[c]})</option>' for c in cats_all)
cat_chips = "".join(f'<button class="c c-{cat_class(c)}" data-cat="{html.escape(c)}">{html.escape(c)} <b>{cat_count[c]}</b></button>' for c in cats_all)
meta = [{"id": it["id"], "sezione": SEC[it["section"]], "categorie": ", ".join(cat_sort(it["categories"])), "data": fmt_date(it["published"]), "slug": it["slug"],
         "titolo": it["title"], "url": f"https://www.hermescenter.org/{it['slug']}/"} for it in items]
index = f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revisione archivio Hermes</title><link rel="stylesheet" href="style.css"></head><body class="index">
<header class="top"><h1>Revisione archivio hermescenter.org</h1>
<p>Contenuti del vecchio sito (2008–2024) ricostruiti dal backup Wayback, solo per la revisione. Le decisioni restano salvate in questo browser: usa <b>Esporta CSV</b> per condividerle.</p>
<nav class="toc">{''.join(toc)}</nav>
<div class="catsum">Categorie applicate: {cat_chips}</div>
<div class="tools"><input id="q" type="search" placeholder="Cerca nel titolo o nell'URL…">
<select id="fl"><option value="">Tutte le lingue</option><option>IT</option><option>EN</option></select>
<select id="fd"><option value="">Tutte le decisioni</option><option value="none">Non ancora decisi</option><option value="ripristina">Ripristina</option><option value="valuta">Da valutare</option><option value="no">No</option></select>
<select id="fp"><option value="">Tutte le categorie</option>{cat_opts}</select>
<span id="count" class="grow"></span>
<button id="exp">Esporta CSV</button><label class="btn">Importa CSV<input id="imp" type="file" accept=".csv" hidden></label></div></header>
<main>{''.join(blocks)}</main>
<footer><p>Esclusi: {len(attach)} pagine allegato (una sola immagine) e i duplicati della stessa pagina sotto URL diversi (elencati come "Altri URL" nella scheda).</p></footer>
<script>window.ITEMS={json.dumps(meta, ensure_ascii=False)};</script><script src="app.js"></script></body></html>"""
(OUT / "index.html").write_text(index, encoding="utf-8")
shutil.copy(ROOT / "tools" / "review_assets" / "style.css", OUT / "style.css")
shutil.copy(ROOT / "tools" / "review_assets" / "app.js", OUT / "app.js")

print("categorie:", dict(cat_count))
print("contenuti:", Counter(SEC[it["section"]] for it in items), "| allegati esclusi:", len(attach), "| vuote:", sum(bool(it.get("empty")) for it in items))
tot = Counter()
for it in items: tot.update(it["stats"])
print(dict(tot))
