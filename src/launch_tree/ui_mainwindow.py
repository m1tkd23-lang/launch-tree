"""MainWindow implementation for launch-tree v1 skeleton."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import (
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

from .domain import Node
from .model_qt import LauncherTreeModel, NODE_ROLE
from .storage_json import JsonStorage


class MainWindow(QMainWindow):
    def __init__(self, storage: JsonStorage):
        super().__init__()
        self.storage = storage
        self.root = self.storage.load_tree()

        self.setWindowTitle("Launch Tree")
        self.resize(900, 580)

        self.tree = QTreeView()
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

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

    def show_context_menu(self, pos: QPoint):
        self.safe_call(self._show_context_menu, pos)

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        add_group = menu.addAction("Add Group")
        rename = menu.addAction("Rename")
        delete = menu.addAction("Delete")

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == add_group:
            self.safe_call(self.add_group)
        elif action == rename:
            self.safe_call(self.rename_node)
        elif action == delete:
            self.safe_call(self.delete_node)

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
