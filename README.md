# File Organizer

A Python package that automatically sorts files in a folder into categorized subfolders by file type. Supports tagging, undo, duplicate handling, watch mode, filtering, reporting, and a full GUI.

---

## Requirements

- Python 3.8+
- No required third-party packages for core functionality

Optional dependencies (install with `pip`):

| Package | Feature enabled |
|---|---|
| `watchdog` | `--watch` mode (auto-organize on drop) |
| `tqdm` | `--progress` progress bar |
| `tkinter` | `--gui` graphical interface (usually bundled with Python) |

---

## Installation

```bash
# Clone or download, then run as a package
python -m file_organizer ~/Downloads
```

No setup required. All state files are written inside the target folder.

---

## Quick Start

```bash
# Preview — no files are moved
python -m file_organizer ~/Downloads --dry-run

# Organize for real
python -m file_organizer ~/Downloads

# Undo the last session
python -m file_organizer ~/Downloads --undo

# Launch the GUI
python -m file_organizer --gui
```

---

## Default Categories

| Folder | Extensions |
|---|---|
| `Images` | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.svg` `.webp` |
| `Videos` | `.mp4` `.mov` `.avi` `.mkv` `.wmv` |
| `Documents` | `.pdf` `.doc` `.docx` `.txt` `.xls` `.xlsx` `.pptx` |
| `Music` | `.mp3` `.wav` `.aac` `.flac` |
| `Archives` | `.zip` `.tar` `.gz` `.rar` `.7z` |
| `Code` | `.py` `.js` `.ts` `.html` `.css` `.java` `.c` `.cpp` |
| `Other` | Anything not matched above |
| `Duplicates` | Exact duplicate files (when duplicate routing is active) |

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
| `--scan` | Scan folder for suspicious file extensions |
| `--scan-recursive` | Same as `--scan`, includes subfolders |

### Organization

| Flag | Description |
|---|---|
| `--recursive` | Organize files in subfolders too |
| `--rename` | Prefix each filename with today's date (`YYYY-MM-DD_`) |
| `--by-date` | Sort into `Category/YYYY/MonthName/` subfolders |
| `--copy` | Copy files instead of moving them |
| `--verify` | Checksum-verify each file after copy or move |
| `--interactive` | Confirm each file action individually |
| `--config FILE` | Load custom category-to-extension map from JSON |
| `--keep-duplicate STRATEGY` | How to handle exact duplicates (see below) |

**Duplicate strategies:**

| Strategy | Behavior |
|---|---|
| `route` | Move duplicate to a `Duplicates/` folder *(default)* |
| `newest` | Keep whichever file was modified more recently |
| `oldest` | Keep whichever file was modified earlier |
| `ask` | Prompt you to decide for each duplicate individually |

### Tagging

| Flag | Description |
|---|---|
| `--tag FILE TAG [TAG...]` | Add one or more tags to a file |
| `--untag FILE TAG [TAG...]` | Remove one or more tags from a file |
| `--list-tags` | List every tagged file and its tags |
| `--search-tag TAG [TAG...]` | Search tagged files by tag — AND logic |
| `--filter-tag TAG [TAG...]` | Only organize files that have ALL specified tags |

Tags use AND logic: `--search-tag budget review` only returns files tagged with **both**.

Tags are stored in `.organize_tags.json`. When a file is moved, its tag entry is automatically updated — tags never go stale.

If you tag a file using just its basename (e.g. `report.pdf`) and two tagged files share that name, the tool warns you and asks for the relative path instead.

### Filters

| Flag | Description |
|---|---|
| `--min-size SIZE` | Skip files smaller than SIZE (e.g. `500KB`, `2MB`) |
| `--max-size SIZE` | Skip files larger than SIZE (e.g. `1GB`) |
| `--older-than DAYS` | Only include files older than N days |
| `--newer-than DAYS` | Only include files newer than N days |
| `--ignore PATTERN...` | Add glob patterns to skip list (e.g. `"*.tmp"`) |

Size units: `B`, `KB`, `MB`, `GB`, `TB`. Case-insensitive.

### Output

| Flag | Description |
|---|---|
| `--log` | Write a timestamped log to `organize_log.txt` |
| `--html-report` | Generate an `organize_report.html` summary |
| `--csv-report` | Generate an `organize_report.csv` summary |
| `--progress` | Show a progress bar (requires `tqdm`) |

### Custom Rules

```bash
--rules '[{"contains": "invoice", "category": "Finance"}]'
```

JSON array of keyword rules. Rules are checked before the extension map, so they take priority.

---

## Usage Examples

```bash
# Dry run preview
python -m file_organizer ~/Downloads --dry-run

# Recursive organization with date subfolders
python -m file_organizer ~/Downloads --recursive --by-date

# Copy and verify
python -m file_organizer ~/Downloads --copy --verify

# Only move files larger than 1MB older than 30 days
python -m file_organizer ~/Downloads --min-size 1MB --older-than 30

# Count files by type without moving
python -m file_organizer ~/Downloads --stats-only

# Skip specific patterns
python -m file_organizer ~/Downloads --ignore "*.tmp" "~*" "draft_*"

# Auto-keep newest on duplicate
python -m file_organizer ~/Downloads --keep-duplicate newest

# Confirm each move
python -m file_organizer ~/Downloads --interactive

