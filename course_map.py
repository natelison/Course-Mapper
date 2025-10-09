#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map a Blackboard course's content layout and export as:
- TXT (tree)
- CSV (full data incl. embedded files/links)
- HTML (collapsible, searchable tree with color-coded type chips)

Credentials:
- Pass via CLI (--key/--secret/--host), or
- Set env vars (BB_KEY / BB_SECRET / BB_HOST), or
- Provide a TOML file via --config, with:
    [blackboard]
    host = "https://blackboard.example.edu"
    key = "..."
    secret = "..."
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

from pathlib import Path

import requests

from cm_shared import safe_slug
from export_txt import draw_tree_txt
from export_csv import write_csv_map
from export_html import build_html


# -------- HTTP helpers --------
def get_token(host: str, key: str, secret: str) -> str:
    url = f"{host}/learn/api/public/v1/oauth2/token"
    resp = requests.post(url, data={"grant_type": "client_credentials"}, auth=(key, secret), timeout=30)
    if not resp.ok:
        raise SystemExit(f"OAuth token request failed: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def bb_get(session: requests.Session, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    r = session.get(url, params=params or {}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"GET failed {r.status_code}: {url}\n{r.text}")
    return r.json()


def normalize_next_url(host: str, next_url: str) -> str:
    if next_url.startswith(("http://", "https://")):
        return next_url
    if next_url.startswith("/"):
        return host.rstrip("/") + next_url
    return host.rstrip("/") + "/" + next_url


def paged_get(session: requests.Session, host: str, url: str, params: Optional[Dict[str, Any]] = None) -> Iterable[Dict[str, Any]]:
    data = bb_get(session, url, params=params)
    yield data
    while isinstance(data, dict) and data.get("paging") and data["paging"].get("nextPage"):
        next_url = normalize_next_url(host, data["paging"]["nextPage"])
        data = bb_get(session, next_url)
        yield data


# -------- course fetch + indexing --------
def build_course_contents_url(host: str, course_id: str) -> str:
    cid = course_id.strip()
    if cid.startswith("_") and "_" in cid[1:]:
        return f"{host}/learn/api/public/v1/courses/{cid}/contents"
    else:
        return f"{host}/learn/api/public/v1/courses/courseId:{cid}/contents"


def resolve_course_pk1(session: requests.Session, host: str, course_id: str) -> str:
    cid = course_id.strip()
    if cid.startswith("_") and "_" in cid[1:]:
        return cid
    try:
        data = bb_get(session, f"{host}/learn/api/public/v1/courses/courseId:{cid}")
        pk1 = data.get("id") or ""
        return pk1 if isinstance(pk1, str) else ""
    except Exception:
        return ""


def fetch_course_meta(session: requests.Session, host: str, course_pk1: str) -> tuple[str, str]:
    data = bb_get(session, f"{host}/learn/api/public/v1/courses/{course_pk1}", params={"fields": "id,courseId,name"})
    return (data.get("courseId") or "", data.get("name") or "")


def fetch_all_contents(session: requests.Session, host: str, course_id: str) -> List[Dict[str, Any]]:
    base = build_course_contents_url(host, course_id)
    params = {
        "recursive": "true",
        "expand": "body,availability,contentHandler",
        "fields": "id,title,parentId,position,webUrl,links,availability,contentHandler,created,modified,body",
        "limit": 200,
    }
    items: List[Dict[str, Any]] = []
    for page in paged_get(session, host, base, params=params):
        items.extend(page.get("results", []))
    return items


def index_by_id(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {it["id"]: it for it in items if isinstance(it.get("id"), str) and it.get("id")}


def children_index(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_parent: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        pid_raw = it.get("parentId")
        pid: str = pid_raw if isinstance(pid_raw, str) else ""  # ensure str key
        by_parent.setdefault(pid, []).append(it)

    # stable sort per parent: position (ints first) then title
    for _pid, arr in by_parent.items():
        arr.sort(
            key=lambda x: (
                x.get("position") if isinstance(x.get("position"), int) else 10_000_000,
                (x.get("title") or ""),
            )
        )
    return by_parent


# -------- config / creds (TOML) --------
def _load_toml(path: str) -> dict:
    """Load TOML using stdlib tomllib (3.11+) or tomli if available."""
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    data = p.read_bytes()
    try:
        import tomllib  # Python 3.11+
        return tomllib.loads(data.decode("utf-8"))
    except Exception:
        try:
            import tomli  # type: ignore
        except Exception:
            raise SystemExit(
                "To use --config TOML on Python < 3.11, please `pip install tomli`, or upgrade to 3.11+."
            )
        return tomli.loads(data.decode("utf-8"))


def resolve_credentials(args) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Precedence: CLI > Env > TOML (--config)
    - CLI: --key / --secret / --host
    - Env: BB_KEY / BB_SECRET / BB_HOST
    - TOML: [blackboard] host/key/secret  (or top-level host/key/secret)
    """
    key = (args.key or os.getenv("BB_KEY") or "").strip()
    secret = (args.secret or os.getenv("BB_SECRET") or "").strip()
    host = (getattr(args, "host", "") or os.getenv("BB_HOST") or "").strip()

    cfg_path = getattr(args, "config", None) or ""
    if cfg_path:
        cfg = _load_toml(cfg_path)
        if isinstance(cfg, dict):
            section = cfg.get("blackboard")
            if isinstance(section, dict):
                # read from [blackboard]
                host = host or str(section.get("host") or "")
                key = key or str(section.get("key") or "")
                secret = secret or str(section.get("secret") or "")
            else:
                # or from top-level
                host = host or str(cfg.get("host") or "")
                key = key or str(cfg.get("key") or "")
                secret = secret or str(cfg.get("secret") or "")

    return (key or None, secret or None, host or None)


# -------- CLI --------
def parse_args():
    p = argparse.ArgumentParser(description="Map a Blackboard course's content layout (tree → TXT/CSV/HTML).")
    p.add_argument("--host", help="Base URL, e.g., https://blackboard.fvtc.edu (or in secrets.toml)")

    # credentials (use CLI, env, or TOML --config)
    p.add_argument("--key", help="Blackboard REST app key (or set BB_KEY)")
    p.add_argument("--secret", help="Blackboard REST app secret (or set BB_SECRET)")
    p.add_argument("--config", help="Path to TOML config (e.g., secrets.toml)")

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--course-id")
    g.add_argument("--courses-file")

    p.add_argument("--out-dir", default=".")
    p.add_argument("--hide-bodies", action="store_true")
    p.add_argument("--tree-file-limit", type=int, default=10)
    p.add_argument("--no-tree-truncate", action="store_true")

    # outputs (multi-select). If none chosen, default to HTML.
    p.add_argument("--txt", action="store_true", help="Write TXT tree output")
    p.add_argument("--csv", action="store_true", help="Write CSV map output")
    p.add_argument("--html", action="store_true", help="Write HTML output (default if no output flags given)")

    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # resolve creds (CLI > env > TOML)
    key, secret, host = resolve_credentials(args)
    if not key or not secret or not host:
        sys.exit("Missing credentials: please provide host/key/secret via CLI, env, or --config secrets.toml")

    token = get_token(host, key, secret)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})

    if args.course_id:
        course_ids = [args.course_id.strip()]
    else:
        with open(args.courses_file, "r", encoding="utf-8") as f:
            course_ids = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    # decide outputs (default to HTML if none selected)
    want_txt = getattr(args, "txt", False)
    want_csv = getattr(args, "csv", False)
    want_html = getattr(args, "html", False)
    if not (want_txt or want_csv or want_html):
        want_html = True

    tree_limit: Optional[int] = None if args.no_tree_truncate else args.tree_file_limit

    for cid in course_ids:
        try:
            items = fetch_all_contents(session, host, cid)
            by_id = index_by_id(items)
            kids = children_index(items)
            roots = kids.get("", [])

            # handle orphans
            for it in items:
                pid = it.get("parentId")
                if pid and pid not in by_id and it not in roots:
                    roots.append(it)

            course_pk1 = resolve_course_pk1(session, host, cid)
            course_code, course_name = ("", "")
            if course_pk1:
                try:
                    course_code, course_name = fetch_course_meta(session, host, course_pk1)
                except Exception:
                    pass

            course_header = " — ".join([x for x in (course_code, course_name) if x]) or (course_pk1 or cid)
            base_raw = course_code or course_pk1 or cid
            base = safe_slug(base_raw)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

            # Compute TXT + CSV rows only if needed
            rows = []
            if want_txt or want_csv:
                txt, rows = draw_tree_txt(
                    course_header,
                    roots,
                    kids,
                    by_id,
                    not args.hide_bodies,
                    host,
                    course_pk1,
                    tree_file_limit=tree_limit,
                )
                if want_txt:
                    txt_path = os.path.join(args.out_dir, f"{base}_tree_{timestamp}.txt")
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(txt)
                    print(f"{cid}: wrote tree → {txt_path}")

                if want_csv:
                    csv_path = os.path.join(args.out_dir, f"{base}_map_{timestamp}.csv")
                    write_csv_map(csv_path, rows)
                    print(f"{cid}: wrote map  → {csv_path}")

            if want_html:
                html_doc = build_html(
                    course_header,
                    roots,
                    kids,
                    by_id,
                    not args.hide_bodies,
                    host,
                    course_pk1,
                    tree_file_limit=tree_limit,
                )
                html_path = os.path.join(args.out_dir, f"{base}_tree_{timestamp}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_doc)
                print(f"{cid}: wrote html → {html_path}")

            print()

        except Exception as e:
            print(f"{cid}: ERROR — {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
