# export_txt.py
from typing import Any, Dict, List, Mapping, Optional, Tuple
from cm_shared import (
    node_type, is_ultra_page, is_document_handler,
    parse_embedded_files_from_body, parse_embedded_content_links,
    files_csv_field, content_links_csv_field, compute_path
)

def draw_tree_txt(course_label: str,
                  roots: List[Dict[str, Any]],
                  kids: Mapping[str, List[Dict[str, Any]]],
                  by_id: Mapping[str, Dict[str, Any]],
                  show_bodies: bool,
                  host: str,
                  course_pk1: str,
                  tree_file_limit: Optional[int]) -> Tuple[str, List[Dict[str, Any]]]:

    lines: List[str] = [f"Course {course_label}", ""]
    rows: List[Dict[str, Any]] = []

    def url_for_display(item: Dict[str, Any]) -> str:
        from cm_shared import external_link_url, is_external_link
        return external_link_url(item) if is_external_link(item) else ""

    def print_helper(prefix: str, is_last: bool, text: str):
        if not text: return
        lines.append(f"{prefix}{'   ' if is_last else '│  '}[{text}]")

    def walk(node: Dict[str, Any], prefix: str = "", is_last: bool = True, depth: int = 0):
        from cm_shared import handler_id
        nid = node.get("id", "")
        typ = node_type(node)
        if not show_bodies and typ == "UltraBody":
            return

        # Merge Ultra Page + Doc
        if is_ultra_page(node):
            doc_child = None
            for c in kids.get(nid, []):
                if is_document_handler(c):
                    doc_child = c
                    break
            if doc_child is not None:
                parent_title = node.get("title") or ""
                parent_avail = (node.get("availability") or {}).get("available", "")
                parent_pos = node.get("position")
                merged_id_str = f"[{nid},{doc_child.get('id','')}]"
                merged_typ = "ULTRA DOC"
                body = doc_child.get("body") or ""
                files = parse_embedded_files_from_body(body)
                links = parse_embedded_content_links(body)

                branch = "└─ " if is_last else "├─ "
                pos_s = str(parent_pos) if isinstance(parent_pos, int) else ""
                lines.append(f"{prefix}{branch}[{merged_typ}] {parent_title}  (id={merged_id_str}, pos={pos_s}, avail={parent_avail})")
                if files:
                    from cm_shared import format_files_for_tree
                    print_helper(prefix, is_last, format_files_for_tree(files, tree_file_limit))
                if links:
                    print_helper(prefix, is_last, "Embedded content links: " + "; ".join([f"{cid} ({lt or 'link'})" for cid, lt in links]))

                rows.append({
                    "course_id": course_pk1 or course_label,
                    "id": merged_id_str,
                    "parentId": node.get("parentId", ""),
                    "title": parent_title,
                    "handler_id": "resource/x-bb-document",
                    "type": merged_typ,
                    "availability": parent_avail,
                    "position": str(parent_pos) if isinstance(parent_pos, int) else "",
                    "depth": depth,
                    "path": compute_path(node, by_id),
                    "web_url": "",
                    "embedded_file_count": str(len(files)),
                    "embedded_files": files_csv_field(files),
                    "embedded_content_links": content_links_csv_field(links),
                })

                merged_children = []
                for c in kids.get(nid, []):
                    if c is doc_child:
                        continue
                    if show_bodies or node_type(c) != "UltraBody":
                        merged_children.append(c)
                for gc in kids.get(doc_child.get("id", ""), []):
                    if show_bodies or node_type(gc) != "UltraBody":
                        merged_children.append(gc)

                for i, child in enumerate(merged_children):
                    walk(child, prefix + ("   " if is_last else "│  "), i == len(merged_children)-1, depth + 1)
                return

        # Normal row
        avail = (node.get("availability") or {}).get("available", "")
        pos = node.get("position")
        pos_s = str(pos) if isinstance(pos, int) else ""
        title = node.get("title") or ""
        gui = url_for_display(node)
        branch = "└─ " if is_last else "├─ "
        suffix = f"  [URL: {gui}]" if gui else ""
        lines.append(f"{prefix}{branch}[{typ}] {title}  (id={nid}, pos={pos_s}, avail={avail}){suffix}")

        extra = {}
        if typ in {"Document", "UltraBody"}:
            body = node.get("body") or ""
            files = parse_embedded_files_from_body(body)
            links = parse_embedded_content_links(body)
            if files:
                from cm_shared import format_files_for_tree
                print_helper(prefix, is_last, format_files_for_tree(files, tree_file_limit))
            if links:
                print_helper(prefix, is_last, "Embedded content links: " + "; ".join([f"{cid} ({lt or 'link'})" for cid, lt in links]))
            extra = {
                "embedded_file_count": str(len(files)),
                "embedded_files": files_csv_field(files),
                "embedded_content_links": content_links_csv_field(links),
            }

        rows.append({
            "course_id": course_pk1 or course_label,
            "id": nid,
            "parentId": node.get("parentId", ""),
            "title": title,
            "handler_id": handler_id(node),
            "type": node_type(node),
            "availability": avail,
            "position": pos_s,
            "depth": depth,
            "path": compute_path(node, by_id),
            "web_url": gui,
            "embedded_file_count": extra.get("embedded_file_count", ""),
            "embedded_files": extra.get("embedded_files", ""),
            "embedded_content_links": extra.get("embedded_content_links", ""),
        })

        ch = kids.get(nid, [])
        ch = [c for c in ch if show_bodies or node_type(c) != "UltraBody"]
        for i, child in enumerate(ch):
            walk(child, prefix + ("   " if is_last else "│  "), i == len(ch)-1, depth + 1)

    for i, r in enumerate(roots):
        walk(r, "", i == len(roots)-1, 0)

    return ("\n".join(lines) + "\n"), rows
