from launch_tree.domain import Node
from launch_tree.icon_logic import icon_category_for_node


def test_icon_category_group_url_separator():
    assert icon_category_for_node(Node(id="1", name="g", type="group", target="", children=[])) == "group"
    assert icon_category_for_node(Node(id="2", name="u", type="url", target="https://x", children=[])) == "url"
    assert icon_category_for_node(Node(id="3", name="s", type="separator", target="", children=[])) == "separator"


def test_icon_category_path_variants():
    assert icon_category_for_node(Node(id="1", name="a", type="path", target="C:/A/app.exe", children=[])) == "path_exe"
    assert icon_category_for_node(Node(id="2", name="b", type="path", target="C:/A/", children=[])) == "path_folder"
    assert icon_category_for_node(Node(id="3", name="c", type="path", target="C:/A/readme.txt", children=[])) == "path_file"
