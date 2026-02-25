from launch_tree.domain import Node
from launch_tree.icon_logic import icon_mode_for_node


def test_icon_mode_non_path_is_none():
    assert icon_mode_for_node(Node(id="1", name="g", type="group", target="", children=[])) == "none"
    assert icon_mode_for_node(Node(id="2", name="u", type="url", target="https://x", children=[])) == "none"
    assert icon_mode_for_node(Node(id="3", name="s", type="separator", target="", children=[])) == "none"


def test_icon_mode_path_variants():
    assert icon_mode_for_node(Node(id="1", name="a", type="path", target="C:/A/app.exe", children=[])) == "exe"
    assert icon_mode_for_node(Node(id="2", name="b", type="path", target="C:/A/", children=[])) == "path_optional"
    assert icon_mode_for_node(Node(id="3", name="c", type="path", target="C:/A/readme.txt", children=[])) == "path_optional"
