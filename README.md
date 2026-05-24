# File Organizer

A Python command-line tool (with optional GUI) that automatically sorts files in a folder into categorized subfolders by file type. Supports tagging, undo, duplicate handling, watch mode, filtering, reporting, and more.

---

## Requirements

- Python 3.8+
- No required third-party packages for core functionality

Optional dependencies (install with `pip`):

| Package    | Feature enabled                        |
|------------|----------------------------------------|
| `watchdog` | `--watch` mode (auto-organize on drop) |
| `tqdm`     | `--progress` progress bar              |
| `tkinter`  | `--gui` graphical interface (usually bundled with Python) |

---

## Installatio
```bash
# Clone or download the script, then run directly
python organizer.py ~n
/Downloads
```

No setup required. All state files (history, tags, log) are written inside the target folder.

---

## Quick Start

```bash
# Preview what would happen — no files are moved
python organizer.py ~/Downloads --dry-run

# Organize for real
python organizer.py ~/Downloads

# Undo the last session
python organizer.py ~/Downloads --undo

# Launch the GUI
python organizer.py --gui
```

---

## Default Categories

Files are sorted into these folders based on extension:

| Folder      | Extensions                                              |
|-------------|---------------------------------------------------------|
| `Images`    | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.svg` `.webp`     |
| `Videos`    | `.mp4` `.mov` `.avi` `.mkv` `.wmv`                      |
| `Documents` | `.pdf` `.doc` `.docx` `.txt` `.xls` `.xlsx` `.pptx`    |
| `Music`     | `.mp3` `.wav` `.aac` `.flac`                            |
| `Archives`  | `.zip` `.tar` `.gz` `.rar` `.7z`                        |
| `Code`      | `.py` `.js` `.ts` `.html` `.css` `.java` `.c` `.cpp`   |
| `Other`     | Anything not matched above                              |
| `Duplicates`| Exact duplicate files (when duplicate routing is active)|

---

## All CLI Flags

### Modes

| Flag                | Description                                        |
|---------------------|----------------------------------------------------|
| `--dry-run`         | Preview all moves without touching any files       |
| `--undo`            | Reverse the last organize session                  |
| `--watch`           | Monitor the folder and auto-organize new files     |
| `--gui`             | Launch the graphical interface                     |
| `--stats-only`      | Count files by type without moving anything        |
| `--scan`            | Scan folder for suspicious file extensions         |
| `--scan-recursive`  | Same as `--scan`, includes subfolders              |

### Organization

| Flag                        | Description                                              |
|-----------------------------|----------------------------------------------------------|
| `--recursive`               | Organize files in subfolders too                         |
| `--rename`                  | Prefix each filename with today's date (`YYYY-MM-DD_`)  |
| `--by-date`                 | Sort into `Category/YYYY/MonthName/` subfolders          |
| `--copy`                    | Copy files instead of moving them                        |
| `--verify`                  | Checksum-verify each file after copy or move             |
| `--interactive`             | Confirm each file action individually before it happens  |
| `--config FILE`             | Load custom category-to-extension map from a JSON file   |
| `--keep-duplicate STRATEGY` | How to handle exact duplicates (see below)               |

**Duplicate strategies:**

| Strategy  | Behavior                                               |
|-----------|--------------------------------------------------------|
| `route`   | Move duplicate to a `Duplicates/` folder *(default)*  |
| `newest`  | Keep whichever file was modified more recently         |
| `oldest`  | Keep whichever file was modified earlier               |
| `ask`     | Prompt you to decide for each duplicate individually   |

### Tagging

| Flag                      | Description                                                    |
|---------------------------|----------------------------------------------------------------|
| `--tag FILE TAG [TAG...]`  | Add one or more tags to a file                                |
| `--untag FILE TAG [TAG...]`| Remove one or more tags from a file                           |
| `--list-tags`             | List every tagged file and its tags                            |
| `--filter-tag TAG [TAG...]`| Only organize files that have ALL of the specified tags       |

Tags use AND logic: `--filter-tag budget review` only matches files tagged with **both** `budget` and `review`.

Tags are stored in `.organize_tags.json` inside the managed folder. When a file is moved, its tag DB entry is automatically updated to the new path — tags never go stale.

### Filters

| Flag                  | Description                                              |
|-----------------------|----------------------------------------------------------|
| `--min-size SIZE`     | Skip files smaller than SIZE (e.g. `500KB`, `2MB`)      |
| `--max-size SIZE`     | Skip files larger than SIZE (e.g. `1GB`)                 |
| `--older-than DAYS`   | Only include files older than N days                     |
| `--newer-than DAYS`   | Only include files newer than N days                     |
| `--ignore PATTERN...` | Add glob patterns to the skip list (e.g. `"*.tmp"`)     |

Size units: `B`, `KB`, `MB`, `GB`, `TB`. Case-insensitive.

### Output

| Flag            | Description                                                    |
|-----------------|----------------------------------------------------------------|
| `--log`         | Write a timestamped log to `organize_log.txt`                 |
| `--html-report` | Generate an `organize_report.html` summary                    |
| `--csv-report`  | Generate an `organize_report.csv` summary                     |
| `--progress`    | Show a progress bar (requires `tqdm`)                         |

### Custom Rules

```bash
--rules '[{"contains": "invoice", "category": "Finance"}]'
```

JSON array of keyword rules. If a filename contains the given string, it's routed to the specified category. Rules are checked before the extension map, so they take priority.

---

## Usage Examples

```bash
# Dry run preview
python organizer.py ~/Downloads --dry-run

