# Course Map for Blackboard Ultra

A tiny command-line tool that **crawls a Blackboard Ultra course** via the REST API and exports the structure as:

* **HTML**: a collapsible, searchable tree with file badges, live highlights, and accurate match counts
* **TXT**: a plain-text tree (easy to diff/share)
* **CSV**: a flat map suitable for spreadsheets & audits

> Built for admins, instructional designers, and anyone who’s ever thought, “where did that one PDF go?” 🕵️‍♂️

---

## ✨ Features

* **One call → full course map** (recursive)
* **Ultra Page + Document “merge”** so each Ultra Doc reads as a single node
* **Embedded file detection** from Ultra Doc body (names, mime types, render mode)
* **Embedded content links** extraction (IDs + link type)
* **HTML viewer**:

  * Instant, case-insensitive search across **titles + file badges**
  * **Highlights** each match (`<mark>`) and outlines the matching row
  * **Accurate match counts** (per occurrence, not per row)
  * **Auto-expands** only the paths that match; closes stale panels as you edit the query
  * “Expand all / Collapse all” buttons for quick skimming
* **Output selection flags** (`--txt`, `--csv`, `--html`) — pick your favorites. If you pick none, **HTML** is the default.
* **Stable CSV header** for easy automation

---

## 🧱 Project structure

```
course_map.py      # CLI & API orchestration
cm_shared.py       # shared helpers (parsers, typing, formatting)
export_txt.py      # TXT renderer (+ returns rows for CSV)
export_csv.py      # CSV writer
export_html.py     # HTML renderer (search + highlight scripts embedded)
```

---

## 📦 Requirements

* Python **3.9+**
* `requests` (`pip install requests`)
* Blackboard REST API app credentials

---

## 🔐 Authentication

The tool uses OAuth2 client credentials:

* **Defaults** can be overridden by environment variables or flags.
* Environment variables supported:

  * `BB_KEY`, `BB_SECRET`

---

## 🚀 Quick start

```bash
# 1) Install dependencies
pip install requests

# 2) Run (HTML by default)
python course_map.py \
  --host https://<your-bb-host> \
  --course-id <COURSE_ID_OR_PK1>
```

You can also pass a file of IDs:

```bash
python course_map.py \
  --host https://<your-bb-host> \
  --courses-file courses.txt
```

`courses.txt` is one ID per line; `#` comments are ignored.

---

## 🛠 CLI options

Required:

* `--host` Base URL, e.g., `https://blackboard.example.edu`
* One of:

  * `--course-id <id>` (courseId or pk1 like `_12345_1`)
  * `--courses-file <path>`

General:

* `--out-dir <dir>` Output directory (default: current)
* `--hide-bodies` Hide “UltraBody” nodes in outputs
* `--tree-file-limit <n>` Max file badges shown per node in HTML/TXT (default: 10)
* `--no-tree-truncate` Show all file badges (overrides limit)

Output selection (multi-select; **if none set → HTML only**):

* `--txt`   Write the text tree
* `--csv`   Write the CSV map
* `--html`  Write the HTML viewer

Auth overrides:

* `--key <app key>` and `--secret <app secret>`

  * (or use `BB_KEY` / `BB_SECRET` env vars)

---

## 🧪 Examples

**HTML only (default):**

```bash
python course_map.py --host https://blackboard.example.edu --course-id 10501107-1-2025fall
```

**TXT + CSV (no HTML):**

```bash
python course_map.py --host https://blackboard.example.edu --course-id 10501107-1-2025fall --txt --csv
```

**All three:**

```bash
python course_map.py --host https://blackboard.example.edu --course-id 10501107-1-2025fall --txt --csv --html
```

Outputs are named like:

```
<course>_tree_YYYYMMDD-HHMMSS.html
<course>_tree_YYYYMMDD-HHMMSS.txt
<course>_map_YYYYMMDD-HHMMSS.csv
```

---

## 📄 CSV columns

* `course_id`
* `id` (or merged IDs for Ultra Page + Doc)
* `parentId`
* `title`
* `handler_id`
* `type`
* `availability`
* `position`
* `depth`
* `path` (breadcrumb string)
* `web_url` (for external links)
* `embedded_file_count`
* `embedded_files` (`name|mime|render; ...`)
* `embedded_content_links` (`contentId|linkType; ...`)

---

## 🧩 How the HTML search works (cool bits)

* Searches **summary titles** and **file badges** (even when the badges live inside nested `<details>`).
* On each keystroke:

  * Closes only the `<details>` it opened last time.
  * Highlights current matches (`<mark class="hit">`) and counts **every match**.
  * Auto-expands from the matched node up to the root so hits are visible.
* Optional nicety: the first hit is scrolled into view.

If you ever embed the JS in a Python f-string, braces/backslashes are already escaped in the generator. No gremlins. 🧙

---

## 🧯 Troubleshooting

* **401/403**: verify REST app permissions and the host base URL.
* **Nothing returns**: confirm the courseId vs pk1. You can pass either; the script resolves pk1 automatically.
* **Search not finding files in HTML**: badges live inside `<details>`—the built-in script already accounts for that.
* **Match count looks off**: counts **occurrences**, not rows; a single Ultra Doc with 3 PDFs = 3 matches.

---

## 👋 Credits

Built with ❤️ for Blackboard admins and course wranglers. If this helps you find that one elusive `.pptx`, buy yourself a donut—you’ve earned it. 🍩
