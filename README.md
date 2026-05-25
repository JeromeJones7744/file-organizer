<div align="center">

```
███████╗██╗██╗     ███████╗     ██████╗ ██████╗  ██████╗ ███████╗
██╔════╝██║██║     ██╔════╝    ██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
█████╗  ██║██║     █████╗      ██║   ██║██████╔╝██║  ███╗███████╗
██╔══╝  ██║██║     ██╔══╝      ██║   ██║██╔══██╗██║   ██║╚════██║
██║     ██║███████╗███████╗    ╚██████╔╝██║  ██║╚██████╔╝███████║
╚═╝     ╚═╝╚══════╝╚══════╝     ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
```

**A Python tool that automatically sorts your files so you don't have to.**

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![Tests](https://img.shields.io/badge/Tests-33%20passing-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/Status-Portfolio%20Project-orange?style=flat-square)

[Features](#features) • [Quick Start](#quick-start) • [CLI Reference](#all-cli-flags) • [Tagging](#tagging) • [GUI](#gui) • [Changelog](#changelog)

</div>

---

## What It Does

Drop this tool on any messy folder and it automatically sorts files into clean subfolders by type — images, documents, code, music, and more. Built with Python's standard library, no installation required for core features.

**Highlights:**
- 🗂️ Sorts files by extension into categorized subfolders
- 🏷️ Tag files with custom labels and filter by tag
- ↩️ Full undo support — reverse any session instantly
- 🔍 Duplicate detection via MD5 hashing
- 👁️ Dry run mode — preview everything before touching files
- 📊 HTML and CSV report generation
- 🖥️ GUI with two-tab layout (Organize + Tags)
- 👀 Watch mode — auto-organizes files as they're added
- 🚨 Suspicious file scanner

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/yourusername/file-organizer.git
cd file-organizer

# Install optional dependencies (core needs nothing)
pip install -r requirements.txt

# Preview what would happen — nothing is moved
python -m file_organizer ~/Downloads --dry-run

# Organize for real
python -m file_organizer ~/Downloads

# Launch the GUI
python -m file_organizer --gui
```

---

## Features

### 🗂️ Smart File Sorting

Files are automatically routed into subfolders based on extension:

| Folder | Extensions |
|---|---|
| `Images` | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.svg` `.webp` |
| `Videos` | `.mp4` `.mov` `.avi` `.mkv` `.wmv` |
| `Documents` | `.pdf` `.doc` `.docx` `.txt` `.xls` `.xlsx` `.pptx` |
| `Music` | `.mp3` `.wav` `.aac` `.flac` |
| `Archives` | `.zip` `.tar` `.gz` `.rar` `.7z` |
| `Code` | `.py` `.js` `.ts` `.html` `.css` `.java` `.c` `.cpp` |
| `Other` | Anything not matched above |
| `Duplicates` | Exact duplicate files (configurable) |

---

### 🏷️ Tagging System

Attach custom labels to files and use them to filter organize runs or search across your folder.

```bash
# Tag a file
python -m file_organizer ~/Downloads --tag report.pdf budget review

# Search for files by tag (AND logic)
python -m file_organizer ~/Downloads --search-tag budget review

# Only organize files tagged 'budget'
python -m file_organizer ~/Downloads --filter-tag budget --dry-run

# Remove a tag
python -m file_organizer ~/Downloads --untag report.pdf review

# List all tagged files
python -m file_organizer ~/Downloads --list-tags
```

Tags are stored in `.organize_tags.json` using relative paths. When a file moves, its tag entry is **automatically updated** — tags never go stale.

```json
{
  "Documents/report.pdf": ["budget", "review"],
  "Images/photo.jpg": ["portfolio"]
}
```

---

### ↩️ Undo

Every move session is logged. One command reverses it entirely.

```bash
python -m file_organizer ~/Downloads --undo
```

Up to 50 sessions stored. Does not apply to copy operations.

---

### 🔍 Duplicate Detection

Exact duplicates are detected via MD5 hash comparison. Four strategies available:

| Strategy | Behavior |
|---|---|
| `route` *(default)* | Move duplicate to a `Duplicates/` folder |
| `newest` | Keep the more recently modified file |
| `oldest` | Keep the older file |
| `ask` | Prompt you for each duplicate individually |

```bash
python -m file_organizer ~/Downloads --keep-duplicate newest
```

---

### 🖥️ GUI

```bash
python -m file_organizer --gui
```

A clean two-tab interface built with tkinter:

**Organize tab** — all options in one place: dry run, recursive, date folders, copy mode, verify, duplicate strategy, log, reports, and a tag filter field.

**Tags tab** — add and remove tags by filename, search by tag, live-refreshing tagged file list, and an output console showing results in real time.

> 📸 *Screenshot coming soon — run `python -m file_organizer --gui` to see it live.*

---

### 👀 Watch Mode

```bash
python -m file_organizer ~/Downloads --watch
```

Monitors the folder in real time using `watchdog`. Any file dropped in is automatically organized. Waits for file size to stabilize before moving (safe for downloads in progress).

---

### 🚨 Suspicious File Scanner

```bash
python -m file_organizer ~/Downloads --scan-recursive
```

Scans for file types commonly associated with malware or unintended execution. Reports findings grouped by category — does **not** move or delete anything.

| Category | Examples |
|---|---|
| Executable | `.exe` `.com` `.scr` `.pif` |
| Script | `.bat` `.ps1` `.vbs` `.hta` and more |
| System/Driver | `.dll` `.sys` `.drv` |
| MacroDoc | `.xlsm` `.docm` `.pptm` |
| DiskImage | `.iso` `.img` |

---

## All CLI Flags

### Modes

| Flag | Description |
|---|---|
| `--dry-run` | Preview all moves without touching any files |
| `--undo` | Reverse the last organize session |
| `--watch` | Monitor folder and auto-organize new files |
| `--gui` | Launch the graphical interface |
| `--stats-only` | Count files by type without moving anything |
| `--scan` | Scan for suspicious file extensions |
| `--scan-recursive` | Scan including subfolders |

### Organization

| Flag | Description |
|---|---|
| `--recursive` | Organize files in subfolders too |
| `--rename` | Prefix filenames with today's date (`YYYY-MM-DD_`) |
| `--by-date` | Sort into `Category/YYYY/MonthName/` subfolders |
| `--copy` | Copy files instead of moving them |
| `--verify` | Checksum-verify each file after copy or move |
| `--interactive` | Confirm each file action individually |
| `--config FILE` | Load custom category-to-extension map from JSON |
| `--keep-duplicate` | `route` / `newest` / `oldest` / `ask` |

### Tagging

| Flag | Description |
|---|---|
| `--tag FILE TAG [TAG...]` | Add tags to a file |
| `--untag FILE TAG [TAG...]` | Remove tags from a file |
| `--list-tags` | List all tagged files and their tags |
| `--search-tag TAG [TAG...]` | Search by tag — AND logic, shows ✓/✗ per result |
| `--filter-tag TAG [TAG...]` | Only organize files matching ALL specified tags |

### Filters

| Flag | Description |
|---|---|
| `--min-size SIZE` | Skip files smaller than SIZE (e.g. `500KB`, `2MB`) |
| `--max-size SIZE` | Skip files larger than SIZE (e.g. `1GB`) |
| `--older-than DAYS` | Only include files older than N days |
| `--newer-than DAYS` | Only include files newer than N days |
| `--ignore PATTERN...` | Add glob patterns to skip (e.g. `"*.tmp"`) |

### Output

| Flag | Description |
|---|---|
| `--log` | Write a timestamped log to `organize_log.txt` |
| `--html-report` | Generate an HTML summary report |
| `--csv-report` | Generate a CSV summary report |
| `--progress` | Show a progress bar (requires `tqdm`) |
| `--rules JSON` | Keyword routing rules (see below) |

### Custom Rules

```bash
python -m file_organizer ~/Downloads --rules '[{"contains":"invoice","category":"Finance"}]'
```

Rules are checked before the extension map — they always take priority.

---

## Project Structure

```
file_organizer/
├── __init__.py       # Public API
├── __main__.py       # Enables python -m file_organizer
├── constants.py      # All constants + OrganizerConfig dataclass
├── core.py           # organize_folder(), filters, helpers, stats
├── tags.py           # Full tagging system
├── history.py        # save_history(), undo_last()
├── reports.py        # HTML + CSV report generation
├── scanner.py        # Suspicious file detection
├── watcher.py        # Watch mode (watchdog)
├── gui.py            # tkinter GUI
└── cli.py            # argparse + main()

test_organizer.py     # 33 pytest tests
requirements.txt      # Dependencies
README.md
```

---

## Testing

```bash
pip install pytest
pytest test_organizer.py -v
```

**33 tests** covering:
- Core organize (move, dry run, multiple files, unknown extensions)
- Undo (single file, multiple files, no history edge case)
- Duplicate detection and all 4 strategies
- Size and date filters including boundary conditions
- Full tagging system including tags following files on move

---

## Files Created in the Managed Folder

| File | Purpose |
|---|---|
| `.organize_history.json` | Undo history (last 50 sessions) |
| `.organize_tags.json` | Tag database (relative paths + tag lists) |
| `organize_log.txt` | Operation log (opt-in via `--log`) |
| `organize_report.html` | HTML report (opt-in via `--html-report`) |
| `organize_report.csv` | CSV report (opt-in via `--csv-report`) |

All auto-generated files are automatically skipped — they will never be moved or tagged.

---

## Changelog

### v4 — Bug fixes · Search tag · Module split
- Fixed broad `except Exception` in three locations → specific `OSError` / `shutil.Error`
- Fixed `_resolve_tag_key()` silently returning wrong file on ambiguous basename match — now warns and requires relative path
- Added `--search-tag`: search tagged files with AND logic, shows `✓`/`✗ missing` per result
- Refactored single 1,293-line script into 10 focused modules
- Added `__main__.py` — runs via `python -m file_organizer`
- Added 33 pytest tests

### v3 — Tagging system
- Added `--tag`, `--untag`, `--list-tags`, `--filter-tag`
- Tags stored in `.organize_tags.json` with relative paths
- Tags automatically follow files on move
- GUI: tabbed layout with dedicated Tags tab

### v2 — Stability and features
- Fixed inverted date filters, recursive path duplication, NameError on undo, GUI crash
- Added recursive, stats-only, scan, reports, interactive, verify, keep-duplicate, watch, and more

### v1 — Initial release
- File organization by extension, dry run, undo, MD5 duplicate detection, optional logging

---

## License

MIT — free to use, modify, and distribute.

---

<div align="center">
Built by Jerome Jones
</div>
