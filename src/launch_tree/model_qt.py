"""Qt model helpers for launcher tree."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QApplication, QFileIconProvider, QStyle, QStyleFactory

from .domain import Node
from .icon_logic import icon_category_for_node


NODE_ROLE = Qt.ItemDataRole.UserRole + 1


class VirtualNode:
    def __init__(self, node_id: str, name: str, node_type: str):
        self.id = node_id
        self.name = name
        self.type = node_type
        self.target = ""
        self.children: list[Node] = []


class IconResolver:
    def __init__(self):
        self._cache: dict[str, QIcon] = {}
        self._provider = QFileIconProvider()

    def icon_for_node(self, node: Node | VirtualNode) -> QIcon:
        if isinstance(node, VirtualNode):
            if node.id == "virtual:favorites":
                return self._style_icon(QStyle.StandardPixmap.SP_DialogYesButton)
            if node.id == "virtual:recent":
                return self._style_icon(QStyle.StandardPixmap.SP_BrowserReload)

        category = icon_category_for_node(node)

        if category == "path_exe":
            target = (node.target or "").strip()
            cache_key = f"exe::{target}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            icon = self._icon_from_path_or_fallback(
                target, self._style_icon(QStyle.StandardPixmap.SP_ComputerIcon)
            )
            self._cache[cache_key] = icon
            return icon

        cache_key = f"cat::{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if category in {"group", "path_folder"}:
            icon = self._style_icon(QStyle.StandardPixmap.SP_DirIcon)
        elif category == "url":
            icon = self._style_icon(QStyle.StandardPixmap.SP_DriveNetIcon)
        elif category == "path_file":
            icon = self._style_icon(QStyle.StandardPixmap.SP_FileIcon)
        elif category == "separator":
            icon = QIcon()
        else:
            icon = self._style_icon(QStyle.StandardPixmap.SP_FileIcon)

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


def display_name_for_node(node: Node | VirtualNode) -> str:
    if isinstance(node, VirtualNode):
        return node.name
    if node.type == "group":
        return node.name
    if node.type == "url":
        return node.name
    if node.type == "path":
        return node.name
    if node.type == "separator":
        return "—"
    return node.name


class LauncherTreeModel(QStandardItemModel):
    def __init__(self, root: Node, user_state: dict | None = None, view_mode: str = "all"):
        super().__init__()
        self.root_node = root
        self.icon_resolver = IconResolver()
        self.user_state = user_state or {"favorites": {}, "recent": [], "ui": {"view_mode": "all"}}
        self.view_mode = view_mode
        self.node_lookup: dict[str, Node] = {}
        self.setHorizontalHeaderLabels(["Launch Tree"])
        self.rebuild()

    def set_view_state(self, user_state: dict, view_mode: str) -> None:
        self.user_state = user_state
        self.view_mode = view_mode

    def rebuild(self) -> None:
        self.clear()
        self.setHorizontalHeaderLabels(["Launch Tree"])
        invisible = self.invisibleRootItem()
        invisible.setData(self.root_node, NODE_ROLE)

        self.node_lookup = {}
        self._collect_lookup(self.root_node)

        if self.view_mode in {"all", "favorites"}:
            fav_item = self._virtual_group_item("virtual:favorites", "★ Favorites", self._favorite_nodes())
            invisible.appendRow(fav_item)

        if self.view_mode in {"all", "recent"}:
            recent_item = self._virtual_group_item("virtual:recent", "🕘 Recent", self._recent_nodes())
            invisible.appendRow(recent_item)

        if self.view_mode == "all":
            for child in self.root_node.children:
                invisible.appendRow(self._item_from_node(child))

    def _collect_lookup(self, node: Node) -> None:
        self.node_lookup[node.id] = node
        for child in node.children:
            self._collect_lookup(child)

    def _favorite_nodes(self) -> list[Node]:
        favorites = self.user_state.get("favorites") if isinstance(self.user_state, dict) else {}
        if not isinstance(favorites, dict):
            return []
        nodes: list[Node] = []
        for node_id, enabled in favorites.items():
            if not enabled:
                continue
            node = self.node_lookup.get(str(node_id))
            if node is not None:
                nodes.append(node)
        return nodes

    def _recent_nodes(self) -> list[Node]:
        recent = self.user_state.get("recent") if isinstance(self.user_state, dict) else []
        if not isinstance(recent, list):
            return []
        nodes: list[Node] = []
        for entry in recent:
            if not isinstance(entry, dict):
                continue
            node = self.node_lookup.get(str(entry.get("id") or ""))
            if node is not None:
                nodes.append(node)
        return nodes

    def _virtual_group_item(self, virtual_id: str, label: str, children: list[Node]) -> QStandardItem:
        virtual = VirtualNode(node_id=virtual_id, name=label, node_type="group")
        item = self._base_item(virtual)
        for child in children:
            item.appendRow(self._item_from_node(child))
        return item

    def _base_item(self, node: Node | VirtualNode) -> QStandardItem:
        item = QStandardItem(display_name_for_node(node))
        item.setEditable(False)
        item.setData(node, NODE_ROLE)
        item.setIcon(self.icon_resolver.icon_for_node(node))
        if node.target:
            item.setToolTip(node.target)
        return item

    def _item_from_node(self, node: Node) -> QStandardItem:
        item = self._base_item(node)
        for child in node.children:
            item.appendRow(self._item_from_node(child))
        return item
