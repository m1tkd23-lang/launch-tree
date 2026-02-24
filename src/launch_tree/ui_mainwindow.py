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
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .domain import Node, insert_relative_to_selection, move_node
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
        self.resize(1000, 650)

        self.tree = DragDropTreeView(self.handle_tree_drop)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.on_tree_double_clicked)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setUniformRowHeights(False)

        detail_panel = QWidget(objectName="detailPanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(18, 18, 18, 18)
        detail_layout.setSpacing(16)

        self.launch_button = QPushButton("Launch")
        self.launch_button.clicked.connect(lambda: self.safe_call(self.launch_current))
        self.copy_target_button = QPushButton("Copy target")
        self.copy_target_button.clicked.connect(lambda: self.safe_call(self.copy_current_target))

        detail_layout.addWidget(self.launch_button)
        detail_layout.addWidget(self.copy_target_button)

        detail_card = QFrame(objectName="detailCard")
        card_layout = QVBoxLayout(detail_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        title = QLabel("Details", objectName="detailTitle")
        self.name_label = QLabel("name: -", objectName="detailValue")
        self.type_label = QLabel("type: -", objectName="detailValue")
        self.target_label = QLabel("target: -", objectName="detailValue")
        self.target_label.setWordWrap(True)

        card_layout.addWidget(title)
        card_layout.addWidget(self.name_label)
        card_layout.addWidget(self.type_label)
        card_layout.addWidget(self.target_label)

        detail_layout.addWidget(detail_card)
        detail_layout.addStretch(1)

        splitter = QSplitter()
        splitter.addWidget(self.tree)
        splitter.addWidget(detail_panel)
        splitter.setSizes([600, 400])

        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
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

    def current_selected_id(self) -> str | None:
        _, node = self.current_item_and_node()
        return node.id if isinstance(node, Node) else None

    def update_detail(self, *_):
        _, node = self.current_item_and_node()
        if node is None:
            self.name_label.setText("name: -")
            self.type_label.setText("type: -")
            self.target_label.setText("target: -")
            self.launch_button.setEnabled(False)
            self.copy_target_button.setEnabled(False)
            return

        self.name_label.setText(f"name: {node.name}")
        self.type_label.setText(f"type: {node.type}")
        self.target_label.setText(f"target: {node.target}")

        launchable = self.can_launch_node(node)
        self.launch_button.setEnabled(launchable)
        self.copy_target_button.setEnabled(launchable)

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
        add_path_file = menu.addAction("Add Path Item (File)...")
        add_path_folder = menu.addAction("Add Path Item (Folder)...")
        add_url = menu.addAction("Add URL Item...")
        add_separator = menu.addAction("Add Separator")
        rename = menu.addAction("Rename")
        delete = menu.addAction("Delete")

        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if action == launch:
            self.safe_call(self.launch_current)
        elif action == copy_target:
            self.safe_call(self.copy_current_target)
        elif action == add_group:
            self.safe_call(self.add_group)
        elif action == add_path_file:
            self.safe_call(self.add_path_item_file)
        elif action == add_path_folder:
            self.safe_call(self.add_path_item_folder)
        elif action == add_url:
            self.safe_call(self.add_url_item)
        elif action == add_separator:
            self.safe_call(self.add_separator_item)
        elif action == rename:
            self.safe_call(self.rename_node)
        elif action == delete:
            self.safe_call(self.delete_node)

    def _insert_new_node(self, node: Node) -> bool:
        inserted = insert_relative_to_selection(self.root, self.current_selected_id(), node)
        if not inserted:
            return False
        self.model.rebuild()
        self.tree.expandAll()
        self.persist()
        return True

    def create_and_insert_item(self, item_type: str, target: str, name: str) -> bool:
        clean_target = target.strip()
        clean_name = name.strip()
        if item_type in {"path", "url"} and not clean_target:
            return False
        if not clean_name:
            return False
        return self._insert_new_node(Node.make(name=clean_name, node_type=item_type, target=clean_target))

    def add_path_item_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if not path:
            return
        name = Path(path).name
        self.create_and_insert_item("path", path, name)

    def add_path_item_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return
        name = Path(folder).name or folder
        self.create_and_insert_item("path", folder, name)

    def add_url_item(self):
        url, ok = QInputDialog.getText(self, "Add URL Item", "URL:")
        if not ok or not url.strip():
            return
        url = url.strip()

        if not (url.startswith("http://") or url.startswith("https://")):
            choice = QMessageBox.question(
                self,
                "URL scheme warning",
                "URL は http/https を推奨します。続行しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return

        self.create_and_insert_item("url", url, url)

    def add_separator_item(self):
        self.create_and_insert_item("separator", "", "----------")

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

    def add_group(self):
        name, ok = QInputDialog.getText(self, "Add Group", "Group name:")
        if not ok or not name.strip():
            return

        self._insert_new_node(Node.make(name=name.strip(), node_type="group"))

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
