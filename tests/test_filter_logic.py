from launch_tree.domain import Node
from launch_tree.filter_logic import compute_visible_node_ids, node_matches_query


def _tree() -> Node:
    group = Node(id="g", name="CAM", type="group", target="", children=[])
    item_path = Node(id="p", name="Readme", type="path", target="C:/docs/readme.txt", children=[])
    item_url = Node(id="u", name="Portal", type="url", target="https://example.com", children=[])
    sep = Node(id="s", name="----------", type="separator", target="", children=[])
    group.children.extend([item_path, sep, item_url])
    return Node(id="root", name="Root", type="group", target="", children=[group])


def test_node_matches_name_or_target_case_insensitive():
    node = Node(id="n", name="Portal", type="url", target="https://Example.com", children=[])
    assert node_matches_query(node, "portal") is True
    assert node_matches_query(node, "example") is True


def test_parent_group_visible_when_descendant_matches():
    root = _tree()
    visible = compute_visible_node_ids(root, "readme")

    assert "p" in visible
    assert "g" in visible
    assert "root" in visible


def test_matching_group_makes_all_descendants_visible():
    root = _tree()
    visible = compute_visible_node_ids(root, "cam")

    assert visible == {"root", "g", "p", "u", "s"}


def test_clear_query_shows_all_nodes():
    root = _tree()
    visible = compute_visible_node_ids(root, "")
    assert visible == {"root", "g", "p", "u", "s"}
