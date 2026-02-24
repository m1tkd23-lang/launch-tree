"""MainWindow implementation for launch-tree v1 skeleton."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QDropEvent
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .domain import Node, move_node
from .model_qt import LauncherTreeModel, NODE_ROLE
from .storage_json import JsonStorage


class DragDropTreeView(QTreeView):
    def __init__(self, on_drop_move):
        super().__init__()
        self.on_drop_move = on_drop_move

    def dropEvent(self, event: QDropEvent):
        source_index = self.currentIndex()
        target_index = self.indexAt(event.position().toPoint())
        indicator = self.dropIndicatorPosition()

        if self.on_drop_move(source_index, target_index, indicator):
            event.acceptProposedAction()
        else:
            event.ignore()


class MainWindow(QMainWindow):
    def __init__(self, storage: JsonStorage):
        super().__init__()
        self.storage = storage
        self.root = self.storage.load_tree()

        self.setWindowTitle("Launch Tree")
        self.resize(900, 580)

        self.tree = DragDropTreeView(self.handle_tree_drop)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.on_tree_double_clicked)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        self.name_label = QLabel("name: -")
        self.type_label = QLabel("type: -")
        self.target_label = QLabel("target: -")

        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.addWidget(self.name_label)
        detail_layout.addWidget(self.type_label)
        detail_layout.addWidget(self.target_label)
        detail_layout.addStretch(1)

        splitter = QSplitter()
        splitter.addWidget(self.tree)
        splitter.addWidget(detail_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.model = LauncherTreeModel(self.root)
        self.tree.setModel(self.model)
        self.tree.selectionModel().selectionChanged.connect(self.update_detail)

        self.update_detail()

    def safe_call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive GUI handler
            logging.exception("UI operation failed")
            QMessageBox.critical(self, "Error", str(exc))
            return None

    def current_item_and_node(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            return None, None
        item = self.model.itemFromIndex(index)
        if item is None:
            return None, None
        return item, item.data(NODE_ROLE)

    def update_detail(self, *_):
        _, node = self.current_item_and_node()
        if node is None:
            self.name_label.setText("name: -")
            self.type_label.setText("type: -")
            self.target_label.setText("target: -")
            return
        self.name_label.setText(f"name: {node.name}")
        self.type_label.setText(f"type: {node.type}")
        self.target_label.setText(f"target: {node.target}")

    def can_launch_node(self, node: Node | None) -> bool:
        return isinstance(node, Node) and node.type in {"path", "url"} and bool(node.target.strip())

    def on_tree_double_clicked(self, index):
        item = self.model.itemFromIndex(index)
        node = item.data(NODE_ROLE) if item is not None else None
        if self.can_launch_node(node):
            self.safe_call(self.launch_node, node)

    def show_context_menu(self, pos: QPoint):
        self.safe_call(self._show_context_menu, pos)

    def _show_context_menu(self, pos: QPoint):
        click_index = self.tree.indexAt(pos)
        if click_index.isValid():
            self.tree.setCurrentIndex(click_index)

        _, node = self.current_item_and_node()
        launchable = self.can_launch_node(node)

        menu = QMenu(self)
        launch = menu.addAction("Launch")
        launch.setEnabled(launchable)

        copy_target = menu.addAction("Copy target")
        copy_target.setEnabled(launchable)

        menu.addSeparator()
        add_group = menu.addAction("Add Group")
        rename = menu.addAction("Rename")
        delete = menu.addAction("Delete")

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == launch:
            self.safe_call(self.launch_current)
        elif action == copy_target:
            self.safe_call(self.copy_current_target)
        elif action == add_group:
            self.safe_call(self.add_group)
        elif action == rename:
            self.safe_call(self.rename_node)
        elif action == delete:
            self.safe_call(self.delete_node)

    def _node_from_index(self, index) -> Node | None:
        if not index.isValid():
            return None
        item = self.model.itemFromIndex(index)
        return item.data(NODE_ROLE) if item is not None else None

    def _parent_node_and_row_for_drop(self, target_index, indicator, source_node: Node) -> tuple[Node, int]:
        if not target_index.isValid() or indicator == QAbstractItemView.DropIndicatorPosition.OnViewport:
            return self.root, len(self.root.children)

        target_node = self._node_from_index(target_index)
        target_item = self.model.itemFromIndex(target_index)
        if target_node is None or target_item is None:
            return self.root, len(self.root.children)

        if indicator == QAbstractItemView.DropIndicatorPosition.OnItem:
            if target_node.type == "group":
                return target_node, len(target_node.children)
            parent_item = target_item.parent()
            parent_node = self.root if parent_item is None else parent_item.data(NODE_ROLE)
            parent_node = parent_node if isinstance(parent_node, Node) else self.root
            return parent_node, target_item.row() + 1

        parent_item = target_item.parent()
        parent_node = self.root if parent_item is None else parent_item.data(NODE_ROLE)
        parent_node = parent_node if isinstance(parent_node, Node) else self.root

        row = target_item.row()
        if indicator == QAbstractItemView.DropIndicatorPosition.BelowItem:
            row += 1
        return parent_node, row

    def handle_tree_drop(self, source_index, target_index, indicator) -> bool:
        return bool(self.safe_call(self._handle_tree_drop, source_index, target_index, indicator))

    def _handle_tree_drop(self, source_index, target_index, indicator) -> bool:
        source_node = self._node_from_index(source_index)
        if source_node is None:
            return False

        dest_parent, dest_row = self._parent_node_and_row_for_drop(target_index, indicator, source_node)

        moved = move_node(
            root=self.root,
            source_id=source_node.id,
            destination_parent_id=dest_parent.id,
            destination_row=dest_row,
        )
        if not moved:
            logging.info("Rejected drag/drop move source=%s dest_parent=%s", source_node.id, dest_parent.id)
            return False

        self.model.rebuild()
        self.tree.expandAll()
        self.persist()
        return True

    def launch_current(self):
        _, node = self.current_item_and_node()
        if self.can_launch_node(node):
            self.launch_node(node)

    def copy_current_target(self):
        _, node = self.current_item_and_node()
        if not self.can_launch_node(node):
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(node.target)

    def launch_node(self, node: Node):
        if node.type == "path":
            self._launch_path(node)
        elif node.type == "url":
            self._launch_url(node)

    def _launch_path(self, node: Node):
        target = Path(node.target)
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {node.target}")

        starter = getattr(os, "startfile", None)
        if starter is None:
            raise RuntimeError("os.startfile is unavailable on this platform")

        try:
            starter(str(target))
            logging.info("Launched path target: %s", target)
        except Exception:
            logging.exception("Failed launching path target: %s", target)
            raise

    def _launch_url(self, node: Node):
        url = QUrl(node.target)
        if not url.isValid() or not url.scheme():
            raise ValueError(f"Invalid URL: {node.target}")

        ok = QDesktopServices.openUrl(url)
        if not ok:
            raise RuntimeError(f"Failed to open URL: {node.target}")
        logging.info("Launched URL target: %s", node.target)

    def _parent_for_new_group(self, node: Node, item) -> Node:
        if node.type == "group":
            return node
        parent_item = item.parent()
        if parent_item is None:
            return self.root
        parent = parent_item.data(NODE_ROLE)
        return parent if isinstance(parent, Node) else self.root

    def add_group(self):
        item, node = self.current_item_and_node()
        parent_node = self.root if node is None else self._parent_for_new_group(node, item)

        name, ok = QInputDialog.getText(self, "Add Group", "Group name:")
        if not ok or not name.strip():
            return
        parent_node.children.append(Node.make(name=name.strip(), node_type="group"))
        self.model.rebuild()
        self.tree.expandAll()
        self.persist()

    def rename_node(self):
        _, node = self.current_item_and_node()
        if node is None:
            return
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=node.name)
        if not ok or not name.strip():
            return
        node.name = name.strip()
        self.model.rebuild()
        self.persist()

    def delete_node(self):
        item, node = self.current_item_and_node()
        if node is None:
            return

        result = QMessageBox.question(
            self,
            "Delete",
            f"Delete '{node.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        parent_item = item.parent()
        parent_node = self.root if parent_item is None else parent_item.data(NODE_ROLE)
        if not isinstance(parent_node, Node):
            parent_node = self.root

        parent_node.children = [child for child in parent_node.children if child.id != node.id]
        self.model.rebuild()
        self.persist()

    def persist(self):
        self.storage.save_tree(self.root)
