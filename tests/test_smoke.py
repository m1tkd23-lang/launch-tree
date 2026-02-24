"""最低限のスモークテスト。"""

from pathlib import Path

from src.launch_tree.domain import Node
from src.launch_tree.storage_json import JsonStorage


def test_import():
    import src.launch_tree.core  # noqa: F401


def test_save_updates_backup(tmp_path: Path):
    storage = JsonStorage(tmp_path / "launcher.json")
    root = Node(id="root", name="Root", type="group", target="", children=[])

    storage.save_tree(root)

    assert storage.path.exists()
    assert storage.backup_path.exists()


def test_load_fallback_to_backup(tmp_path: Path):
    storage = JsonStorage(tmp_path / "launcher.json")
    storage.path.write_text("not-json", encoding="utf-8")
    storage.backup_path.write_text(
        '{"id":"root","name":"Root","type":"group","target":"","children":[]}',
        encoding="utf-8",
    )

    loaded = storage.load_tree()

    assert loaded.id == "root"
    assert loaded.name == "Root"
