from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from launch_tree.domain import Node
from launch_tree.storage_json import JsonStorage, load_user_state, set_user_state_path
from launch_tree.ui_mainwindow import MainWindow


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def window(tmp_path: Path, app):
    storage = JsonStorage(tmp_path / "launcher.json")
    root = Node(id="root", name="Root", type="group", target="", children=[])
    storage.save_tree(root)
    win = MainWindow(storage)
    return win


def test_launch_path_calls_startfile(window, monkeypatch, tmp_path: Path):
    target = tmp_path / "sample.txt"
    target.write_text("ok", encoding="utf-8")
    called = {}

    def fake_startfile(path):
        called["path"] = path

    monkeypatch.setattr(os, "startfile", fake_startfile, raising=False)

    node = Node(id="n1", name="path", type="path", target=str(target), children=[])
    window.launch_node(node)

    assert called["path"] == str(target)


def test_launch_url_calls_qdesktopservices(window, monkeypatch):
    called = {}

    def fake_open_url(url):
        called["url"] = url.toString()
        return True

    monkeypatch.setattr("launch_tree.ui_mainwindow.QDesktopServices.openUrl", fake_open_url)

    node = Node(id="n2", name="url", type="url", target="https://example.com", children=[])
    window.launch_node(node)

    assert called["url"] == "https://example.com"


def test_launch_invalid_url_shows_error(window, monkeypatch):
    errors = []

    def fake_critical(*args):
        errors.append(args)
        return 0

    monkeypatch.setattr("launch_tree.ui_mainwindow.QMessageBox.critical", fake_critical)

    bad = Node(id="n3", name="bad", type="url", target="not a valid url", children=[])
    window.safe_call(window.launch_node, bad)

    assert errors


def test_recent_updated_even_when_launch_fails(window):
    set_user_state_path(window.storage.path.parent / "user_state.json")

    missing = Node(id="n4", name="missing", type="path", target="/not/found", children=[])
    window.safe_call(window.launch_node, missing)

    state = load_user_state()
    assert state["recent"][0]["id"] == "n4"


def test_recent_updated_on_context_launch(window, monkeypatch):
    set_user_state_path(window.storage.path.parent / "user_state.json")
    called = {}

    def fake_open_url(url):
        called["url"] = url.toString()
        return True

    monkeypatch.setattr("launch_tree.ui_mainwindow.QDesktopServices.openUrl", fake_open_url)

    good = Node(id="n5", name="good", type="url", target="https://example.com", children=[])
    window.launch_node(good)

    state = load_user_state()
    assert called["url"] == "https://example.com"
    assert state["recent"][0]["id"] == "n5"
