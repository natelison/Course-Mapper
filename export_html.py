# export_html.py
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Tuple
import html as _html
from cm_shared import (
    node_type, is_ultra_page, is_document_handler, external_link_url,
    parse_embedded_files_from_body, parse_embedded_content_links
)

def build_html(course_label: str,
               roots: List[Dict[str, Any]],
               kids: Mapping[str, List[Dict[str, Any]]],
               by_id: Mapping[str, Dict[str, Any]],
               show_bodies: bool,
               host: str,
               course_pk1: str,
               tree_file_limit: Optional[int]) -> str:
    """
    Collapsible HTML tree with file badges + improved search/highlight (live, correct match counts).
    """

    # ----- tiny helpers -----
    def chip(typ: str) -> str:
        cls = {
            "ULTRA DOC": "chip-ultra-doc",
            "UltraBody": "chip-ultrabody",
            "Document": "chip-document",
            "Folder": "chip-folder",
            "MODULE": "chip-module",
            "VideoStudio": "chip-videostudio",
            "Link": "chip-link",
            "COURSE LINK": "chip-course-link",
            "LTI": "chip-lti",
            "SCORM": "chip-scorm",
            "FORM": "chip-form",
            "TEST/ASSIGNMENT": "chip-test-assignment",
            "FILE": "chip-file",
        }.get(typ, "chip-unknown")
        return f'<span class="chip {cls}">{_html.escape(typ)}</span>'

    def url_for_display(item: Dict[str, Any]) -> str:
        from cm_shared import is_external_link
        return external_link_url(item) if is_external_link(item) else ""

    def ext_class(name: str) -> str:
        n = (name or "").lower().strip()
        if "." in n:
            return "ext-" + n.rsplit(".", 1)[-1]
        return ""

    def files_to_badges(files: List[Dict[str, str]], limit: Optional[int]) -> str:
        if not files:
            return ""
        names = [f.get("name", "") for f in files if f.get("name")]
        if limit is not None and len(names) > limit:
            extra = len(names) - limit
            names = names[:limit] + [f"… (+{extra} more)"]
        parts = ['<div class="files files-badges"><span class="files-label">Files</span> ']
        for nm in names:
            cls = "file-badge " + ext_class(nm)
            parts.append(f'<span class="{cls}">{_html.escape(nm)}</span>')
        parts.append("</div>")
        return "".join(parts)

    def render_files_badges(files: List[Dict[str, str]]) -> str:
        return files_to_badges(files, tree_file_limit)

    def body_source_for_node(node: Dict[str, Any]) -> str:
        typ = node_type(node)
        if typ in ("ULTRA DOC", "Document", "UltraBody"):
            return node.get("body") or ""
        if is_ultra_page(node):
            for c in kids.get(node.get("id", ""), []):
                if is_document_handler(c):
                    return c.get("body") or ""
        return ""

    def embedded_for_node(node: Dict[str, Any]) -> Tuple[List[Dict[str, str]], List[Tuple[str, str]]]:
        body = body_source_for_node(node)
        files = parse_embedded_files_from_body(body)
        links = [(cid, lt) for (cid, lt) in parse_embedded_content_links(body) if (lt or "").lower() != "knowledgecheck"]
        return files, links

    def try_ultra_merge(node: Dict[str, Any]):
        if not is_ultra_page(node):
            return None
        nid = node.get("id", "")
        doc_child = None
        for c in kids.get(nid, []):
            if is_document_handler(c):
                doc_child = c
                break
        if not doc_child:
            return None

        merged_children: List[Dict[str, Any]] = []
        for c in kids.get(nid, []):
            if c is doc_child: continue
            if show_bodies or node_type(c) != "UltraBody":
                merged_children.append(c)
        for gc in kids.get(doc_child.get("id", ""), []):
            if show_bodies or node_type(gc) != "UltraBody":
                merged_children.append(gc)

        merged_title = node.get("title") or (doc_child.get("title") or "")
        return merged_title, doc_child, merged_children

    # ----- recursive render -----
    def render_node(node: Dict[str, Any]) -> str:
        typ = node_type(node)
        title = (node.get("title") or "").strip()
        href = url_for_display(node)

        merged = try_ultra_merge(node)
        if merged:
            merged_title, doc_child, merged_children = merged
            files, links = embedded_for_node(node)
            parts = [
                "<li><details>",
                f"<summary>{chip('ULTRA DOC')}{_html.escape(merged_title)}</summary>",
            ]
            if files:
                parts.append(render_files_badges(files))
            if links:
                links_txt = "; ".join(f"{_html.escape(cid)} ({_html.escape(lt)})" for cid, lt in links)
                parts.append(f'<div class="files">[Embedded content links: {links_txt}]</div>')
            if merged_children:
                parts.append("<ul>")
                for c in merged_children:
                    if not show_bodies and node_type(c) == "UltraBody": continue
                    parts.append(render_node(c))
                parts.append("</ul>")
            parts.append("</details></li>")
            return "".join(parts)

        label = f"{chip(typ)}{_html.escape(title)}"
        url_suffix = f'  [URL: <a href="{_html.escape(href)}" target="_blank" rel="noopener">{_html.escape(href)}</a>]' if href else ""

        children = kids.get(node.get("id", ""), [])
        show_children = [c for c in children if show_bodies or node_type(c) != "UltraBody"]

        extras_html = ""
        if typ in ("ULTRA DOC", "Document") or is_ultra_page(node):
            files, links = embedded_for_node(node)
            if files: extras_html += render_files_badges(files)
            if links:
                links_txt = "; ".join(f"{_html.escape(cid)} ({_html.escape(lt)})" for cid, lt in links)
                extras_html += f'<div class="files">[Embedded content links: {links_txt}]</div>'

        if show_children:
            out = ["<li><details>"]
            out.append(f"<summary>{label}{url_suffix}</summary>")
            if extras_html: out.append(extras_html)
            out.append("<ul>")
            for c in show_children:
                out.append(render_node(c))
            out.append("</ul></details></li>")
            return "".join(out)
        else:
            out = [f"<li>{label}{url_suffix}</li>"]
            if extras_html:
                out = ["<li><details open><summary>" + label + "</summary>", extras_html, "</details></li>"]
            return "".join(out)

    # ----- document -----
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Course Map — { _html.escape(course_label) }</title>
<style>
/* (styles unchanged from your current file; keeping them inline here) */

