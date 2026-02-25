from launch_tree.domain import Node
from launch_tree.edit_logic import apply_node_update


def test_empty_name_rejected():
    node = Node(id="n", name="A", type="group", target="", children=[])
    ok, _ = apply_node_update(node, new_name="")
    assert ok is False


def test_group_with_children_cannot_become_non_group():
    node = Node(id="g", name="G", type="group", target="", children=[Node(id="c", name="C", type="item", target="", children=[])])
    ok, _ = apply_node_update(node, new_type="path", new_target="C:/x")
    assert ok is False


def test_group_to_path_requires_target():
    node = Node(id="g", name="G", type="group", target="", children=[])
    ok, _ = apply_node_update(node, new_type="path", new_target="")
    assert ok is False


def test_group_or_separator_forces_empty_target():
    node = Node(id="n", name="X", type="url", target="https://example.com", children=[])
    ok, _ = apply_node_update(node, new_type="separator")
    assert ok is True
    assert node.target == ""
