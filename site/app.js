// Review decisions, kept in this browser's localStorage and exportable/importable as CSV.
(function () {
  const K = "hc-review:";
  const get = (id) => { try { return JSON.parse(localStorage.getItem(K + id)) || {}; } catch (e) { return {}; } };
  const put = (id, v) => { try { localStorage.setItem(K + id, JSON.stringify(v)); } catch (e) {} };

  // article page
  const box = document.querySelector(".decide");
  if (box) {
    const id = box.dataset.id, cur = get(id), ta = box.querySelector("textarea");
    const paint = (v) => box.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.v === v));
    paint(cur.d); ta.value = cur.n || "";
    box.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const s = get(id); s.d = s.d === b.dataset.v ? "" : b.dataset.v; put(id, s); paint(s.d);
    }));
    ta.addEventListener("input", () => { const s = get(id); s.n = ta.value; put(id, s); });
    document.addEventListener("keydown", (e) => {
      if (e.target.tagName === "TEXTAREA") return;
      const a = [...document.querySelectorAll(".bar a")];
      if (e.key === "ArrowLeft" && a[1] && a[1].textContent.includes("prec")) location = a[1].href;
      if (e.key === "ArrowRight") { const n = a.find((x) => x.textContent.includes("succ")); if (n) location = n.href; }
    });
    return;
  }

  // index page
  const rows = [...document.querySelectorAll("tr[data-id]")];
  const q = document.getElementById("q"), fl = document.getElementById("fl"), fd = document.getElementById("fd"), fp = document.getElementById("fp");
  const load = () => rows.forEach((r) => { const s = get(r.dataset.id); r.dataset.dec = s.d || ""; r.querySelector("select").value = s.d || ""; });
  const filter = () => {
    const t = q.value.trim().toLowerCase(); let shown = 0; const c = { ripristina: 0, valuta: 0, no: 0 };
    rows.forEach((r) => {
      const d = r.dataset.dec; if (c[d] !== undefined) c[d]++;
      const ok = (!t || r.textContent.toLowerCase().includes(t)) && (!fl.value || r.dataset.lang === fl.value) &&
        (!fd.value || (fd.value === "none" ? !d : d === fd.value)) && (!fp.value || (fp.value === "(nessuna)" ? !r.dataset.cat : r.dataset.cat.split("|").includes(fp.value)));
      r.classList.toggle("hide", !ok); if (ok) shown++;
    });
    document.getElementById("count").textContent =
      `${shown}/${rows.length} visibili · ripristina ${c.ripristina} · da valutare ${c.valuta} · no ${c.no}`;
  };
  rows.forEach((r) => r.querySelector("select").addEventListener("change", (e) => {
    const s = get(r.dataset.id); s.d = e.target.value; put(r.dataset.id, s); r.dataset.dec = s.d; filter();
  }));
  [q, fl, fd, fp].forEach((el) => el.addEventListener("input", filter));
  document.querySelectorAll(".catsum button").forEach((b) => b.addEventListener("click", () => {
    fp.value = fp.value === b.dataset.cat ? "" : b.dataset.cat; filter();
    document.querySelectorAll(".catsum button").forEach((x) => x.classList.toggle("on", x.dataset.cat === fp.value));
  }));

  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  document.getElementById("exp").addEventListener("click", () => {
    const head = ["id", "sezione", "categorie", "data", "slug", "titolo", "url", "decisione", "note"];
    const lines = [head.join(",")].concat(window.ITEMS.map((it) => {
      const s = get(it.id); return [it.id, it.sezione, it.categorie, it.data, it.slug, it.titolo, it.url, s.d || "", s.n || ""].map(esc).join(",");
    }));
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" }));
    a.download = "revisione_hermes_" + new Date().toISOString().slice(0, 10) + ".csv"; a.click();
  });
  document.getElementById("imp").addEventListener("change", async (e) => {
    const f = e.target.files[0]; if (!f) return;
    const txt = (await f.text()).replace(/^﻿/, "");
    const parse = (line) => { const out = []; let cur = "", qd = false;
      for (let i = 0; i < line.length; i++) { const ch = line[i];
        if (qd) { if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') qd = false; else cur += ch; }
        else if (ch === '"') qd = true; else if (ch === ",") { out.push(cur); cur = ""; } else cur += ch; }
      out.push(cur); return out; };
    const recs = []; let buf = "";
    for (const line of txt.split("\n")) { buf = buf ? buf + "\n" + line : line; if ((buf.match(/"/g) || []).length % 2 === 0) { recs.push(parse(buf.replace(/\r$/, ""))); buf = ""; } }
    const h = recs.shift(), iid = h.indexOf("id"), idd = h.indexOf("decisione"), idn = h.indexOf("note"); let n = 0;
    recs.forEach((r) => { if (r[iid]) { put(r[iid], { d: r[idd] || "", n: r[idn] || "" }); n++; } });
    load(); filter(); alert(n + " decisioni importate");
  });
  load(); filter();
})();