/* ===== Course Map — Polished UI (with header card) ===== */
:root{{ --bg:#0b0c0d00; --surface:#fff; --surface-2:#f7f8fa; --ink:#0f172a; --muted:#6b7280; --ring:#3b82f6; --border:#e5e7eb; --chip-ink-dark:#0b0f19;
 --blue-600:#2563eb; --blue-500:#3b82f6; --blue-400:#60a5fa; --violet-500:#8b5cf6; --violet-600:#7c3aed; --purple-500:#a855f7; --red-500:#ef4444;
 --emerald-500:#10b981; --green-500:#22c55e; --sky-500:#0ea5e9; --amber-500:#f59e0b; --amber-400:#fbbf24; --orange-500:#f97316; --stone-500:#6b7280; --slate-400:#94a3b8;
 --shadow-sm:0 1px 2px rgba(16,24,40,.06),0 1px 1px rgba(16,24,40,.04); --shadow-md:0 6px 20px rgba(2,6,23,.08); }}
@media (prefers-color-scheme: dark){{
  :root{{ --surface:#0b1220; --surface-2:#0e1626; --ink:#e5e7eb; --muted:#94a3b8; --ring:#60a5fa; --border:#1f2937;
          --shadow-sm:0 1px 2px rgba(0,0,0,.35); --shadow-md:0 10px 30px rgba(0,0,0,.35); }}
}}
html,body{{height:100%}}
body{{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;line-height:1.5;color:var(--ink);background:var(--bg)}}
.page-header{{position:sticky;top:0;z-index:4;background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:12px 16px 10px;margin:0 0 16px;box-shadow:var(--shadow-sm);backdrop-filter:blur(6px)}}
.page-header h1{{margin:0 0 6px;font-size:24px;font-weight:600;color:var(--ink)}}
.page-header .meta{{margin:0;font-size:.9em;color:var(--muted)}}
@media (prefers-color-scheme: dark){{.page-header{{background:var(--surface-2)}}}}
.controls{{position:sticky;top:70px;z-index:3;display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:14px 0 18px;padding:10px 12px;background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow-sm);backdrop-filter:blur(6px)}}
input[type="search"]{{padding:10px 36px 10px 36px;min-width:min(520px,100%);border:1px solid var(--border);border-radius:10px;background:
url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='8'/><path d='m21 21-3.5-3.5'/></svg>") no-repeat 10px 50%, var(--surface-2);color:var(--ink);outline:none;transition:box-shadow .18s ease,border-color .18s ease,background-color .18s ease}}
input[type="search"]::placeholder{{color:var(--muted)}}
input[type="search"]:focus{{border-color:color-mix(in oklab,var(--ring) 65%,var(--border));box-shadow:0 0 0 3px color-mix(in oklab,var(--ring) 22%,transparent)}}
button{{padding:9px 12px;border:1px solid var(--border);background:linear-gradient(180deg,var(--surface),var(--surface-2));border-radius:10px;cursor:pointer;color:var(--ink);box-shadow:var(--shadow-sm);transition:transform .06s ease,box-shadow .18s ease,border-color .18s ease}}
button:hover{{transform:translateY(-1px);box-shadow:var(--shadow-md)}}
button:active{{transform:translateY(0) scale(.98)}}
button:focus-visible{{outline:none;box-shadow:0 0 0 3px color-mix(in oklab,var(--ring) 25%,transparent),var(--shadow-md);border-color:var(--ring)}}
#count{{margin-left:auto;padding:4px 8px;background:var(--surface-2);border:1px solid var(--border);border-radius:999px;font-size:.85em}}
ul{{list-style:none;padding-left:0;margin:0}}
#tree{{border:1px solid var(--border);border-radius:14px;background:var(--surface);box-shadow:var(--shadow-sm);padding:8px 8px 10px}}
#tree>li{{margin:6px 8px}} #tree li{{position:relative;margin:4px 4px;padding-left:22px}}
#tree li::before{{content:"";position:absolute;left:9px;top:.8em;width:10px;height:1px;background:var(--border)}}
#tree ul{{margin-left:12px;padding-left:12px;border-left:1px dashed var(--border)}}
details>summary{{cursor:pointer;user-select:none;list-style:none;padding:6px 8px;margin:-6px -8px;border-radius:8px;transition:background-color .18s ease,color .18s ease}}
details>summary::-webkit-details-marker{{display:none}}
details>summary::before{{content:"";display:inline-block;width:9px;height:9px;margin-right:8px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(-45deg) translateY(-1px);transition:transform .18s ease,border-color .18s ease}}
details[open]>summary::before{{transform:rotate(45deg) translateY(-1px);border-color:var(--ring)}}
details>summary:hover{{background:var(--surface-2)}} details[open]>summary{{color:color-mix(in oklab,var(--ink) 86%,var(--ring))}}
.files{{color:var(--muted);margin:4px 0 6px 22px;font-size:.92em;padding:6px 10px;background:color-mix(in oklab,var(--surface-2) 86%,transparent);border:1px dashed var(--border);border-radius:10px;backdrop-filter:blur(2px)}}
.files-badges{{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:6px 0 8px 22px;padding:8px 10px;background:color-mix(in oklab,var(--surface-2) 92%,transparent);border:1px solid var(--border);border-left:4px solid var(--ring);border-radius:10px;color:var(--ink)}}
.files-label{{font-size:.72em;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:2px 6px}}
.file-badge{{display:inline-flex;align-items:center;padding:3px 10px;background:var(--surface);border:1px solid var(--border);border-radius:999px;font-size:.9em;box-shadow:var(--shadow-sm);white-space:nowrap}}
.file-badge.ext-pdf{{border-color:var(--red-500)}}
.file-badge.ext-doc,.file-badge.ext-docx{{border-color:var(--blue-500)}}
.file-badge.ext-xls,.file-badge.ext-xlsx{{border-color:var(--green-500)}}
.file-badge.ext-ppt,.file-badge.ext-pptx{{border-color:var(--orange-500)}}
.file-badge.ext-zip{{border-color:var(--amber-500)}}
.file-badge.ext-jpg,.file-badge.ext-jpeg,.file-badge.ext-png,.file-badge.ext-gif,.file-badge.ext-webp{{border-color:var(--emerald-500)}}
.chip{{margin-right:6px;display:inline-flex;align-items:center;gap:6px;padding:2px 8px;border-radius:999px;font-size:.78em;line-height:1.6;color:#fff;box-shadow:inset 0 -1px 0 rgba(255,255,255,.15),var(--shadow-sm);border:1px solid rgba(255,255,255,.15);vertical-align:text-bottom;letter-spacing:.2px}}
.chip-ultra-doc{{background:linear-gradient(180deg,var(--blue-600),color-mix(in oklab,var(--blue-600) 70%,#000))}}
.chip-document{{background:linear-gradient(180deg,var(--blue-500),color-mix(in oklab,var(--blue-500) 70%,#000))}}
.chip-ultrabody{{background:linear-gradient(180deg,var(--blue-400),color-mix(in oklab,var(--blue-400) 65%,#000))}}
.chip-folder{{background:linear-gradient(180deg,var(--violet-500),color-mix(in oklab,var(--violet-500) 70%,#000))}}
.chip-module{{background:linear-gradient(180deg,var(--purple-500),color-mix(in oklab,var(--purple-500) 68%,#000))}}
.chip-videostudio{{background:linear-gradient(180deg,var(--red-500),color-mix(in oklab,var(--red-500) 70%,#000))}}
.chip-link{{background:linear-gradient(180deg,var(--emerald-500),color-mix(in oklab,var(--emerald-500) 70%,#000))}}
.chip-course-link{{background:linear-gradient(180deg,var(--green-500),color-mix(in oklab,var(--green-500) 68%,#000))}}
.chip-lti{{background:linear-gradient(180deg,var(--sky-500),color-mix(in oklab,var(--sky-500) 70%,#000))}}
.chip-scorm{{background:linear-gradient(180deg,var(--amber-500),var(--amber-400));color:var(--chip-ink-dark)}}
.chip-form{{background:linear-gradient(180deg,var(--amber-400),#ffd54a);color:var(--chip-ink-dark)}}
.chip-test-assignment{{background:linear-gradient(180deg,var(--orange-500),color-mix(in oklab,var(--orange-500) 70%,#000))}}
.chip-file{{background:linear-gradient(180deg,var(--stone-500),color-mix(in oklab,var(--stone-500) 68%,#000))}}
.chip-unknown{{background:linear-gradient(180deg,var(--slate-400),color-mix(in oklab,var(--slate-400) 65%,#000))}}
#tree li:hover{{background:color-mix(in oklab,var(--surface-2) 72%,transparent);border-radius:8px}}
#tree a{{color:var(--blue-500);text-decoration:underline dotted}} #tree a:hover{{text-decoration:underline}}
.hidden{{display:none !important}}
:focus-visible{{outline:3px solid color-mix(in oklab,var(--ring) 35%,transparent);outline-offset:2px;border-radius:8px}}
@media print{{body{{margin:12px;background:#fff}} .controls,#count,.page-header{{display:none !important}} #tree{{box-shadow:none;border-color:#ddd}} a[href^="http"]::after{{content:" (" attr(href) ")";color:#555;font-size:.9em}}}}
</style>
</head>
<body>
  <header class="page-header">
    <h1>Course Map — { _html.escape(course_label) }</h1>
    <div class="meta">Generated { _html.escape(generated) }</div>
  </header>

  <div class="controls">
    <input id="q" type="search" placeholder="Search title/files/type…">
    <button id="expand">Expand all</button>
    <button id="collapse">Collapse all</button>
    <span id="count" class="meta"></span>
  </div>

  <ul id="tree">
"""
    body_parts: List[str] = [render_node(r) for r in roots]

    # (JS = your latest version with highlight + correct counting)
    tail = """
  </ul>

<script>
(function () {
  const q = document.getElementById('q');
  const tree = document.getElementById('tree');
  const expandBtn = document.getElementById('expand');
  const collapseBtn = document.getElementById('collapse');
  const count = document.getElementById('count');

  (function injectStyles(){
    if (document.getElementById('search-highlight-styles')) return;
    const s = document.createElement('style');
    s.id = 'search-highlight-styles';
    s.textContent = `
      :root{ --hit-bg:#fde047; --hit-ring:#f59e0b; }
      mark.hit{ background:var(--hit-bg); color:#0b0f19; padding:0 .2em; border-radius:.25rem; }
      li.has-hit > details > summary{ outline:2px solid var(--hit-ring); outline-offset:2px; border-radius:.5rem; }
      li.has-hit .files-badges, li.has-hit .files{ box-shadow:0 0 0 2px var(--hit-ring) inset; border-radius:.5rem; }
    `;
    document.head.appendChild(s);
  })();

  function debounce(fn, ms = 80){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }
  function setAll(open){ tree.querySelectorAll('details').forEach(d => d.open = open); }
  function updateCount(n){ count.textContent = n ? n + ' match' + (n===1?'':'es') : ''; }
  function escapeRe(s){ return s.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'); } // safe in f-string

  function markSearchOpen(d){ if (d && d.tagName === 'DETAILS'){ d.open = true; d.dataset.searchOpen = '1'; } }

  function openAncestors(el){
    let cur = el;
    while (cur) {
      if (cur.tagName === 'DETAILS') markSearchOpen(cur);
      if (cur.matches?.('li')) {
        const row = cur.querySelector(':scope > details');
        if (row) markSearchOpen(row);
      }
      cur = cur.parentElement;
    }
  }

  function rememberOriginal(el){
    if (!el.dataset.origHtml) el.dataset.origHtml = el.innerHTML;
    else el.innerHTML = el.dataset.origHtml;
  }
  function clearHighlights(){
    tree.querySelectorAll('summary, .files, .files-badges').forEach(el => {
      if (el.dataset.origHtml != null) el.innerHTML = el.dataset.origHtml;
    });
    tree.querySelectorAll('li.has-hit').forEach(li => li.classList.remove('has-hit'));
  }

  function highlightInElement(root, term){
    if (!term || !root) return 0;
    rememberOriginal(root);
    const re = new RegExp(escapeRe(term), 'gi');

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node){
        return node.nodeValue && node.nodeValue.trim()
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT;
      }
    });

    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    let totalHits = 0;
    for (const textNode of nodes){
      const value = textNode.nodeValue;
      let m, last = 0, changed = false;
      re.lastIndex = 0;

      const frag = document.createDocumentFragment();
      while ((m = re.exec(value)) !== null){
        changed = true;
        totalHits++;
        if (m.index > last) frag.appendChild(document.createTextNode(value.slice(last, m.index)));
        const mark = document.createElement('mark'); mark.className = 'hit'; mark.textContent = m[0];
        frag.appendChild(mark);
        last = m.index + m[0].length;
        if (re.lastIndex === m.index) re.lastIndex++;
      }
      if (changed){
        if (last < value.length) frag.appendChild(document.createTextNode(value.slice(last)));
        textNode.parentNode.replaceChild(frag, textNode);
      }
    }
    return totalHits;
  }

  function matches(li, term){
    if (!term) return { hits:0, matched:true };
    let hits = 0;

    const sum = li.querySelector(':scope > details > summary') || li.querySelector(':scope > summary');
    const h1 = highlightInElement(sum, term);
    if (h1 > 0){ li.classList.add('has-hit'); openAncestors(sum); }
    hits += h1;

    const candidates = li.querySelectorAll(
      ':scope > .files, :scope > .files-badges, :scope details .files, :scope details .files-badges'
    );
    for (const node of candidates){
      const h = highlightInElement(node, term);
      if (h > 0){ li.classList.add('has-hit'); openAncestors(node); }
      hits += h;
    }

    return { hits, matched: hits > 0 };
  }

  function filter(){
    const term = q.value.trim();

    tree.querySelectorAll('details[data-search-open="1"]').forEach(d => { d.open = false; delete d.dataset.searchOpen; });
    clearHighlights();

    let totalHits = 0;
    tree.querySelectorAll(':scope > li').forEach(root => {
      (function visit(li){
        const kids = Array.from(li.querySelectorAll(':scope > ul > li'));
        kids.forEach(visit);
        const { hits: selfHits, matched } = matches(li, term);
        const childVisible = kids.some(k => !k.classList.contains('hidden'));
        const visible = matched || childVisible;
        li.classList.toggle('hidden', !visible);
        totalHits += selfHits;
      })(root);
    });

    updateCount(totalHits);
    const firstHit = tree.querySelector('mark.hit');
    if (firstHit) firstHit.scrollIntoView({ block: 'nearest' });
  }

  q.addEventListener('input', debounce(filter, 80));
  expandBtn.addEventListener('click', () => setAll(true));
  collapseBtn.addEventListener('click', () => setAll(false));
  filter();
})();
</script>

</body>
</html>
"""
    return head + "".join(body_parts) + tail
