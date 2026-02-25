import pytest

pytest.importorskip("PyQt6")

from launch_tree.domain import Node
from launch_tree.model_qt import display_name_for_node


def test_group_url_and_path_do_not_add_emoji_prefixes():
    group = Node(id="1", name="G", type="group", target="", children=[])
    url = Node(id="2", name="U", type="url", target="https://x", children=[])
    exe = Node(id="3", name="App", type="path", target="C:/Tools/app.exe", children=[])
    folder = Node(id="4", name="Dir", type="path", target="C:/Tools/", children=[])
    file = Node(id="5", name="Doc", type="path", target="C:/Docs/readme.txt", children=[])

    assert display_name_for_node(group) == "G"
    assert display_name_for_node(url) == "U"
    assert display_name_for_node(exe) == "App"
    assert display_name_for_node(folder) == "Dir"
    assert display_name_for_node(file) == "Doc"


def test_separator_display_only():
    sep = Node(id="s", name="ignore", type="separator", target="", children=[])
    assert display_name_for_node(sep) == "—"
