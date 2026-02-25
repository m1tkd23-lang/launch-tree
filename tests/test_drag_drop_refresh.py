from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QAbstractItemView

from launch_tree.domain import Node, find_node_ref
from launch_tree.storage_json import JsonStorage
from launch_tree.ui_mainwindow import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path: Path, app):
    x = Node(id="x", name="Item X", type="path", target="C:/x", children=[])
    a = Node(id="a", name="A", type="group", target="", children=[x])
    b = Node(id="b", name="B", type="group", target="", children=[])
    root = Node(id="root", name="Root", type="group", target="", children=[a, b])

    storage = JsonStorage(tmp_path / "launcher.json")
    storage.save_tree(root)
    win = MainWindow(storage)
    win._refresh_tree_model()
    return win


def test_tree_drop_refreshes_proxy_and_keeps_moved_node_visible(window):
    source_index = window._source_index_for_node_id("x")
    target_index = window._source_index_for_node_id("b")
    assert source_index.isValid()
    assert target_index.isValid()

    source_proxy = window.proxy_model.mapFromSource(source_index)
    target_proxy = window.proxy_model.mapFromSource(target_index)

    moved = window._handle_tree_drop(
        source_proxy,
        target_proxy,
        QAbstractItemView.DropIndicatorPosition.OnItem,
    )

    assert moved is True
    assert window.current_selected_id() == "x"

    moved_ref = find_node_ref(window.root, "x")
    assert moved_ref is not None
    assert moved_ref.parent is not None
    assert moved_ref.parent.id == "b"


def test_refresh_for_tree_change_recomputes_query_visibility(window):
    window.proxy_model.set_query("item x")
    assert window._source_index_for_node_id("x").isValid()

    node_ref = find_node_ref(window.root, "x")
    assert node_ref is not None
    node_ref.node.name = "Renamed"

    window.proxy_model.refresh_for_tree_change()

    source_index = window._source_index_for_node_id("x")
    assert source_index.isValid()
    assert not window.proxy_model.mapFromSource(source_index).isValid()
