# Course Map for Blackboard Ultra

CLI tool that crawls a **Blackboard Ultra** course via the REST API and exports the structure as:

* **HTML** – collapsible, searchable tree (with file badges + live highlights)
* **TXT** – plain-text tree (diff-friendly)
* **CSV** – flat map for audits/spreadsheets

> For admins, IDs, and anyone who’s muttered “where did that PDF go?” 🕵️‍♂️

---

## ✨ Features

* One call → full recursive course map
* **Ultra Page + Document merge** (each Ultra Doc reads as one node)
* Parses **embedded files** (name, MIME, render mode) from Ultra Doc body
* Extracts **embedded content links** (contentId + link type)
* **HTML viewer**:
  * Instant, case-insensitive search across **titles + file badges**
  * Per-occurrence **match count** and `<mark>` highlights
  * Auto-expands only paths that match; collapses stale panels as you edit
  * “Expand all / Collapse all” for quick skims
* Output selection flags: `--txt`, `--csv`, `--html` (if none, **HTML** by default)
* Stable CSV header for automation

---

## 📦 Requirements

* Python **3.9+**
* `requests` (`pip install requests`)
* Blackboard REST API app credentials

---

## 🔐 Credentials (TOML / Env / CLI)

Precedence (each later source fills in missing values):  
**CLI (`--host --key --secret`) → Env (`BB_HOST`, `BB_KEY`, `BB_SECRET`) → TOML (`--config`)**

**Example `secrets.toml`:**
```toml
[blackboard]
host = "https://blackboard.example.edu"
key  = "YOUR_APP_KEY"
secret = "YOUR_APP_SECRET"
```

**Environment variables (optional):**
```bash
export BB_HOST="https://blackboard.example.edu"
export BB_KEY="YOUR_APP_KEY"
export BB_SECRET="YOUR_APP_SECRET"
```

> Use whichever combo you like—CLI args override env/TOML, and env overrides TOML. Fewer flags, fewer frowns. 😌

**.gitignore tip (keep secrets out of git):**
```gitignore
# secrets
secrets.toml
.env
*.env

# generated outputs
*_tree_*.html
*_tree_*.txt
*_map_*.csv
# or put outputs in a folder and ignore it:
# /artifacts/
```

---

## 🚀 Quick start

```bash
# 1) Install deps
pip install requests

# 2) Run (HTML is default if no outputs are specified)

# Option A: everything from TOML
python course_map.py \
  --course-id <COURSE_ID_OR_PK1> \
  --config secrets.toml

# Option B: override host (or use env)
python course_map.py \
  --host https://<your-bb-host> \
  --course-id <COURSE_ID_OR_PK1> \
  --config secrets.toml
```

Batch mode (file of IDs, one per line; `#` comments allowed):

```bash
# From TOML (no --host flag needed):
python course_map.py \
  --courses-file courses.txt \
  --config secrets.toml
```

---

## 🛠 CLI options

**Required**

* One of: `--course-id <id>` **or** `--courses-file <path>`

**Host**

* `--host` Base URL, e.g. `https://blackboard.example.edu`  
  _Optional if provided by env (`BB_HOST`) or TOML (`[blackboard].host`)._

**Auth**

* `--key <app key>` / `--secret <app secret>` (or env `BB_KEY` / `BB_SECRET` / TOML)
* `--config <secrets.toml>`

**General**

* `--out-dir <dir>` output directory (default: current)
* `--hide-bodies` hide “UltraBody” nodes
* `--tree-file-limit <n>` max file badges shown per node (default: 10)
* `--no-tree-truncate` show all file badges (overrides limit)

**Outputs** (multi-select; **default = HTML** if none specified)

* `--txt`  write text tree
* `--csv`  write CSV map
* `--html` write HTML viewer

---

## 🧪 Examples

HTML only (default):
```bash
python course_map.py --course-id 10501107-1-2025fall --config secrets.toml
```

TXT + CSV (no HTML):
```bash
python course_map.py --course-id 10501107-1-2025fall --txt --csv --config secrets.toml
```

All three:
```bash
python course_map.py --course-id 10501107-1-2025fall --txt --csv --html --config secrets.toml
```

**Output filenames**
```
<course>_tree_YYYYMMDD-HHMMSS.html
<course>_tree_YYYYMMDD-HHMMSS.txt
<course>_map_YYYYMMDD-HHMMSS.csv
```

---

## 📄 CSV columns

`course_id`, `id` (merged for Ultra Page + Doc), `parentId`, `title`, `handler_id`, `type`,
`availability`, `position`, `depth`, `path`, `web_url`,
`embedded_file_count`, `embedded_files` (`name|mime|render; …`),
`embedded_content_links` (`contentId|linkType; …`)

---

## 🔎 HTML search behavior

* Searches **summary titles** and **file badges** (even inside nested `<details>`)
* Each keystroke:
  * closes only panels opened by the last search
  * re-highlights matches with `<mark class="hit">`
  * opens ancestors so hits are visible
  * counts **every occurrence**, not just rows
* Scrolls first hit into view (nice little UX bow 🎁)

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

## 🧯 Troubleshooting

* **401/403** → verify REST app permissions and base URL/host
* **No results** → check `courseId` vs `pk1` (script resolves pk1 for you)
* **HTML search misses files** → badges live inside `<details>`; the script accounts for this
* **Match count seems low** → it counts **occurrences**; one Ultra Doc with three PDFs = **3** matches

---

## 🗒️ Changelog

* **2025-10-08** — Host can be provided via `secrets.toml` (`[blackboard].host`) or `BB_HOST`; `--host` now optional. CLI/env/TOML precedence clarified. Error message updated if any of host/key/secret are missing.

---

## 👋 Credits

Built with ❤️ for Blackboard admins and course wranglers.
If this helps you find that one elusive `.pptx`, treat yourself to a donut. 🍩
