from launch_tree.domain import Node, move_node


def _sample_tree() -> Node:
    a = Node(id="a", name="A", type="group", target="", children=[])
    b = Node(id="b", name="B", type="group", target="", children=[])
    i1 = Node(id="i1", name="I1", type="item", target="", children=[])
    i2 = Node(id="i2", name="I2", type="item", target="", children=[])
    x = Node(id="x", name="X", type="item", target="", children=[])
    a.children.extend([i1, i2])
    root = Node(id="root", name="Root", type="group", target="", children=[a, b, x])
    return root


def test_move_reorder_within_same_parent():
    root = _sample_tree()

    ok = move_node(root, source_id="x", destination_parent_id="root", destination_row=0)

    assert ok is True
    assert [n.id for n in root.children] == ["x", "a", "b"]


def test_move_into_another_group_changes_parent():
    root = _sample_tree()

    ok = move_node(root, source_id="x", destination_parent_id="b", destination_row=0)

    assert ok is True
    assert [n.id for n in root.children] == ["a", "b"]
    assert [n.id for n in root.children[1].children] == ["x"]


def test_reject_move_into_descendant():
    root = _sample_tree()
    child = Node(id="child", name="child", type="group", target="", children=[])
    root.children[0].children.append(child)

    ok = move_node(root, source_id="a", destination_parent_id="child", destination_row=0)

    assert ok is False
    assert root.children[0].id == "a"