# Custom routing rule
python -m file_organizer ~/Downloads --rules '[{"contains":"invoice","category":"Finance"}]'

# Scan for suspicious files
python -m file_organizer ~/Downloads --scan-recursive

# Watch mode
python -m file_organizer ~/Downloads --watch

# Tagging
python -m file_organizer ~/Downloads --tag report.pdf budget review
python -m file_organizer ~/Downloads --untag report.pdf review
python -m file_organizer ~/Downloads --list-tags
python -m file_organizer ~/Downloads --search-tag budget
python -m file_organizer ~/Downloads --search-tag budget review
python -m file_organizer ~/Downloads --filter-tag budget
python -m file_organizer ~/Downloads --filter-tag budget review --dry-run
```

---

## Project Structure

```
file_organizer/
├── __init__.py       # Public API
├── __main__.py       # Enables python -m file_organizer
├── constants.py      # All constants + OrganizerConfig dataclass
├── core.py           # organize_folder(), filters, helpers, stats
├── tags.py           # Tagging system
├── history.py        # save_history(), undo_last()
├── reports.py        # HTML + CSV report generation
├── scanner.py        # Suspicious file detection
├── watcher.py        # Watch mode (watchdog)
├── gui.py            # tkinter GUI
└── cli.py            # argparse + main()

test_organizer.py     # 33 pytest tests
requirements.txt      # Optional dependencies
README.md
```

---

## Files Created in the Managed Folder

| File | Purpose |
|---|---|
| `.organize_history.json` | Undo history (last 50 sessions) |
| `.organize_tags.json` | Tag database (relative paths + tag lists) |
| `organize_log.txt` | Operation log (opt-in via `--log`) |
| `organize_report.html` | HTML report (opt-in via `--html-report`) |
| `organize_report.csv` | CSV report (opt-in via `--csv-report`) |

All auto-generated files are skipped by the organizer — they will never be moved or tagged.

---

## How Undo Works

Every move session is saved to `.organize_history.json`. `--undo` reverses the most recent session in reverse order. Up to 50 sessions stored. Does not apply to copy operations.

---

## How Tagging Works

Tags are stored as a JSON dictionary using relative file paths as keys:

```json
{
  "Documents/report.pdf": ["budget", "review"],
  "Images/photo.jpg": ["portfolio"]
}
```

**Path tracking:** Tag keys are automatically rewritten when files move.
**AND logic:** `--search-tag` and `--filter-tag` require ALL specified tags to match.
**Ambiguity detection:** If two files share a basename, the tool warns you and requires the relative path.

---

## Suspicious File Scanner

| Category | Extensions |
|---|---|
| Executable | `.exe` `.com` `.scr` `.pif` |
| Script | `.bat` `.cmd` `.vbs` `.ps1` `.js` `.hta` and more |
| System/Driver | `.dll` `.sys` `.drv` |
| Installer | `.msi` `.msp` |
| Registry | `.reg` |
| Java | `.jar` |
| MacroDoc | `.xlsm` `.docm` `.pptm` `.xlam` |
| DiskImage | `.iso` `.img` |

Reports findings grouped by category. Does not move or delete files.

---

## GUI

```bash
python -m file_organizer --gui
```

Two-tab layout:

**Organize tab** — all organize options including dry run, recursive, date folders, copy mode, verify, duplicate handling, log, reports, and a tag filter field.

**Tags tab** — add/remove tags, search by tag, live-refreshing file list, output console. Folder field stays in sync with the Organize tab automatically.

---

## Testing

```bash
pip install pytest
pytest test_organizer.py -v
```

33 tests covering: core organize, dry run, undo, duplicate detection and strategies, size/date filters, and the full tagging system including tags following files on move.

---

## Changelog

### v4 — Bug fixes + search tag + module split
- Fixed `except Exception` in `verify_copy()` → `except OSError` with warning message
- Fixed `except Exception` in `organize_folder()` → `except (OSError, shutil.Error)`
- Fixed `except Exception` in watch mode `on_created()` → `except (OSError, shutil.Error)`
- Fixed `_resolve_tag_key()` silently returning first basename match when multiple files share a name — now warns and requires relative path
- Added `--search-tag` CLI flag: search tagged files with AND logic, shows `✓`/`✗ missing` per result
- Split single 1,293-line script into 10 focused modules
- Added `__main__.py` — tool now runs via `python -m file_organizer`
- Added 33 pytest tests covering core, undo, duplicates, filters, and full tagging system

### v3 — Tagging system
- Added user-defined file tagging (`--tag`, `--untag`, `--list-tags`, `--filter-tag`)
- Tags stored in `.organize_tags.json` using relative paths for portability
- Tags automatically follow files when they are moved during an organize run
- GUI: added tabbed layout with dedicated Tags tab
- `OrganizerConfig` gains `filter_tags: List[str]` field

### v2 — Stability and features
- Fixed inverted date filters, recursive path duplication, missing constant NameError, GUI crash
- Added recursive, stats-only, scan, HTML/CSV reports, interactive, verify, keep-duplicate
- Added by-date, rename, progress, watch, rules, ignore, size/date filters, copy, config, GUI

### v1 — Initial release
- Basic file organization by extension
- Dry run, undo, MD5 duplicate detection, timestamped rename, optional logging

---

## License

MIT — free to use, modify, and distribute.