# Recursive organization with date subfolders
python organizer.py ~/Downloads --recursive --by-date

# Copy files and checksum verify each one
python organizer.py ~/Downloads --copy --verify

# Only move files larger than 1MB that are older than 30 days
python organizer.py ~/Downloads --min-size 1MB --older-than 30

# Count files by type without moving anything
python organizer.py ~/Downloads --stats-only

# Skip specific file patterns
python organizer.py ~/Downloads --ignore "*.tmp" "~*" "draft_*"

# Auto-keep the newest file when duplicates are found
python organizer.py ~/Downloads --keep-duplicate newest

# Confirm each move before it happens
python organizer.py ~/Downloads --interactive

# Route files with "invoice" in the name to a Finance folder
python organizer.py ~/Downloads --rules '[{"contains":"invoice","category":"Finance"}]'

# Scan for potentially dangerous file types
python organizer.py ~/Downloads --scan-recursive

# Watch the folder and auto-organize files as they're added
python organizer.py ~/Downloads --watch

# --- Tagging ---

# Tag a file with multiple labels
python organizer.py ~/Downloads --tag report.pdf budget review

# Remove a tag
python organizer.py ~/Downloads --untag report.pdf review

# List all tagged files
python organizer.py ~/Downloads --list-tags

# Only organize files tagged 'budget'
python organizer.py ~/Downloads --filter-tag budget

