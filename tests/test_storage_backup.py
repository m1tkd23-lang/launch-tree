from pathlib import Path
import json

from launch_tree.domain import Node
from launch_tree.storage_json import JsonStorage


def test_save_creates_bak_and_generation_backup(tmp_path: Path):
    data_path = tmp_path / "launcher.json"
    storage = JsonStorage(data_path)

    # seed an existing file so pre-save backup has a source
    data_path.write_text('{"id":"root","name":"Old","type":"group","target":"","children":[]}', encoding="utf-8")

    root = Node(id="root", name="Root", type="group", target="", children=[])
    storage.save_tree(root)

    assert storage.backup_path.exists()
    generations = list(storage.backup_dir.glob("launcher_*.json"))
    assert len(generations) >= 1


def test_generation_backups_rotated_to_keep_count(tmp_path: Path):
    storage = JsonStorage(tmp_path / "launcher.json", backup_keep_count=50)
    storage._ensure_backup_dir()

    for i in range(55):
        (storage.backup_dir / f"launcher_20240101_000000_{i:03d}.json").write_text("{}", encoding="utf-8")

    storage._rotate_backups()

    assert len(list(storage.backup_dir.glob("launcher_*.json"))) == 50


def test_load_recovers_from_bak_when_json_is_broken(tmp_path: Path):
    storage = JsonStorage(tmp_path / "launcher.json")
    storage.path.write_text("not-json", encoding="utf-8")
    storage.backup_path.write_text(
        json.dumps({"id": "root", "name": "Recovered", "type": "group", "target": "", "children": []}),
        encoding="utf-8",
    )

    loaded = storage.load_tree()

    assert loaded.name == "Recovered"
    # also copied back to primary
    payload = json.loads(storage.path.read_text(encoding="utf-8"))
    assert payload["name"] == "Recovered"


def test_load_bootstraps_from_example_when_missing(tmp_path: Path):
    storage = JsonStorage(tmp_path / "launcher.json")
    storage.example_path.write_text(
        json.dumps({"id": "root", "name": "Example", "type": "group", "target": "", "children": []}),
        encoding="utf-8",
    )

    loaded = storage.load_tree()

    assert loaded.name == "Example"
    assert storage.path.exists()
