import pytest

pytest.importorskip("PyQt6")

from launch_tree.domain import Node
from launch_tree.model_qt import display_name_for_node


def test_prefix_for_group_and_url():
    assert display_name_for_node(Node(id="1", name="G", type="group", target="", children=[])).startswith("📁 ")
    assert display_name_for_node(Node(id="2", name="U", type="url", target="https://x", children=[])).startswith("🌐 ")


def test_prefix_for_path_variants():
    exe = Node(id="1", name="App", type="path", target="C:/Tools/app.exe", children=[])
    folder = Node(id="2", name="Dir", type="path", target="C:/Tools/", children=[])
    file = Node(id="3", name="Doc", type="path", target="C:/Docs/readme.txt", children=[])
    assert display_name_for_node(exe).startswith("⚙️ ")
    assert display_name_for_node(folder).startswith("🗂️ ")
    assert display_name_for_node(file).startswith("📄 ")


def test_separator_display_only():
    sep = Node(id="s", name="ignore", type="separator", target="", children=[])
    assert display_name_for_node(sep) == "—"
