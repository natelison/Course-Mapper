# cm_shared.py
import html
import json
import os
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

# -------- content handler helpers --------
def handler_id(item: Dict[str, Any]) -> str:
    return ((item.get("contentHandler") or {}).get("id") or "").lower()

def ch_bool(item: Dict[str, Any], key: str) -> bool:
    ch = item.get("contentHandler") or {}
    return bool(ch.get(key))

def is_external_link(item: Dict[str, Any]) -> bool:
    return handler_id(item) == "resource/x-bb-externallink"

def external_link_url(item: Dict[str, Any]) -> str:
    ch = item.get("contentHandler") or {}
    return (ch.get("url") or ch.get("launchUrl") or "").strip()

def is_ultra_page(item: Dict[str, Any]) -> bool:
    return handler_id(item) == "resource/x-bb-folder" and ch_bool(item, "isBbPage")

def is_document_handler(item: Dict[str, Any]) -> bool:
    return handler_id(item).startswith("resource/x-bb-document")

# -------- type classification (matches your previous logic) --------
def node_type(item: Dict[str, Any]) -> str:
    h = (item.get("contentHandler") or {}).get("id", "").lower()
    title_lc = (item.get("title") or "").strip().lower()

    if h.startswith("resource/x-bb-document"):
        return "UltraBody" if title_lc in {"ultradocumentbody", "documentbody"} else "ULTRA DOC"

    if ("x-bb-lesson" in h) or ("learningmodule" in h) or ("learning-module" in h) or ("learning" in h and "module" in h):
        return "MODULE"

    if "folder" in h:
        return "Folder"

    if "externallink" in h:
        return "Link"
    if "courselink" in h:
        return "COURSE LINK"
    if "file" in h:
        return "FILE"

    if "asmt-survey-link" in h:
        return "FORM"
    if "asmt-test-link" in h or "assignment" in h:
        return "TEST/ASSIGNMENT"

    if "plugin-scormengine" in h:
        return "SCORM"

    if "x-bb-blti-link" in h or "bltiplacement" in h:
        return "LTI"

    body_lc = (item.get("body") or "").lower()
    if 'data-bbtype="video-studio"' in body_lc:
        return "VideoStudio"

    return "Unknown"

def is_ultra_body(item: Dict[str, Any]) -> bool:
    return node_type(item) == "UltraBody"

# -------- embedded parsers --------
_DATA_BBFILE_RE = re.compile(r'data-bbfile\s*=\s*"([^"]+)"', re.I)
_CONTENT_LINK_PAIR_RE = re.compile(
    r'data-content-link\s*=\s*"([^"]+)"[^>]*data-content-link-type\s*=\s*"([^"]+)"'
    r'|data-content-link-type\s*=\s*"([^"]+)"[^>]*data-content-link\s*=\s*"([^"]+)"',
    re.I
)

OPENXML_MAP = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
}
LEGACY_MS_MAP = {
    "application/msword": "doc",
    "application/vnd.ms-excel": "xls",
    "application/vnd.ms-powerpoint": "ppt",
}

def mime_family(mime: str) -> str:
    mime = (mime or "").lower().strip()
    if mime in OPENXML_MAP: return OPENXML_MAP[mime]
    if mime in LEGACY_MS_MAP: return LEGACY_MS_MAP[mime]
    if "/" in mime: return mime.split("/")[-1]
    return mime or ""

def parse_embedded_files_from_body(body_html: str) -> List[Dict[str, str]]:
    if not body_html: return []
    out: List[Dict[str, str]] = []
    for m in _DATA_BBFILE_RE.finditer(body_html):
        raw = m.group(1)
        try:
            decoded = html.unescape(raw)
            obj = json.loads(decoded)
            name = str(obj.get("linkName") or obj.get("alternativeText") or "").strip()
            mime = str(obj.get("mimeType") or "").strip()
            render = str(obj.get("render") or "").strip()
            if name:
                out.append({"name": name, "mime": mime, "render": render})
        except Exception:
            continue
    return out

def parse_embedded_content_links(body_html: str) -> List[Tuple[str, str]]:
    if not body_html: return []
    out: List[Tuple[str, str]] = []
    for m in _CONTENT_LINK_PAIR_RE.finditer(body_html):
        if m.group(1) is not None:
            cid, ltype = m.group(1), m.group(2) or ""
        else:
            ltype, cid = m.group(3) or "", m.group(4)
        cid = (cid or "").strip()
        ltype = (ltype or "").strip()
        if cid:
            out.append((cid, ltype))
    return out

# -------- shared formatting helpers --------
def safe_slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", (s or "").strip()).strip("_")

def compute_path(item: Dict[str, Any], by_id: Mapping[str, Dict[str, Any]]) -> str:
    names: List[str] = []
    seen = set()
    cur: Optional[Dict[str, Any]] = item
    while cur and cur.get("id") not in seen:
        seen.add(cur.get("id"))
        name = (cur.get("title") or "").strip() or handler_id(cur)
        names.append(name)
        pid = cur.get("parentId")
        cur = by_id.get(pid) if pid else None
    names.reverse()
    return " / ".join(names)

def files_csv_field(files: List[Dict[str, str]]) -> str:
    return "; ".join([f"{f.get('name','')}|{f.get('mime','')}|{f.get('render','')}" for f in files])

def content_links_csv_field(links: List[Tuple[str, str]]) -> str:
    return "; ".join([f"{cid}|{lt}" for cid, lt in links])

def format_files_for_tree(files: List[Dict[str, str]], limit: Optional[int]) -> str:
    parts: List[str] = []
    for f in files:
        kind = mime_family(f.get("mime", ""))
        render = (f.get("render") or "").lower() or "inline"
        parts.append(f"{f.get('name','')} ({render}, {kind})")
    if limit is not None and len(parts) > limit:
        shown = parts[:limit]
        extra = len(parts) - limit
        shown.append(f"… (+{extra} more)")
        parts = shown
    return ("Files: " + "; ".join(parts)) if parts else ""

def format_file_names_for_tree(files: List[Dict[str, str]], limit: Optional[int]) -> str:
    names = [f.get("name", "") for f in files if f.get("name")]
    if limit is not None and len(names) > limit:
        shown = names[:limit]
        extra = len(names) - limit
        shown.append(f"… (+{extra} more)")
        names = shown
    return ("Files: " + "; ".join(names)) if names else ""
