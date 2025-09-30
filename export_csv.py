# export_csv.py
import csv
from typing import Any, Dict, List

CSV_FIELDS = [
    "course_id", "id", "parentId", "title", "handler_id", "type",
    "availability", "position", "depth", "path", "web_url",
    "embedded_file_count", "embedded_files", "embedded_content_links",
    "inline_urls", "inline_videostudio"
]

def write_csv_map(path: str, rows: List[Dict[str, Any]]) -> str:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            out = {k: ("" if r.get(k) is None else r.get(k)) for k in CSV_FIELDS}
            w.writerow(out)
    return path
