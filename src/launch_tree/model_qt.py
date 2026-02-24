"""Qt model helpers for launcher tree."""

from __future__ import annotations

from pathlib import PurePath

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel

from .domain import Node


NODE_ROLE = Qt.ItemDataRole.UserRole + 1


def display_name_for_node(node: Node) -> str:
    if node.type == "group":
        return f"📁 {node.name}"
    if node.type == "url":
        return f"🌐 {node.name}"
    if node.type == "path":
        target = (node.target or "").strip()
        suffix = PurePath(target).suffix.lower()
        if suffix == ".exe":
            return f"⚙️ {node.name}"
        looks_folder = target.endswith("/") or target.endswith("\\") or suffix == ""
        if looks_folder:
            return f"🗂️ {node.name}"
        return f"📄 {node.name}"
    if node.type == "separator":
        return "—"
    return node.name


class LauncherTreeModel(QStandardItemModel):
    def __init__(self, root: Node):
        super().__init__()
        self.root_node = root
        self.setHorizontalHeaderLabels(["Launch Tree"])
        self.rebuild()

    def rebuild(self) -> None:
        self.clear()
        self.setHorizontalHeaderLabels(["Launch Tree"])
        invisible = self.invisibleRootItem()
        invisible.setData(self.root_node, NODE_ROLE)
        for child in self.root_node.children:
            invisible.appendRow(self._item_from_node(child))

    def _item_from_node(self, node: Node) -> QStandardItem:
        item = QStandardItem(display_name_for_node(node))
        item.setEditable(False)
        item.setData(node, NODE_ROLE)
        if node.target:
            item.setToolTip(node.target)
        for child in node.children:
            item.appendRow(self._item_from_node(child))
        return item
