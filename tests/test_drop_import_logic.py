from pathlib import Path

from launch_tree.drop_import_logic import build_drop_entries


def test_build_drop_entries_for_files_and_url():
    entries = build_drop_entries([
        "C:/Tools/app.exe",
        "C:/Docs/readme.txt",
        "https://example.com",
    ])

    assert entries[0].item_type == "path"
    assert entries[0].name == "app.exe"
    assert entries[1].item_type == "path"
    assert entries[2].item_type == "url"
    assert entries[2].target == "https://example.com"


def test_url_shortcut_file_extracts_url(tmp_path: Path):
    p = tmp_path / "site.url"
    p.write_text("[InternetShortcut]\nURL=https://example.org/page\n", encoding="utf-8")

    entries = build_drop_entries([str(p)])

    assert len(entries) == 1
    assert entries[0].item_type == "url"
    assert entries[0].target == "https://example.org/page"
