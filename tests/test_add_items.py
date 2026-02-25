from pathlib import Path

from launch_tree.domain import Node, insert_relative_to_selection
from launch_tree.storage_json import JsonStorage


def _tree() -> Node:
    child_group = Node(id="g1", name="G1", type="group", target="", children=[])
    item = Node(id="i1", name="I1", type="item", target="", children=[])
    root = Node(id="root", name="Root", type="group", target="", children=[child_group, item])
    return root


def test_insert_path_under_group_selection():
    root = _tree()
    new_node = Node.make(name="a.txt", node_type="path", target="C:/tmp/a.txt")

    ok = insert_relative_to_selection(root, "g1", new_node)

    assert ok is True
    assert root.children[0].children[0].type == "path"


def test_insert_url_after_item_selection_same_level():
    root = _tree()
    new_node = Node.make(name="https://example.com", node_type="url", target="https://example.com")

    ok = insert_relative_to_selection(root, "i1", new_node)

    assert ok is True
    assert [n.id for n in root.children][-1] == new_node.id


def test_insert_node_can_be_saved_to_json(tmp_path: Path):
    root = _tree()
    sep = Node.make(name="----------", node_type="separator", target="")
    assert insert_relative_to_selection(root, None, sep) is True

    storage = JsonStorage(tmp_path / "launcher.json")
    storage.save_tree(root)
    loaded = storage.load_tree()

    assert any(child.type == "separator" for child in loaded.children)
