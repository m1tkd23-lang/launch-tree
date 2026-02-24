"""Qt model helpers for launcher tree."""

from __future__ import annotations

from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtCore import Qt

from .domain import Node


NODE_ROLE = Qt.ItemDataRole.UserRole + 1


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
        item = QStandardItem(node.name)
        item.setEditable(False)
        item.setData(node, NODE_ROLE)
        for child in node.children:
            item.appendRow(self._item_from_node(child))
        return item