# Only organize files tagged with BOTH 'budget' AND 'review'
python organizer.py ~/Downloads --filter-tag budget review --dry-run
```

---

## Custom Category Config

Create a JSON file to override the default categories:

```json
{
  "Design":    [".psd", ".ai", ".fig", ".sketch"],
  "Documents": [".pdf", ".docx", ".txt"],
  "Data":      [".csv", ".json", ".xml", ".sql"]
}
```

Use it with:

```bash
python organizer.py ~/Downloads --config my_categories.json
```

---

## Files Created in the Managed Folder

| File                      | Purpose                                              |
|---------------------------|------------------------------------------------------|
| `.organize_history.json`  | Undo history (last 50 sessions)                      |
| `.organize_tags.json`     | Tag database (relative paths + tag lists)            |
| `organize_log.txt`        | Operation log (only created when `--log` is used)    |
| `organize_report.html`    | HTML report (only created when `--html-report` used) |
| `organize_report.csv`     | CSV report (only created when `--csv-report` used)   |

All of these files are automatically skipped when the organizer runs — they will never be moved or tagged.

---

## Suspicious File Scanner

The `--scan` flag checks for file types that are commonly associated with malware or unintended execution:

| Category       | Extensions                                                 |
|----------------|------------------------------------------------------------|
| Executable     | `.exe` `.com` `.scr` `.pif`                                |
| Script         | `.bat` `.cmd` `.vbs` `.ps1` `.js` `.hta` and more         |
| System/Driver  | `.dll` `.sys` `.drv`                                       |
| Installer      | `.msi` `.msp`                                              |
| Registry       | `.reg`                                                     |
| Java           | `.jar`                                                     |
| MacroDoc       | `.xlsm` `.docm` `.pptm` `.xlam`                           |
| DiskImage      | `.iso` `.img`                                              |

The scanner reports findings grouped by category. It does **not** move or delete files.

---

## GUI

Launch with:

```bash
python organizer.py --gui
```

The GUI is split into two tabs:

**Organize tab** — full access to all organize options including dry run, recursive, date folders, copy mode, verify, duplicate handling, log, reports, and a tag filter field to restrict which files get organized.

**Tags tab** — add and remove tags by filename, search for files by tag, and view a live list of all tagged files. The folder field in the Tags tab stays in sync with the Organize tab automatically.

---

## How Undo Works

Every time files are moved (not copied), the session is saved to `.organize_history.json`. Running `--undo` reverses the most recent session, moving each file back to its original location. Up to 50 sessions are stored; older sessions are dropped automatically.

Undo does **not** apply to copy operations — the originals were never moved, so there's nothing to reverse.

---

## How Tagging Works

Tags are stored as a JSON dictionary mapping relative file paths to lists of lowercase tag strings:

```json
{
  "Documents/report.pdf": ["budget", "review"],
  "Images/photo.jpg": ["portfolio"]
}
```

**Path tracking:** When a file is moved during an organize run, the tag database entry is automatically rewritten to the new relative path. Tags never point to a stale location.

**Search logic:** `--filter-tag` uses AND logic. A file must have every tag you specify to be included. Tags are case-insensitive.

**Basename resolution:** When running `--tag report.pdf budget`, you can use just the filename — the tool searches the tag DB for a matching basename if the exact key isn't found.

---

## Changelog

### v3 — Tagging system
- Added user-defined file tagging (`--tag`, `--untag`, `--list-tags`, `--filter-tag`)
- Tags stored in `.organize_tags.json` using relative paths for portability
- Tags automatically follow files when they are moved during an organize run
- `--filter-tag` supports multiple tags with AND logic
- GUI: added tabbed layout (`ttk.Notebook`) with a dedicated Tags tab
- Tags tab: add/remove tags by filename, search by tag, live-refreshing file list, output console
- Organize tab: added tag filter field to restrict which files get organized
- `TAGS_FILE` constant added; `.organize_tags.json` is now skipped by the organizer and scanner
- `OrganizerConfig` gains `filter_tags: List[str]` field

### v2 — Stability and features
- Fixed inverted date filter logic (`--older-than` / `--newer-than` were reversed)
- Fixed recursive mode path duplication (files inside category subfolders were re-processed)
- Fixed missing `HISTORY_FILE` constant causing `NameError` on undo
- Fixed GUI crash when tkinter `Text` widget was written to after being set `disabled`
- Fixed undo skipping files when destination path no longer existed
- Added `--recursive` flag for subfolder organization
- Added `--stats-only` mode for read-only file counts
- Added `--scan` / `--scan-recursive` for suspicious extension detection
- Added HTML and CSV report generation
- Added `--interactive` mode for per-file confirmation
- Added `--verify` checksum validation for copy and move operations
- Added `--keep-duplicate` with `route`, `newest`, `oldest`, and `ask` strategies
- Added conflict renaming for same-name, different-content files (`_conflict_N` suffix)
- Added `--by-date` to organize into `Category/YYYY/MonthName/` subfolders
- Added `--rename` to prefix filenames with today's date
- Added `--progress` progress bar via `tqdm`
- Added `--watch` mode using `watchdog` for real-time folder monitoring
- Added `--rules` for keyword-based custom routing rules
- Added `--ignore` for additional glob skip patterns
- Added `--min-size`, `--max-size`, `--older-than`, `--newer-than` file filters
- Added `--copy` mode to copy instead of move
- Added `--config` to load custom category-to-extension JSON
- Added GUI (`--gui`) with tkinter: folder browser, all options, output console
- History capped at 50 sessions; older entries automatically pruned
- Logger deduplication prevents duplicate handlers on repeated calls

### v1 — Initial release
- Basic file organization by extension into category subfolders
- Dry run mode
- Undo support via `.organize_history.json`
- MD5 duplicate detection with `Duplicates/` routing
- Timestamped rename option
- Default ignore patterns for system junk files
- File size display using human-readable units
- Optional logging to `organize_log.txt`

---

## Project Structure

```
organizer.py               # Single-file script — everything is here
.organize_history.json     # Auto-generated: undo history
.organize_tags.json        # Auto-generated: tag database
organize_log.txt           # Auto-generated: operation log (opt-in)
organize_report.html       # Auto-generated: HTML report (opt-in)
organize_report.csv        # Auto-generated: CSV report (opt-in)
```

---

## License

MIT — free to use, modify, and distribute.
