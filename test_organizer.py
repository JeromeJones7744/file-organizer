"""
test_organizer.py — Full test suite for file_organizer_fixed_v4
Run with: pytest test_organizer.py -v
"""

import os
import json
import time
import pytest
from datetime import datetime, timedelta

from file_organizer import (
    # Core
    organize_folder,
    OrganizerConfig,
    DEFAULT_FILE_TYPES,
    get_file_hash,
    passes_filters,
    resolve_duplicate_auto,
    # Tags
    add_tags,
    remove_tags,
    load_tags,
    update_tags_on_move,
    get_tagged_files,
    # History
    save_history,
    undo_last,
)


# ===========================================================================
# Helpers
# ===========================================================================

def make_file(path, content="fake content", size_bytes=None):
    """Create a file at path. Optionally write size_bytes of data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if size_bytes is not None:
        path.write_bytes(b"x" * size_bytes)
    else:
        path.write_text(content)
    return path


# ===========================================================================
# 1. Core organize_folder — integration tests
# ===========================================================================

def test_organize_moves_pdf_to_documents(tmp_path):
    make_file(tmp_path / "report.pdf")
    cfg = OrganizerConfig(dry_run=False)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert not (tmp_path / "report.pdf").exists()


def test_organize_moves_jpg_to_images(tmp_path):
    make_file(tmp_path / "photo.jpg")
    cfg = OrganizerConfig(dry_run=False)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "Images" / "photo.jpg").exists()


def test_organize_moves_mp3_to_music(tmp_path):
    make_file(tmp_path / "song.mp3")
    cfg = OrganizerConfig(dry_run=False)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "Music" / "song.mp3").exists()


def test_unknown_extension_goes_to_other(tmp_path):
    make_file(tmp_path / "weirdfile.xyz")
    cfg = OrganizerConfig(dry_run=False)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "Other" / "weirdfile.xyz").exists()


def test_dry_run_moves_nothing(tmp_path):
    make_file(tmp_path / "report.pdf")
    cfg = OrganizerConfig(dry_run=True)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documents" / "report.pdf").exists()


def test_multiple_files_sorted_correctly(tmp_path):
    make_file(tmp_path / "report.pdf")
    make_file(tmp_path / "photo.jpg")
    make_file(tmp_path / "song.mp3")
    cfg = OrganizerConfig(dry_run=False)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert (tmp_path / "Images"    / "photo.jpg").exists()
    assert (tmp_path / "Music"     / "song.mp3").exists()


# ===========================================================================
# 2. Undo
# ===========================================================================

def test_undo_restores_single_file(tmp_path):
    make_file(tmp_path / "report.pdf")
    cfg = OrganizerConfig(dry_run=False)
    _, moves_log = organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    save_history(moves_log, str(tmp_path))
    undo_last(str(tmp_path))
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documents" / "report.pdf").exists()


def test_undo_restores_multiple_files(tmp_path):
    make_file(tmp_path / "report.pdf")
    make_file(tmp_path / "photo.jpg")
    cfg = OrganizerConfig(dry_run=False)
    _, moves_log = organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    save_history(moves_log, str(tmp_path))
    undo_last(str(tmp_path))
    assert (tmp_path / "report.pdf").exists()
    assert (tmp_path / "photo.jpg").exists()


def test_undo_with_no_history_does_not_crash(tmp_path):
    # Should print a message but not raise
    undo_last(str(tmp_path))


# ===========================================================================
# 3. Duplicate handling
# ===========================================================================

def test_identical_files_get_same_hash(tmp_path):
    a = make_file(tmp_path / "a.txt", content="same content")
    b = make_file(tmp_path / "b.txt", content="same content")
    assert get_file_hash(str(a)) == get_file_hash(str(b))


def test_different_files_get_different_hash(tmp_path):
    a = make_file(tmp_path / "a.txt", content="content A")
    b = make_file(tmp_path / "b.txt", content="content B")
    assert get_file_hash(str(a)) != get_file_hash(str(b))


def test_duplicate_routes_to_duplicates_folder(tmp_path):
    content = "exact same content"
    make_file(tmp_path / "report.pdf", content=content)
    # Pre-place identical file in destination
    dest_dir = tmp_path / "Documents"
    dest_dir.mkdir()
    make_file(dest_dir / "report.pdf", content=content)
    cfg = OrganizerConfig(dry_run=False, keep_duplicate="route")
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "Duplicates" / "report.pdf").exists()


def test_keep_newest_duplicate_strategy(tmp_path):
    a = make_file(tmp_path / "a.txt", content="old")
    b = make_file(tmp_path / "b.txt", content="new")
    # Make b (dest) newer than a (src)
    future = time.time() + 10
    os.utime(str(b), (future, future))
    # src is older, dest is newer — newest = keep_dest
    result = resolve_duplicate_auto(str(a), str(b), keep="newest")
    assert result == "keep_dest"


def test_keep_oldest_duplicate_strategy(tmp_path):
    a = make_file(tmp_path / "a.txt", content="old")
    b = make_file(tmp_path / "b.txt", content="new")
    # Make b (dest) newer than a (src)
    future = time.time() + 10
    os.utime(str(b), (future, future))
    # src is older, dest is newer — oldest = keep_src
    result = resolve_duplicate_auto(str(a), str(b), keep="oldest")
    assert result == "keep_src"


# ===========================================================================
# 4. Filters
# ===========================================================================

def test_min_size_skips_small_file(tmp_path):
    make_file(tmp_path / "small.pdf", size_bytes=100)
    cfg = OrganizerConfig(dry_run=False, min_size=1024)  # 1KB min
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "small.pdf").exists()
    assert not (tmp_path / "Documents" / "small.pdf").exists()


def test_max_size_skips_large_file(tmp_path):
    make_file(tmp_path / "large.pdf", size_bytes=5000)
    cfg = OrganizerConfig(dry_run=False, max_size=1024)  # 1KB max
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "large.pdf").exists()


def test_min_size_allows_file_at_exact_boundary(tmp_path):
    make_file(tmp_path / "exact.pdf", size_bytes=1024)
    cfg = OrganizerConfig(dry_run=False, min_size=1024)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "Documents" / "exact.pdf").exists()


def test_older_than_filter_skips_new_file(tmp_path):
    make_file(tmp_path / "new.pdf")
    # File is brand new — older_than=30 means skip files newer than 30 days ago
    cutoff = datetime.now() - timedelta(days=30)
    cfg = OrganizerConfig(dry_run=False, older_than=cutoff)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "new.pdf").exists()


def test_newer_than_filter_skips_old_file(tmp_path):
    f = make_file(tmp_path / "old.pdf")
    # Set mtime to 60 days ago
    old_time = time.time() - (60 * 86400)
    os.utime(str(f), (old_time, old_time))
    cutoff = datetime.now() - timedelta(days=30)
    cfg = OrganizerConfig(dry_run=False, newer_than=cutoff)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "old.pdf").exists()


def test_combined_size_and_date_filter(tmp_path):
    # File that passes size but fails date — should not move
    f = make_file(tmp_path / "report.pdf", size_bytes=2000)
    old_time = time.time() - (60 * 86400)
    os.utime(str(f), (old_time, old_time))
    cutoff = datetime.now() - timedelta(days=30)
    cfg = OrganizerConfig(dry_run=False, min_size=500, newer_than=cutoff)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "report.pdf").exists()


def test_passes_filters_returns_true_for_valid_file(tmp_path):
    f = make_file(tmp_path / "report.pdf", size_bytes=2000)
    result = passes_filters(str(f), min_size=500, max_size=10000)
    assert result is True


def test_passes_filters_returns_false_for_small_file(tmp_path):
    f = make_file(tmp_path / "tiny.pdf", size_bytes=10)
    result = passes_filters(str(f), min_size=500)
    assert result is False


# ===========================================================================
# 5. Tagging system
# ===========================================================================

def test_add_single_tag(tmp_path):
    make_file(tmp_path / "report.pdf")
    add_tags(str(tmp_path), "report.pdf", ["budget"])
    tags = load_tags(str(tmp_path))
    assert "budget" in tags["report.pdf"]


def test_add_multiple_tags(tmp_path):
    make_file(tmp_path / "report.pdf")
    add_tags(str(tmp_path), "report.pdf", ["budget", "review", "q4"])
    tags = load_tags(str(tmp_path))
    assert set(tags["report.pdf"]) == {"budget", "review", "q4"}


def test_tags_are_lowercased(tmp_path):
    make_file(tmp_path / "report.pdf")
    add_tags(str(tmp_path), "report.pdf", ["BUDGET", "Review"])
    tags = load_tags(str(tmp_path))
    assert "budget" in tags["report.pdf"]
    assert "review" in tags["report.pdf"]


def test_duplicate_tags_not_added_twice(tmp_path):
    make_file(tmp_path / "report.pdf")
    add_tags(str(tmp_path), "report.pdf", ["budget"])
    add_tags(str(tmp_path), "report.pdf", ["budget"])
    tags = load_tags(str(tmp_path))
    assert tags["report.pdf"].count("budget") == 1


def test_remove_single_tag(tmp_path):
    make_file(tmp_path / "report.pdf")
    add_tags(str(tmp_path), "report.pdf", ["budget", "review"])
    remove_tags(str(tmp_path), "report.pdf", ["review"])
    tags = load_tags(str(tmp_path))
    assert "review" not in tags["report.pdf"]
    assert "budget" in tags["report.pdf"]


def test_remove_all_tags_cleans_entry(tmp_path):
    make_file(tmp_path / "report.pdf")
    add_tags(str(tmp_path), "report.pdf", ["budget"])
    remove_tags(str(tmp_path), "report.pdf", ["budget"])
    tags = load_tags(str(tmp_path))
    # Entry should be gone (pruned on save)
    assert "report.pdf" not in tags


def test_tags_persist_to_json(tmp_path):
    make_file(tmp_path / "report.pdf")
    add_tags(str(tmp_path), "report.pdf", ["budget"])
    # Re-load from disk
    tags = load_tags(str(tmp_path))
    assert "budget" in tags["report.pdf"]


def test_get_tagged_files_and_logic(tmp_path):
    make_file(tmp_path / "report.pdf")
    make_file(tmp_path / "invoice.pdf")
    add_tags(str(tmp_path), "report.pdf",  ["budget", "review"])
    add_tags(str(tmp_path), "invoice.pdf", ["budget", "finance"])
    # Only report.pdf has BOTH budget AND review
    matched = get_tagged_files(str(tmp_path), ["budget", "review"])
    basenames = {os.path.basename(p) for p in matched}
    assert "report.pdf"  in basenames
    assert "invoice.pdf" not in basenames


def test_get_tagged_files_returns_none_when_no_filter(tmp_path):
    result = get_tagged_files(str(tmp_path), [])
    assert result is None


def test_filter_tag_skips_untagged_files(tmp_path):
    make_file(tmp_path / "report.pdf")
    make_file(tmp_path / "photo.jpg")
    add_tags(str(tmp_path), "report.pdf", ["budget"])
    cfg = OrganizerConfig(dry_run=False, filter_tags=["budget"])
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    # report.pdf is tagged budget — should move
    assert (tmp_path / "Documents" / "report.pdf").exists()
    # photo.jpg is not tagged — should stay
    assert (tmp_path / "photo.jpg").exists()


def test_tags_follow_file_on_move(tmp_path):
    make_file(tmp_path / "report.pdf")
    add_tags(str(tmp_path), "report.pdf", ["budget"])
    cfg = OrganizerConfig(dry_run=False)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    tags = load_tags(str(tmp_path))
    assert "Documents/report.pdf" in tags
    assert "budget" in tags["Documents/report.pdf"]
    assert "report.pdf" not in tags
