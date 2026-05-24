import os
import sys
import time
import shutil
import json
import hashlib
import argparse
import logging
import fnmatch
import csv
import html as html_module
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional

# Optional: watchdog for watch mode
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object

# Optional: tkinter for GUI
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# Optional: tqdm for progress bars
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# ---------------------------------------------------------------------------
# Extension definitions
# ---------------------------------------------------------------------------
SUSPICIOUS_EXTENSIONS = {
    "Executable":    [".exe", ".com", ".scr", ".pif"],
    "Script":        [".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse",
                      ".ps1", ".psm1", ".psd1", ".ws", ".wsh", ".wsf", ".hta"],
    "System/Driver": [".dll", ".sys", ".drv"],
    "Installer":     [".msi", ".msp"],
    "Registry":      [".reg"],
    "Java":          [".jar"],
    "MacroDoc":      [".xlsm", ".docm", ".pptm", ".xlam"],
    "DiskImage":     [".iso", ".img"],
}

DEFAULT_FILE_TYPES = {
    "Images":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
    "Videos":    [".mp4", ".mov", ".avi", ".mkv", ".wmv"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".pptx"],
    "Music":     [".mp3", ".wav", ".aac", ".flac"],
    "Archives":  [".zip", ".tar", ".gz", ".rar", ".7z"],
    "Code":      [".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp"],
}

HISTORY_FILE = ".organize_history.json"
TAGS_FILE    = ".organize_tags.json"
MAX_HISTORY_SESSIONS = 50
LOG_FILE     = "organize_log.txt"

DEFAULT_IGNORE_PATTERNS = [
    "thumbs.db", "desktop.ini", ".DS_Store", "*.tmp", "*.temp", "~*"
]


# ---------------------------------------------------------------------------
# Organizer configuration dataclass
# ---------------------------------------------------------------------------
@dataclass
class OrganizerConfig:
    dry_run:        bool = False
    recursive:      bool = False
    rename:         bool = False
    by_date:        bool = False
    copy_mode:      bool = False
    interactive:    bool = False
    verify:         bool = False
    keep_duplicate: str  = "route"   # "route" | "newest" | "oldest" | "ask"
    ignore_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))
    custom_rules:   List[dict] = field(default_factory=list)
    min_size:       Optional[int] = None
    max_size:       Optional[int] = None
    older_than:     Optional[datetime] = None
    newer_than:     Optional[datetime] = None
    filter_tags:    List[str] = field(default_factory=list)
    logger:         Optional[logging.Logger] = None
    progress:       object = None   # tqdm instance or None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config(config_path):
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return DEFAULT_FILE_TYPES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_file_hash(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_timestamped_name(filename):
    timestamp = datetime.now().strftime("%Y-%m-%d_")
    name, ext = os.path.splitext(filename)
    return f"{timestamp}{name}{ext}"


def get_date_subfolder(filepath):
    """Return YYYY/MonthName based on file mtime."""
    dt = datetime.fromtimestamp(os.path.getmtime(filepath))
    return os.path.join(str(dt.year), dt.strftime("%B"))


def human_size(nbytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def setup_logger(folder_path):
    log_path    = os.path.join(folder_path, LOG_FILE)
    logger_name = f"organizer_{os.path.abspath(folder_path)}"
    logger      = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h = logging.FileHandler(log_path)
        h.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        logger.addHandler(h)
    return logger


def matches_ignore(filename, patterns):
    lower = filename.lower()
    return any(fnmatch.fnmatch(lower, p.lower()) for p in patterns)


def passes_filters(file_path, min_size=None, max_size=None,
                   older_than=None, newer_than=None):
    try:
        stat = os.stat(file_path)
    except OSError:
        return False
    size  = stat.st_size
    mtime = datetime.fromtimestamp(stat.st_mtime)
    if min_size   is not None and size  < min_size:    return False
    if max_size   is not None and size  > max_size:    return False
    if older_than is not None and mtime >= older_than: return False
    if newer_than is not None and mtime <= newer_than: return False
    return True


def apply_custom_rules(filename, custom_rules):
    """Return a category from keyword rules, or None."""
    lower = filename.lower()
    for rule in (custom_rules or []):
        kw = rule.get("contains", "").lower()
        if kw and kw in lower:
            return rule.get("category")
    return None


def verify_copy(src, dest):
    try:
        return get_file_hash(src) == get_file_hash(dest)
    except Exception:
        return False


def describe_duplicate_pair(src_path, dest_path):
    """Print side-by-side info about two files."""
    def info(p):
        s = os.stat(p)
        return human_size(s.st_size), datetime.fromtimestamp(s.st_mtime).strftime("%Y-%m-%d %H:%M")
    ss, sm = info(src_path)
    ds, dm = info(dest_path)
    print(f"    Incoming : {os.path.basename(src_path):<40}  {ss:>10}  {sm}")
    print(f"    Existing : {os.path.basename(dest_path):<40}  {ds:>10}  {dm}")


def resolve_duplicate_auto(src_path, dest_path, keep="newest"):
    src_t  = os.path.getmtime(src_path)
    dest_t = os.path.getmtime(dest_path)
    if keep == "newest":
        return "keep_src" if src_t > dest_t else "keep_dest"
    return "keep_src" if src_t < dest_t else "keep_dest"


# ---------------------------------------------------------------------------
# Undo support
# ---------------------------------------------------------------------------
def save_history(moves, folder_path):
    history_path = os.path.join(folder_path, HISTORY_FILE)
    history = {"sessions": []}
    if os.path.exists(history_path):
        with open(history_path) as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                pass
    history["sessions"].append({
        "timestamp": datetime.now().isoformat(),
        "moves": moves,
    })
    history["sessions"] = history["sessions"][-MAX_HISTORY_SESSIONS:]
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)


def undo_last(folder_path):
    history_path = os.path.join(folder_path, HISTORY_FILE)
    if not os.path.exists(history_path):
        print("No history found. Nothing to undo.")
        return
    with open(history_path) as f:
        try:
            history = json.load(f)
        except json.JSONDecodeError:
            print("History file is corrupted.")
            return
    if not history.get("sessions"):
        print("No sessions to undo.")
        return

    last_session = history["sessions"].pop()
    restored = 0
    for move in reversed(last_session["moves"]):
        src, dest = move["src"], move["dest"]
        if not os.path.exists(dest):
            print(f"Skipping '{os.path.basename(dest)}' — file not found at destination")
            continue
        try:
            src_dir = os.path.dirname(src)
            if src_dir:
                os.makedirs(src_dir, exist_ok=True)
            shutil.move(dest, src)
            print(f"Restored '{os.path.basename(src)}'")
            restored += 1
        except Exception as exc:
            print(f"  ERROR restoring '{os.path.basename(src)}': {exc}")

    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"\nUndo complete. Restored {restored} file(s).")


