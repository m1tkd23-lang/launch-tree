"""Qt model helpers for launcher tree."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtGui import QFont, QIcon, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QApplication, QFileIconProvider, QStyle, QStyleFactory

from .domain import Node
from .icon_logic import icon_mode_for_node


NODE_ROLE = Qt.ItemDataRole.UserRole + 1


class IconResolver:
    def __init__(self):
        self._cache: dict[str, QIcon] = {}
        self._provider = QFileIconProvider()

    def icon_for_node(self, node: Node) -> QIcon:
        mode = icon_mode_for_node(node)

        if mode == "none":
            return QIcon()

        target = (node.target or "").strip()
        cache_key = f"{mode}::{target}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if mode == "exe":
            icon = self._icon_from_path_or_fallback(target, self._style_icon(QStyle.StandardPixmap.SP_ComputerIcon))
            self._cache[cache_key] = icon
            return icon

        # mode == path_optional: show icon only if real icon obtained, otherwise none.
        icon = self._icon_from_path_or_fallback(target, QIcon())
        self._cache[cache_key] = icon
        return icon

    def _style_icon(self, pixmap: QStyle.StandardPixmap) -> QIcon:
        app = QApplication.instance()
        style = app.style() if app is not None else QStyleFactory.create("Fusion")
        return style.standardIcon(pixmap) if style is not None else QIcon()

    def _icon_from_path_or_fallback(self, raw_path: str, fallback: QIcon) -> QIcon:
        try:
            if raw_path and Path(raw_path).exists():
                icon = self._provider.icon(QFileInfo(raw_path))
                if not icon.isNull():
                    return icon
        except Exception:
            pass
        return fallback


def display_name_for_node(node: Node) -> str:
    if node.type == "separator":
        return "—"
    return node.name


class LauncherTreeModel(QStandardItemModel):
    def __init__(self, root: Node):
        super().__init__()
        self.root_node = root
        self.icon_resolver = IconResolver()
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
        item.setIcon(self.icon_resolver.icon_for_node(node))

        if node.type == "group":
            font = QFont(item.font())
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            item.setFont(font)

        if node.target:
            item.setToolTip(node.target)
        for child in node.children:
            item.appendRow(self._item_from_node(child))
        return item
