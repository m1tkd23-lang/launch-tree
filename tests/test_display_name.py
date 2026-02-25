import pytest

pytest.importorskip("PyQt6")

from launch_tree.domain import Node
from launch_tree.model_qt import display_name_for_node


def test_display_name_is_raw_name_for_normal_nodes():
    assert display_name_for_node(Node(id="1", name="G", type="group", target="", children=[])) == "G"
    assert display_name_for_node(Node(id="2", name="U", type="url", target="https://x", children=[])) == "U"
    assert display_name_for_node(Node(id="3", name="Doc", type="path", target="C:/Docs/readme.txt", children=[])) == "Doc"


def test_separator_display_only():
    sep = Node(id="s", name="ignore", type="separator", target="", children=[])
    assert display_name_for_node(sep) == "—"