# ---------------------------------------------------------------------------
# Tag system
# ---------------------------------------------------------------------------
def _tags_path(folder_path):
    return os.path.join(folder_path, TAGS_FILE)


def load_tags(folder_path):
    """Load tag DB. Returns dict of {relative_path: [tag, ...]}."""
    path = _tags_path(folder_path)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_tags(folder_path, tags):
    """Persist tag DB, pruning empty entries."""
    tags = {k: v for k, v in tags.items() if v}
    with open(_tags_path(folder_path), "w") as f:
        json.dump(tags, f, indent=2, sort_keys=True)


def _rel(folder_path, file_path):
    """Relative path key used in tag DB."""
    return os.path.relpath(os.path.abspath(file_path), os.path.abspath(folder_path))


def add_tags(folder_path, filename, new_tags):
    """Add tags to a file. filename may be a bare name or relative path."""
    tags = load_tags(folder_path)
    # Resolve the key: search for a match if only basename given
    key = _resolve_tag_key(folder_path, filename, tags)
    if key is None:
        # File might be at root of folder
        candidate = os.path.join(folder_path, filename)
        if os.path.exists(candidate):
            key = filename
        else:
            print(f"  File not found in '{folder_path}': {filename}")
            return
    existing = tags.get(key, [])
    added = []
    for t in new_tags:
        t = t.lower().strip()
        if t and t not in existing:
            existing.append(t)
            added.append(t)
    tags[key] = existing
    save_tags(folder_path, tags)
    if added:
        print(f"  Tagged '{key}': {', '.join(added)}")
    else:
        print(f"  No new tags added (already present).")


def remove_tags(folder_path, filename, del_tags):
    """Remove specific tags from a file."""
    tags = load_tags(folder_path)
    key = _resolve_tag_key(folder_path, filename, tags)
    if key is None or key not in tags:
        print(f"  No tags found for: {filename}")
        return
    before = set(tags[key])
    tags[key] = [t for t in tags[key] if t not in [d.lower() for d in del_tags]]
    removed = before - set(tags[key])
    save_tags(folder_path, tags)
    if removed:
        print(f"  Removed tags from '{key}': {', '.join(sorted(removed))}")
    else:
        print(f"  None of those tags were present on '{key}'.")


def _resolve_tag_key(folder_path, filename, tags):
    """Find an existing tag DB key that matches filename (bare name or rel path)."""
    # Exact key match
    if filename in tags:
        return filename
    # Match by basename anywhere in DB
    for key in tags:
        if os.path.basename(key) == os.path.basename(filename):
            return key
    return None


def list_tags(folder_path, filter_tag=None):
    """Print all tagged files, optionally filtered by a tag."""
    tags = load_tags(folder_path)
    if not tags:
        print("  No tagged files.")
        return
    results = {k: v for k, v in tags.items()
               if filter_tag is None or filter_tag.lower() in [t.lower() for t in v]}
    if not results:
        print(f"  No files tagged '{filter_tag}'.")
        return
    header = f"Tagged files (filter: '{filter_tag}')" if filter_tag else "All tagged files"
    print(f"\n--- {header} ---")
    for key, tag_list in sorted(results.items()):
        print(f"  {key:<50}  [{', '.join(sorted(tag_list))}]")
    print()


def update_tags_on_move(folder_path, src_path, dest_path):
    """Rewrite tag DB key when a file is moved. Called after a successful move."""
    tags = load_tags(folder_path)
    old_key = _rel(folder_path, src_path)
    new_key = _rel(folder_path, dest_path)
    if old_key in tags:
        tags[new_key] = tags.pop(old_key)
        save_tags(folder_path, tags)


def get_tagged_files(folder_path, filter_tags):
    """Return set of absolute paths for files matching ALL given tags."""
    if not filter_tags:
        return None  # None = no filter active
    tags = load_tags(folder_path)
    matched = set()
    for key, tag_list in tags.items():
        tag_set = {t.lower() for t in tag_list}
        if all(ft.lower() in tag_set for ft in filter_tags):
            abs_path = os.path.abspath(os.path.join(folder_path, key))
            matched.add(abs_path)
    return matched


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_html_report(moves_log, stats, folder_path, dry_run=False):
    report_path = os.path.join(folder_path, "organize_report.html")
    mode = "DRY RUN PREVIEW" if dry_run else "COMPLETED"
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = "".join(
        f"<tr><td>{html_module.escape(os.path.basename(m['src']))}</td>"
        f"<td>{html_module.escape(os.path.relpath(m['dest'], folder_path))}</td></tr>\n"
        for m in moves_log
    )
    stat_rows = "".join(
        f"<tr><td>{html_module.escape(cat)}</td><td>{count}</td></tr>\n"
        for cat, count in sorted(stats.items())
    )
    total = sum(stats.values())

    move_label = "Previewed Files (Dry Run)" if dry_run else "File Moves"
    col_label  = "Would Move To" if dry_run else "Destination"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>File Organizer Report</title>
