from organizer import (
    organize_folder, OrganizerConfig, DEFAULT_FILE_TYPES,
    add_tags, load_tags, save_history, undo_last
)

def test_organize_moves_pdf_to_documents(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_text("fake content")
    cfg = OrganizerConfig(dry_run=False)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert not f.exists()

def test_dry_run_moves_nothing(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_text("fake content")
    cfg = OrganizerConfig(dry_run=True)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    assert f.exists()
    assert not (tmp_path / "Documents" / "report.pdf").exists()

def test_tags_follow_file_on_move(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_text("fake content")
    add_tags(str(tmp_path), "report.pdf", ["budget"])
    cfg = OrganizerConfig(dry_run=False)
    organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    tags = load_tags(str(tmp_path))
    assert "Documents/report.pdf" in tags
    assert "budget" in tags["Documents/report.pdf"]
    assert "report.pdf" not in tags

def test_undo_restores_files(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_text("fake content")
    cfg = OrganizerConfig(dry_run=False)
    _, moves_log = organize_folder(str(tmp_path), DEFAULT_FILE_TYPES, cfg)
    save_history(moves_log, str(tmp_path))
    undo_last(str(tmp_path))
    assert f.exists()
    assert not (tmp_path / "Documents" / "report.pdf").exists()