<style>
  body{{font-family:Arial,sans-serif;margin:32px;color:#222}}
  h1{{color:#2e7d32}} h2{{color:#555;margin-top:28px}}
  table{{border-collapse:collapse;width:100%;max-width:860px}}
  th,td{{border:1px solid #ddd;padding:8px 12px;text-align:left}}
  th{{background:#f5f5f5}} tr:nth-child(even){{background:#fafafa}}
  .badge{{display:inline-block;padding:2px 10px;border-radius:12px;
    background:{'#fff3e0' if dry_run else '#e8f5e9'};
    color:{'#e65100' if dry_run else '#2e7d32'};font-weight:bold;font-size:.9em}}
  .note{{font-style:italic;color:#888;font-size:.9em}}
</style></head>
<body>
<h1>File Organizer Report</h1>
<p>Generated: {ts} &nbsp;<span class="badge">{mode}</span></p>
<p>Folder: <code>{html_module.escape(folder_path)}</code></p>
{'<p class="note">This is a dry-run preview. No files were actually moved.</p>' if dry_run else ''}
<h2>Summary by Category {'(Preview)' if dry_run else ''}</h2>
<table><tr><th>Category</th><th>{'Would Move' if dry_run else 'Files Moved'}</th></tr>
{stat_rows}<tr><th>Total</th><th>{total}</th></tr></table>
<h2>{move_label} ({len(moves_log)})</h2>
<table><tr><th>File</th><th>{col_label}</th></tr>
{rows if rows else '<tr><td colspan="2">No files moved.</td></tr>'}
</table></body></html>"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML report -> {report_path}")


def generate_csv_report(moves_log, stats, folder_path, dry_run=False):
    report_path = os.path.join(folder_path, "organize_report.csv")
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "key", "value"])
        w.writerow(["meta", "generated", datetime.now().isoformat()])
        w.writerow(["meta", "dry_run",   str(dry_run)])
        w.writerow(["meta", "folder",    folder_path])
        for cat, count in sorted(stats.items()):
            w.writerow(["stat", cat, count])
        w.writerow(["stat", "Total", sum(stats.values())])
        for m in moves_log:
            w.writerow(["move", m["src"], m["dest"]])
    print(f"  CSV  report -> {report_path}")


# ---------------------------------------------------------------------------
# Stats-only scan
# ---------------------------------------------------------------------------
def stats_only(folder_path, file_types, recursive=False, ignore_patterns=None,
               min_size=None, max_size=None, older_than=None, newer_than=None):
    ignore_patterns = ignore_patterns or DEFAULT_IGNORE_PATTERNS
    stats   = {}
    managed = set(file_types.keys()) | {"Other", "Duplicates"}

    def _scan(dirpath):
        try:
            entries = os.listdir(dirpath)
        except PermissionError:
            return
        for name in entries:
            full = os.path.join(dirpath, name)
            if os.path.isdir(full):
                if recursive:
                    _scan(full)
                continue
            if name.startswith(".") or name in (LOG_FILE, HISTORY_FILE):
                continue
            if matches_ignore(name, ignore_patterns):
                continue
            if not passes_filters(full, min_size, max_size, older_than, newer_than):
                continue
            _, ext = os.path.splitext(name)
            cat = "Other"
            for c, exts in file_types.items():
                if ext.lower() in exts:
                    cat = c
                    break
            if cat not in stats:
                stats[cat] = {"count": 0, "bytes": 0}
            stats[cat]["count"] += 1
            stats[cat]["bytes"] += os.path.getsize(full)

    _scan(folder_path)
    return stats


def print_stats_only(stats):
    if not stats:
        print("\nNo files found.")
        return
    print("\n--- File Count by Type (no files moved) ---")
    tc = tb = 0
    for cat, data in sorted(stats.items()):
        c, b = data["count"], data["bytes"]
        print(f"  {cat:<15} {c:>5} file{'s' if c != 1 else ''}   {human_size(b):>10}")
        tc += c; tb += b
    print(f"  {'Total':<15} {tc:>5} files       {human_size(tb):>10}")


# ---------------------------------------------------------------------------
# Core organizer
# ---------------------------------------------------------------------------
def organize_folder(folder_path, file_types, cfg: OrganizerConfig,
                    stats=None, moves_log=None, target_file=None, root_folder=None):
    if stats     is None: stats     = {}
    if moves_log is None: moves_log = []
    if root_folder is None:
        root_folder = os.path.abspath(folder_path)

    managed = set(file_types.keys()) | {"Other", "Duplicates"}

    try:
        filenames = [target_file] if target_file else os.listdir(folder_path)
    except PermissionError:
        print(f"  Permission denied: {folder_path}")
        return stats, moves_log

    for filename in filenames:
        file_path = os.path.join(folder_path, filename)

        if os.path.isdir(file_path):
            if cfg.recursive:
                organize_folder(file_path, file_types, cfg, stats, moves_log, root_folder=root_folder)
            continue

        if filename.startswith(".") or filename in (LOG_FILE, HISTORY_FILE, TAGS_FILE):
            continue
        if matches_ignore(filename, cfg.ignore_patterns):
            continue
        if not passes_filters(file_path, cfg.min_size, cfg.max_size,
                              cfg.older_than, cfg.newer_than):
            continue

        # Tag filter: skip files that don't match all required tags
        if cfg.filter_tags:
            tagged = get_tagged_files(root_folder, cfg.filter_tags)
            if tagged is not None and os.path.abspath(file_path) not in tagged:
                continue

        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        # Category: custom rules first, then extension map
        category = apply_custom_rules(filename, cfg.custom_rules)
        if category is None:
            category = "Other"
            for cat, extensions in file_types.items():
                if ext in extensions:
                    category = cat
                    break

        # Skip if already inside the correct category folder
        current_dir = os.path.abspath(folder_path)
        rel_dir = os.path.relpath(current_dir, root_folder)
        relative_parts = [] if rel_dir == "." else rel_dir.split(os.sep)
        if category in relative_parts:
            continue

        dest_folder = os.path.join(folder_path, category)
        base_dest_folder = dest_folder
        if cfg.by_date:
            dest_folder = os.path.join(dest_folder, get_date_subfolder(file_path))

        # Duplicate detection: search entire category folder tree
        check_path    = None
        if os.path.isdir(base_dest_folder):
            for _root, _dirs, _files in os.walk(base_dest_folder):
                if filename in _files:
                    check_path = os.path.join(_root, filename)
                    break
        dest_filename = get_timestamped_name(filename) if cfg.rename else filename
        dest_path     = os.path.join(dest_folder, dest_filename)

        _file_to_delete = None

        if check_path is not None:
            src_hash  = get_file_hash(file_path)
            dest_hash = get_file_hash(check_path)
            if src_hash == dest_hash:
                if cfg.keep_duplicate == "route":
                    dest_folder   = os.path.join(folder_path, "Duplicates")
                    dest_path     = os.path.join(dest_folder, dest_filename)
                    category      = "Duplicates"
                elif cfg.keep_duplicate in ("newest", "oldest"):
                    decision = resolve_duplicate_auto(file_path, check_path, cfg.keep_duplicate)
                    if decision == "keep_dest":
                        print(f"  Skipping duplicate (keeping existing): {filename}")
                        if cfg.progress: cfg.progress.update(1)
                        continue
                    else:
                        _file_to_delete = check_path
                elif cfg.keep_duplicate == "ask":
                    print(f"\n  Duplicate: {filename}")
                    describe_duplicate_pair(file_path, check_path)
                    choice = input("  Keep [i]ncoming / [e]xisting / [r]oute to Duplicates? ").strip().lower()
                    if choice == "e":
                        if cfg.progress: cfg.progress.update(1)
                        continue
                    elif choice == "r":
                        dest_folder = os.path.join(folder_path, "Duplicates")
                        dest_path   = os.path.join(dest_folder, dest_filename)
                        category    = "Duplicates"
            else:
                # Same name, different content — conflict rename
                base, file_ext = os.path.splitext(dest_filename)
                counter = 1
                candidate = f"{base}_conflict_{counter}{file_ext}"
                while os.path.exists(os.path.join(dest_folder, candidate)):
                    counter  += 1
                    candidate = f"{base}_conflict_{counter}{file_ext}"
                dest_filename = candidate
                dest_path     = os.path.join(dest_folder, dest_filename)

        # Interactive confirmation
        if cfg.interactive and not cfg.dry_run:
            verb = "Copy" if cfg.copy_mode else "Move"
            ans  = input(f"  {verb} '{filename}' -> {category}/{dest_filename}? [y/N] ").strip().lower()
            if ans != "y":
                if cfg.progress: cfg.progress.update(1)
                continue

        if cfg.dry_run:
            verb = "copy" if cfg.copy_mode else "move"
            msg  = f"[DRY RUN] Would {verb} '{filename}' -> {category}/{dest_filename}"
            print(msg)
            if cfg.logger: cfg.logger.info(msg)
            stats[category] = stats.get(category, 0) + 1
            moves_log.append({"src": file_path, "dest": dest_path})
        else:
            try:
                os.makedirs(dest_folder, exist_ok=True)
                if cfg.copy_mode:
                    src_hash_before = get_file_hash(file_path) if cfg.verify else None
                    shutil.copy2(file_path, dest_path)
                    if cfg.verify and get_file_hash(dest_path) != src_hash_before:
                        print(f"  WARNING: Checksum mismatch after copy of '{filename}'!")
                        if cfg.logger: cfg.logger.warning(f"Checksum mismatch: {filename}")
                else:
                    src_hash_before = get_file_hash(file_path) if cfg.verify else None
                    shutil.move(file_path, dest_path)
                    if cfg.verify and (not os.path.exists(dest_path) or
                                       get_file_hash(dest_path) != src_hash_before):
                        print(f"  WARNING: Verification failed after move of '{filename}'!")
                        if cfg.logger: cfg.logger.warning(f"Verification failed: {filename}")
                    if (_file_to_delete and os.path.exists(_file_to_delete)
                        and os.path.abspath(_file_to_delete) != os.path.abspath(dest_path)):
                        os.remove(_file_to_delete)
                    # Keep tags in sync with new path
                    update_tags_on_move(root_folder, file_path, dest_path)

                verb = "Copied" if cfg.copy_mode else "Moved"
                msg  = f"{verb} '{filename}' -> {category}/{dest_filename}"
                print(msg)
                if cfg.logger: cfg.logger.info(msg)
                stats[category] = stats.get(category, 0) + 1
                moves_log.append({"src": file_path, "dest": dest_path})

            except Exception as exc:
                print(f"  ERROR on '{filename}': {exc}")
                if cfg.logger: cfg.logger.error(f"Failed on '{filename}': {exc}")

        if cfg.progress: cfg.progress.update(1)

    return stats, moves_log


# ---------------------------------------------------------------------------
# Suspicious file scanner
# ---------------------------------------------------------------------------
def scan_suspicious(folder_path, recursive=False):
    ext_to_category = {
        ext: cat
        for cat, exts in SUSPICIOUS_EXTENSIONS.items()
        for ext in exts
    }
    results = []

    def _scan_dir(dirpath):
        try:
            entries = os.listdir(dirpath)
        except PermissionError:
            return
        for name in entries:
            full = os.path.join(dirpath, name)
            if os.path.isdir(full):
                if recursive: _scan_dir(full)
            else:
                ext_lower = os.path.splitext(name)[1].lower()
                if ext_lower in ext_to_category:
                    results.append({
                        "path": full, "filename": name,
                        "extension": ext_lower,
                        "category": ext_to_category[ext_lower],
                    })

    _scan_dir(folder_path)
    return results


def print_scan_results(results, folder_path):
    if not results:
        print("No suspicious files found.")
        return
    print(f"\n--- Suspicious Files Found: {len(results)} ---")
    by_category = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)
    for category, items in sorted(by_category.items()):
        print(f"\n  [{category}]")
        for item in items:
            print(f"    {os.path.relpath(item['path'], folder_path)}")
    print()


# ---------------------------------------------------------------------------
# Stats summary
# ---------------------------------------------------------------------------
def print_stats(stats, dry_run=False):
    if not stats:
        label = "previewed" if dry_run else "moved"
        print(f"\nNo files were {label}.")
        return
    label = "Would move" if dry_run else "Moved"
    print(f"\n--- Summary ({label}) ---")
    for category, count in sorted(stats.items()):
        print(f"  {category:<15} {count} file{'s' if count != 1 else ''}")
    total = sum(stats.values())
    print(f"  {'Total':<15} {total} file{'s' if total != 1 else ''}")


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------
class FolderHandler(FileSystemEventHandler):
    def __init__(self, folder_path, file_types, cfg: OrganizerConfig):
        self.folder_path = folder_path
        self.file_types  = file_types
        self.cfg         = cfg

    def on_created(self, event):
        if not event.is_directory:
            path = event.src_path
            prev_size = -1
            for _ in range(10):
                try:
                    curr_size = os.path.getsize(path)
                except OSError:
                    curr_size = -1
                if curr_size == prev_size and curr_size >= 0:
                    break
                prev_size = curr_size
                time.sleep(0.3)
            filename = os.path.basename(path)
            if not filename.startswith("."):
                try:
                    stats, moves_log = organize_folder(
                        self.folder_path, self.file_types, self.cfg,
                        target_file=filename,
                    )
                    if moves_log and not self.cfg.copy_mode and not self.cfg.dry_run:
                        save_history(moves_log, self.folder_path)
                    print_stats(stats)
                except Exception as exc:
                    print(f"  Watch mode error on '{filename}': {exc}")
                    if self.cfg.logger:
                        self.cfg.logger.error(f"Watch mode error on '{filename}': {exc}")


def watch_folder(folder_path, file_types, cfg: OrganizerConfig):
    if not WATCHDOG_AVAILABLE:
        print("watchdog is not installed. Run: pip3 install watchdog")
        return
    handler  = FolderHandler(folder_path, file_types, cfg)
    observer = Observer()
    observer.schedule(handler, folder_path, recursive=False)
    observer.start()
    print(f"Watching '{folder_path}' for new files... Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
def launch_gui(file_types):
    if not TKINTER_AVAILABLE:
        print("tkinter is not available on this system.")
        return

    root = tk.Tk()
    root.title("File Organizer")
    root.geometry("650x700")
    root.resizable(False, False)

    # Use ttk Notebook for tabs
    try:
        from tkinter import ttk
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        organize_tab = ttk.Frame(notebook)
        tags_tab     = ttk.Frame(notebook)
        notebook.add(organize_tab, text="  Organize  ")
        notebook.add(tags_tab,     text="  Tags  ")
    except Exception:
        # Fallback: no tabs
        organize_tab = root
        tags_tab     = None

    # ------------------------------------------------------------------ #
    #  ORGANIZE TAB                                                        #
    # ------------------------------------------------------------------ #
    tk.Label(organize_tab, text="Folder to organize:", anchor="w").pack(fill="x", padx=12, pady=(12, 0))
    row = tk.Frame(organize_tab); row.pack(fill="x", padx=12)
    folder_var = tk.StringVar()
    tk.Entry(row, textvariable=folder_var, width=50).pack(side="left", fill="x", expand=True)

    def browse():
        path = filedialog.askdirectory()
        if path: folder_var.set(path)

    tk.Button(row, text="Browse", command=browse).pack(side="right", padx=(4, 0))

    tk.Label(organize_tab, text="Options:", anchor="w").pack(fill="x", padx=12, pady=(10, 0))
    dry_run_var        = tk.BooleanVar()
    recursive_var      = tk.BooleanVar()
    rename_var         = tk.BooleanVar()
    by_date_var        = tk.BooleanVar()
    copy_mode_var      = tk.BooleanVar()
    verify_var         = tk.BooleanVar()
    log_var            = tk.BooleanVar()
    html_report_var    = tk.BooleanVar()
    csv_report_var     = tk.BooleanVar()
    scan_recursive_var = tk.BooleanVar()
    keep_duplicate_var = tk.StringVar(value="route")

    for label, var in [
        ("Dry run (preview only)",                       dry_run_var),
        ("Recursive (include subfolders)",               recursive_var),
        ("Rename files with date prefix",                rename_var),
        ("Organise into date subfolders (YYYY/Month/)",  by_date_var),
        ("Copy files instead of moving",                 copy_mode_var),
        ("Verify copies with checksum",                  verify_var),
        ("Save log to organize_log.txt",                 log_var),
        ("Generate HTML report",                         html_report_var),
        ("Generate CSV report",                          csv_report_var),
        ("Scan subfolders for suspicious files",         scan_recursive_var),
    ]:
        tk.Checkbutton(organize_tab, text=label, variable=var).pack(anchor="w", padx=24)

    # Duplicate handling dropdown
    dup_row = tk.Frame(organize_tab); dup_row.pack(anchor="w", padx=24, pady=(4, 0))
    tk.Label(dup_row, text="Duplicate handling:").pack(side="left")
    tk.OptionMenu(dup_row, keep_duplicate_var, "route", "newest", "oldest", "ask").pack(side="left", padx=4)

    # Filter by tag row
    filter_row = tk.Frame(organize_tab); filter_row.pack(anchor="w", padx=24, pady=(4, 0))
    tk.Label(filter_row, text="Only organize files tagged:").pack(side="left")
    filter_tag_var = tk.StringVar()
    tk.Entry(filter_row, textvariable=filter_tag_var, width=20).pack(side="left", padx=(4, 0))
    tk.Label(filter_row, text="(space-separated, leave blank for all)", fg="#888").pack(side="left", padx=(4, 0))

    tk.Label(organize_tab, text="Output:", anchor="w").pack(fill="x", padx=12, pady=(8, 0))
    output = tk.Text(organize_tab, height=8, state="disabled",
                     bg="#1e1e1e", fg="#d4d4d4", font=("Courier", 10))
    output.pack(fill="both", expand=True, padx=12, pady=(0, 6))

    class Redirect:
        def write(self, text):
            output.config(state="normal")
            output.insert(tk.END, text)
            output.see(tk.END)
            output.config(state="disabled")
            root.update()
        def flush(self): pass

    def run():
        folder = os.path.abspath(os.path.expanduser(folder_var.get().strip()))
        if not os.path.exists(folder):
            messagebox.showerror("Error", f"Folder not found:\n{folder}"); return
        output.config(state="normal"); output.delete("1.0", tk.END)
        old_stdout = sys.stdout; sys.stdout = Redirect()
        logger = setup_logger(folder) if log_var.get() else None
        raw_tags = filter_tag_var.get().strip()
        filter_tags = [t.lower() for t in raw_tags.split() if t] if raw_tags else []
        cfg = OrganizerConfig(
            dry_run=dry_run_var.get(),
            recursive=recursive_var.get(),
            rename=rename_var.get(),
            by_date=by_date_var.get(),
            copy_mode=copy_mode_var.get(),
            verify=verify_var.get(),
            keep_duplicate=keep_duplicate_var.get(),
            filter_tags=filter_tags,
            logger=logger,
        )
        if filter_tags:
            print(f"Tag filter active: {', '.join(filter_tags)}")
        stats, moves_log = organize_folder(folder, file_types, cfg)
        if not cfg.dry_run and not cfg.copy_mode and moves_log:
            save_history(moves_log, folder)
        if html_report_var.get():
            generate_html_report(moves_log, stats, folder, dry_run=cfg.dry_run)
        if csv_report_var.get():
            generate_csv_report(moves_log, stats, folder, dry_run=cfg.dry_run)
        print_stats(stats, dry_run=cfg.dry_run); print("Done!")
        sys.stdout = old_stdout; output.config(state="disabled")

    def run_scan():
        folder = os.path.abspath(os.path.expanduser(folder_var.get().strip()))
        if not os.path.exists(folder):
            messagebox.showerror("Error", f"Folder not found:\n{folder}"); return
        output.config(state="normal"); output.delete("1.0", tk.END)
        old_stdout = sys.stdout; sys.stdout = Redirect()
        results = scan_suspicious(folder, recursive=scan_recursive_var.get())
        print_scan_results(results, folder)
        sys.stdout = old_stdout; output.config(state="disabled")

    btn_row = tk.Frame(organize_tab); btn_row.pack(pady=6)
    tk.Button(btn_row, text="Organize",        command=run,
              bg="#4CAF50", fg="white", font=("Helvetica", 11, "bold"), pady=4
              ).pack(side="left", padx=4)
    tk.Button(btn_row, text="Scan Suspicious", command=run_scan,
              bg="#e65100", fg="white", font=("Helvetica", 11, "bold"), pady=4
              ).pack(side="left", padx=4)

    # ------------------------------------------------------------------ #
    #  TAGS TAB                                                            #
    # ------------------------------------------------------------------ #
    if tags_tab is not None:
        tk.Label(tags_tab, text="Folder:", anchor="w").pack(fill="x", padx=12, pady=(12, 0))
        tag_folder_row = tk.Frame(tags_tab); tag_folder_row.pack(fill="x", padx=12)
        tag_folder_var = tk.StringVar()

        def _sync_folder(*_):
            # Keep tag folder in sync with organize folder
            tag_folder_var.set(folder_var.get())
        folder_var.trace_add("write", _sync_folder)

        tk.Entry(tag_folder_row, textvariable=tag_folder_var, width=50).pack(side="left", fill="x", expand=True)

        def browse_tag_folder():
            path = filedialog.askdirectory()
            if path: tag_folder_var.set(path)
        tk.Button(tag_folder_row, text="Browse", command=browse_tag_folder).pack(side="right", padx=(4, 0))

        # --- Add/Remove tags ---
        tk.Label(tags_tab, text="File name (or relative path):", anchor="w").pack(fill="x", padx=12, pady=(14, 0))
        tag_file_var = tk.StringVar()
        tk.Entry(tags_tab, textvariable=tag_file_var, width=55).pack(fill="x", padx=12)

        tk.Label(tags_tab, text="Tags (space-separated):", anchor="w").pack(fill="x", padx=12, pady=(8, 0))
        tag_input_var = tk.StringVar()
        tk.Entry(tags_tab, textvariable=tag_input_var, width=55).pack(fill="x", padx=12)

        def _get_tag_folder():
            f = os.path.abspath(os.path.expanduser(tag_folder_var.get().strip()))
            if not os.path.exists(f):
                messagebox.showerror("Error", f"Folder not found:\n{f}")
                return None
            return f

        def do_add_tags():
            folder = _get_tag_folder()
            if not folder: return
            fname  = tag_file_var.get().strip()
            tnames = tag_input_var.get().strip().split()
            if not fname or not tnames:
                messagebox.showwarning("Missing input", "Enter a file name and at least one tag.")
                return
            old_stdout = sys.stdout; sys.stdout = Redirect_tags()
            add_tags(folder, fname, tnames)
            sys.stdout = old_stdout
            refresh_tag_list()

        def do_remove_tags():
            folder = _get_tag_folder()
            if not folder: return
            fname  = tag_file_var.get().strip()
            tnames = tag_input_var.get().strip().split()
            if not fname or not tnames:
                messagebox.showwarning("Missing input", "Enter a file name and at least one tag.")
                return
            old_stdout = sys.stdout; sys.stdout = Redirect_tags()
            remove_tags(folder, fname, tnames)
            sys.stdout = old_stdout
            refresh_tag_list()

        tag_btn_row = tk.Frame(tags_tab); tag_btn_row.pack(pady=(8, 0))
        tk.Button(tag_btn_row, text="Add Tags",    command=do_add_tags,
                  bg="#1976D2", fg="white", font=("Helvetica", 10, "bold"), pady=3
                  ).pack(side="left", padx=6)
        tk.Button(tag_btn_row, text="Remove Tags", command=do_remove_tags,
                  bg="#c62828", fg="white", font=("Helvetica", 10, "bold"), pady=3
                  ).pack(side="left", padx=6)

        # --- Search / list tags ---
        search_row = tk.Frame(tags_tab); search_row.pack(fill="x", padx=12, pady=(14, 0))
        tk.Label(search_row, text="Search tag:").pack(side="left")
        search_var = tk.StringVar()
        tk.Entry(search_row, textvariable=search_var, width=20).pack(side="left", padx=4)
        tk.Button(search_row, text="Search", command=lambda: refresh_tag_list(search_var.get().strip())
                  ).pack(side="left", padx=2)
        tk.Button(search_row, text="Show All", command=lambda: refresh_tag_list()
                  ).pack(side="left", padx=2)

        tk.Label(tags_tab, text="Tagged files:", anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        tag_list_box = tk.Text(tags_tab, height=12, state="disabled",
                               bg="#1e1e1e", fg="#d4d4d4", font=("Courier", 10))
        tag_list_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        tag_output_lines = []

        class Redirect_tags:
            def write(self, text):
                tag_output_lines.append(text)
            def flush(self): pass

        def refresh_tag_list(filter_tag=None):
            folder = _get_tag_folder()
            if not folder: return
            tag_output_lines.clear()
            old_stdout = sys.stdout; sys.stdout = Redirect_tags()
            list_tags(folder, filter_tag=filter_tag if filter_tag else None)
            sys.stdout = old_stdout
            tag_list_box.config(state="normal")
            tag_list_box.delete("1.0", tk.END)
            tag_list_box.insert(tk.END, "".join(tag_output_lines))
            tag_list_box.config(state="disabled")

        tk.Button(tags_tab, text="Refresh List", command=refresh_tag_list,
                  font=("Helvetica", 9)).pack(pady=(0, 6))

        # Output console for tag operations (shared with Redirect_tags)
        tag_console = tk.Text(tags_tab, height=4, state="disabled",
                              bg="#111", fg="#aaffaa", font=("Courier", 9))
        tag_console.pack(fill="x", padx=12, pady=(0, 8))

        # Patch Redirect_tags to also write to console
        class Redirect_tags:  # noqa: F811
            def write(self, text):
                tag_output_lines.append(text)
                tag_console.config(state="normal")
                tag_console.insert(tk.END, text)
                tag_console.see(tk.END)
                tag_console.config(state="disabled")
                root.update()
            def flush(self): pass

    root.mainloop()


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------
def parse_size(s):
    """Parse size strings like '500KB', '2MB', '1GB' into bytes."""
    s = s.strip().upper()
    for unit, mult in [("TB", 1024**4), ("GB", 1024**3), ("MB", 1024**2), ("KB", 1024), ("B", 1)]:
        if s.endswith(unit):
            return int(float(s[:-len(unit)]) * mult)
    return int(s)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="File Organizer — sort files into folders by type",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python organizer.py ~/Downloads --dry-run
  python organizer.py ~/Downloads --recursive --by-date
  python organizer.py ~/Downloads --copy --verify --html-report
  python organizer.py ~/Downloads --min-size 1MB --older-than 30
  python organizer.py ~/Downloads --ignore "*.tmp" "~*" --stats-only
  python organizer.py ~/Downloads --keep-duplicate newest
  python organizer.py ~/Downloads --interactive
  python organizer.py ~/Downloads --rules '[{"contains":"invoice","category":"Finance"}]'

  Tagging:
  python organizer.py ~/Downloads --tag report.pdf budget review
  python organizer.py ~/Downloads --untag report.pdf review
  python organizer.py ~/Downloads --list-tags
  python organizer.py ~/Downloads --filter-tag budget
  python organizer.py ~/Downloads --filter-tag budget review --dry-run
""",
    )

    parser.add_argument("folder",      nargs="?",       help="Path to the folder to organize")

    # Modes
    parser.add_argument("--dry-run",       action="store_true", help="Preview without moving anything")
    parser.add_argument("--undo",          action="store_true", help="Undo the last organize session")
    parser.add_argument("--watch",         action="store_true", help="Watch folder and auto-organize new files")
    parser.add_argument("--gui",           action="store_true", help="Launch the graphical interface")
    parser.add_argument("--stats-only",    action="store_true", help="Count files by type without moving")
    parser.add_argument("--scan",          action="store_true", help="Scan for suspicious file extensions")
    parser.add_argument("--scan-recursive",action="store_true", help="Scan subfolders for suspicious files")

    # Tagging
    parser.add_argument("--tag",       metavar=("FILE", "TAG"), nargs="+",
                        help="Tag a file: --tag report.pdf budget review")
    parser.add_argument("--untag",     metavar=("FILE", "TAG"), nargs="+",
                        help="Remove tags from a file: --untag report.pdf review")
    parser.add_argument("--list-tags", action="store_true", help="List all tagged files and their tags")
    parser.add_argument("--filter-tag", metavar="TAG", nargs="+",
                        help="Only organize files that have ALL specified tags")

    # Organisation
    parser.add_argument("--recursive",    action="store_true", help="Organize subfolders recursively")
    parser.add_argument("--rename",       action="store_true", help="Prefix filenames with today's date")
    parser.add_argument("--by-date",      action="store_true", help="Organize into Category/YYYY/Month/")
    parser.add_argument("--copy",         action="store_true", help="Copy files instead of moving")
    parser.add_argument("--verify",       action="store_true", help="Checksum-verify each copy/move")
    parser.add_argument("--interactive",  action="store_true", help="Confirm each file move individually")
    parser.add_argument("--config",       metavar="FILE",      help="Path to custom categories JSON")
    parser.add_argument("--keep-duplicate", default="route",
                        choices=["route", "newest", "oldest", "ask"],
                        help="How to handle identical duplicates (default: route)")

    # Filters
    parser.add_argument("--min-size",    metavar="SIZE", help="Skip files smaller than SIZE (e.g. 500KB)")
    parser.add_argument("--max-size",    metavar="SIZE", help="Skip files larger than SIZE (e.g. 1GB)")
    parser.add_argument("--older-than",  metavar="DAYS", type=int, help="Only files older than N days")
    parser.add_argument("--newer-than",  metavar="DAYS", type=int, help="Only files newer than N days")
    parser.add_argument("--ignore",      metavar="PATTERN", nargs="+",
                        help="Glob patterns to skip, added to defaults (e.g. '*.tmp' '~*')")

    # Output
    parser.add_argument("--log",         action="store_true", help="Write organize_log.txt")
    parser.add_argument("--html-report", action="store_true", help="Generate HTML summary report")
    parser.add_argument("--csv-report",  action="store_true", help="Generate CSV summary report")
    parser.add_argument("--progress",    action="store_true", help="Show progress bar (requires tqdm)")

    # Custom rules
    parser.add_argument("--rules", metavar="JSON",
                        help='Keyword rules as JSON: \'[{"contains":"invoice","category":"Finance"}]\'')

    args = parser.parse_args()
    file_types = load_config(args.config)

    if args.gui:
        launch_gui(file_types)
        return

    if args.folder:
        folder = os.path.abspath(os.path.expanduser(args.folder))
    else:
        folder = os.path.abspath(os.path.expanduser(
            input("Enter the path to the folder you want to organize: ").strip()
        ))

    if not os.path.exists(folder):
        print(f"Folder not found: {folder}")
        return

    if args.undo:
        undo_last(folder)
        return

    # Tag commands
    if args.tag:
        filename, *tag_names = args.tag
        if not tag_names:
            print("Usage: --tag <filename> <tag1> [tag2 ...]")
        else:
            add_tags(folder, filename, tag_names)
        return

    if args.untag:
        filename, *tag_names = args.untag
        if not tag_names:
            print("Usage: --untag <filename> <tag1> [tag2 ...]")
        else:
            remove_tags(folder, filename, tag_names)
        return

    if args.list_tags:
        list_tags(folder)
        return

    if args.scan or args.scan_recursive:
        results = scan_suspicious(folder, recursive=args.scan_recursive)
        print_scan_results(results, folder)
        return

    # Parse filters
    min_size   = parse_size(args.min_size)                         if args.min_size   else None
    max_size   = parse_size(args.max_size)                         if args.max_size   else None
    older_than = datetime.now() - timedelta(days=args.older_than)  if args.older_than else None
    newer_than = datetime.now() - timedelta(days=args.newer_than)  if args.newer_than else None

    ignore_patterns = list(DEFAULT_IGNORE_PATTERNS)
    if args.ignore:
        ignore_patterns.extend(args.ignore)

    custom_rules = []
    if args.rules:
        try:
            custom_rules = json.loads(args.rules)
        except json.JSONDecodeError as e:
            print(f"Invalid --rules JSON: {e}"); return

    if args.interactive and args.dry_run:
        print("Note: --interactive has no effect in --dry-run mode. Proceeding with dry run.")

    if args.stats_only:
        s = stats_only(folder, file_types, recursive=args.recursive,
                       ignore_patterns=ignore_patterns,
                       min_size=min_size, max_size=max_size,
                       older_than=older_than, newer_than=newer_than)
        print_stats_only(s)
        return

    logger = setup_logger(folder) if args.log else None
    progress = None

    cfg = OrganizerConfig(
        dry_run=args.dry_run,
        recursive=args.recursive,
        rename=args.rename,
        by_date=args.by_date,
        copy_mode=args.copy,
        interactive=args.interactive,
        verify=args.verify,
        keep_duplicate=args.keep_duplicate,
        ignore_patterns=ignore_patterns,
        custom_rules=custom_rules,
        min_size=min_size,
        max_size=max_size,
        older_than=older_than,
        newer_than=newer_than,
        filter_tags=args.filter_tag or [],
        logger=logger,
        progress=progress,
    )

    if args.watch:
        watch_folder(folder, file_types, cfg)
        return

    # Optional progress bar — indeterminate mode so filters don't cause mismatch
    if args.progress:
        if TQDM_AVAILABLE:
            progress = tqdm(total=None, unit="file", desc="Organizing")
        else:
            print("tqdm not installed. Run: pip3 install tqdm  (continuing without progress bar)")
    cfg.progress = progress

    stats, moves_log = organize_folder(folder, file_types, cfg)

    if progress:
        progress.close()

    if not cfg.dry_run and not cfg.copy_mode and moves_log:
        save_history(moves_log, folder)

    if args.html_report:
        generate_html_report(moves_log, stats, folder, dry_run=cfg.dry_run)
    if args.csv_report:
        generate_csv_report(moves_log, stats, folder, dry_run=cfg.dry_run)

    print_stats(stats, dry_run=cfg.dry_run)
    print("Done!")


if __name__ == "__main__":
    main()
