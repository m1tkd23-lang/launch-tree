"""MainWindow implementation for launch-tree v1 skeleton."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PyQt6.QtCore import QModelIndex, QPoint, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QDesktopServices,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeySequence,
    QMouseEvent,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QComboBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .domain import Node, find_node_ref, insert_relative_to_selection, move_node
from .drop_import_logic import build_drop_entries
from .edit_logic import ALLOWED_NODE_TYPES, apply_node_update
from .model_filter import TreeFilterProxyModel
from .model_qt import LauncherTreeModel, NODE_ROLE, VirtualNode
from .storage_json import JsonStorage, load_user_state, save_user_state, set_user_state_path, update_recent


class DragDropTreeView(QTreeView):
    def __init__(self, on_drop_move, on_external_drop):
        super().__init__()
        self.on_drop_move = on_drop_move
        self.on_external_drop = on_external_drop

    def dragEnterEvent(self, event: QDragEnterEvent):
        # 外部ドロップ（Explorer等）を許可
        if event.mimeData().hasUrls() and (event.source() is None or event.source() is not self):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls() and (event.source() is None or event.source() is not self):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        target_index = self.indexAt(event.position().toPoint())
        indicator = self.dropIndicatorPosition()

        # 外部ドロップ（Explorer等）：登録処理へ
        if event.mimeData().hasUrls() and (event.source() is None or event.source() is not self):
            raw_values: list[str] = []
            for qurl in event.mimeData().urls():
                raw_values.append(qurl.toLocalFile() if qurl.isLocalFile() else qurl.toString())
            if self.on_external_drop(raw_values, target_index, indicator):
                event.acceptProposedAction()
            else:
                event.ignore()
            return

        # 内部DnD：並び替え/階層移動（既存処理）
        selected_indexes = self.selectedIndexes()
        source_index = selected_indexes[0] if selected_indexes else self.currentIndex()
        if self.on_drop_move(source_index, target_index, indicator):
            event.acceptProposedAction()
        else:
            event.ignore()


class EditableValueLabel(QLabel):
    double_clicked = pyqtSignal(str)

    def __init__(self, field_name: str, text: str = ""):
        super().__init__(text)
        self.field_name = field_name

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.field_name)
        super().mouseDoubleClickEvent(event)


class WindowHeader(QWidget):
    def __init__(self, window: QMainWindow):
        super().__init__(objectName="windowHeader")
        self.window = window
        self.drag_offset: QPoint | None = None
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        title = QLabel("Launch Tree", objectName="windowHeaderTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self.min_btn = QPushButton("_", objectName="titleBarButton")
        self.min_btn.setToolTip("Minimize")
        self.min_btn.clicked.connect(self.window.showMinimized)

        self.close_btn = QPushButton("×", objectName="titleBarButtonClose")
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self.window.close)

        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.window.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.drag_offset = None
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, storage: JsonStorage):
        super().__init__()
        self.storage = storage
        self.root = self.storage.load_tree()
        set_user_state_path(self.storage.path.parent / "user_state.json")
        self.user_state = load_user_state()
        self.view_mode = str(self.user_state.get("ui", {}).get("view_mode") or "all")
        if self.view_mode not in {"all", "favorites", "recent"}:
            self.view_mode = "all"

        self.setWindowTitle("Launch Tree")
        self.resize(1000, 650)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        self.tree = DragDropTreeView(self.handle_tree_drop, self.handle_external_drop)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.on_tree_double_clicked)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by name / target / type...")
        self.search_box.textChanged.connect(self.on_search_changed)
        QShortcut(QKeySequence("Esc"), self.search_box, activated=self.search_box.clear)

        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItem("All", "all")
        self.view_mode_combo.addItem("Favorites", "favorites")
        self.view_mode_combo.addItem("Recent", "recent")
        self._set_view_mode_combo(self.view_mode)
        self.view_mode_combo.currentIndexChanged.connect(self.on_view_mode_changed)

        self.expand_all_button = QPushButton("Expand all")
        self.expand_all_button.clicked.connect(self.tree.expandAll)
        self.collapse_all_button = QPushButton("Collapse all")
        self.collapse_all_button.clicked.connect(self.tree.collapseAll)

        detail_panel = QWidget(objectName="detailPanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(18, 18, 18, 18)
        detail_layout.setSpacing(16)

        self.launch_button = QPushButton("Launch")
        self.launch_button.clicked.connect(lambda: self.safe_call(self.launch_current))
        self.copy_target_button = QPushButton("Copy target")
        self.copy_target_button.clicked.connect(lambda: self.safe_call(self.copy_current_target))
        self.favorite_button = QPushButton("★ Favorite")
        self.favorite_button.setCheckable(True)
        self.favorite_button.clicked.connect(lambda: self.safe_call(self.toggle_current_favorite))

        detail_layout.addWidget(self.launch_button)
        detail_layout.addWidget(self.copy_target_button)
        detail_layout.addWidget(self.favorite_button)

        detail_card = QFrame(objectName="detailCard")
        card_layout = QVBoxLayout(detail_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        title = QLabel("Details", objectName="detailTitle")

        name_key = QLabel("name", objectName="detailTitle")
        self.name_value = EditableValueLabel("name", "-")
        self.name_value.setObjectName("detailValue")

        type_key = QLabel("type", objectName="detailTitle")
        self.type_value = EditableValueLabel("type", "-")
        self.type_value.setObjectName("detailValue")

        target_key = QLabel("target", objectName="detailTitle")
        self.target_value = EditableValueLabel("target", "-")
        self.target_value.setObjectName("detailValue")
        self.target_value.setWordWrap(True)

        self.name_value.double_clicked.connect(lambda field: self.safe_call(self.edit_detail_field, field))
        self.type_value.double_clicked.connect(lambda field: self.safe_call(self.edit_detail_field, field))
        self.target_value.double_clicked.connect(lambda field: self.safe_call(self.edit_detail_field, field))

        card_layout.addWidget(title)
        card_layout.addWidget(name_key)
        card_layout.addWidget(self.name_value)
        card_layout.addWidget(type_key)
        card_layout.addWidget(self.type_value)
        card_layout.addWidget(target_key)
        card_layout.addWidget(self.target_value)

        detail_layout.addWidget(detail_card)
        detail_layout.addStretch(1)

        splitter = QSplitter()
        splitter.addWidget(self.tree)
        splitter.addWidget(detail_panel)
        splitter.setSizes([600, 400])

        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)
        self.header = WindowHeader(self)
        main_layout.addWidget(self.header)
        search_row = QWidget()
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.addWidget(self.search_box, 1)
        search_layout.addWidget(self.expand_all_button)
        search_layout.addWidget(self.collapse_all_button)
        search_layout.addWidget(self.view_mode_combo)

        main_layout.addWidget(search_row)
        main_layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.source_model = LauncherTreeModel(self.root, self.user_state, self.view_mode)
        self.proxy_model = TreeFilterProxyModel(self.root)
        self.proxy_model.setSourceModel(self.source_model)
        self.tree.setModel(self.proxy_model)
        self.tree.selectionModel().selectionChanged.connect(self.update_detail)

        self.update_detail()

    def safe_call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive GUI handler
            logging.exception("UI operation failed")
            QMessageBox.critical(self, "Error", str(exc))
            return None

    def _set_view_mode_combo(self, mode: str) -> None:
        idx = self.view_mode_combo.findData(mode)
        if idx >= 0:
            self.view_mode_combo.setCurrentIndex(idx)

    def _refresh_tree_model(self, expand: bool = False, preferred_selected_id: str | None = None) -> None:
        self.source_model.set_view_state(self.user_state, self.view_mode)
        self.source_model.rebuild()
        self.proxy_model.set_query(self.search_box.text())
        # Structural changes can leave proxy visibility stale; force recomputation before selection restore.
        self.proxy_model.refresh_for_tree_change()
        if expand:
            self.tree.expandAll()
        self._ensure_node_visible(preferred_selected_id)


    def _source_index_for_node_id(self, node_id: str | None):
        if not node_id:
            return QModelIndex()

        def walk(parent_index):
            rows = self.source_model.rowCount(parent_index)
            for row in range(rows):
                idx = self.source_model.index(row, 0, parent_index)
                node = self._node_from_source_index(idx)
                if isinstance(node, Node) and node.id == node_id:
                    return idx
                child_match = walk(idx)
                if child_match.isValid():
                    return child_match
            return QModelIndex()

        return walk(QModelIndex())

    def _ensure_node_visible(self, node_id: str | None) -> None:
        source_index = self._source_index_for_node_id(node_id)
        if not source_index.isValid():
            return

        proxy_index = self.proxy_model.mapFromSource(source_index)
        if not proxy_index.isValid():
            return

        parent = proxy_index.parent()
        while parent.isValid():
            self.tree.expand(parent)
            parent = parent.parent()

        self.tree.setCurrentIndex(proxy_index)
        self.tree.scrollTo(proxy_index, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _save_user_state(self) -> None:
        save_user_state(self.user_state)

    def on_view_mode_changed(self) -> None:
        selected_mode = str(self.view_mode_combo.currentData() or "all")
        if selected_mode not in {"all", "favorites", "recent"}:
            selected_mode = "all"
        self.view_mode = selected_mode
        ui_state = self.user_state.setdefault("ui", {})
        if not isinstance(ui_state, dict):
            self.user_state["ui"] = {"view_mode": self.view_mode}
        else:
            ui_state["view_mode"] = self.view_mode
        self._save_user_state()
        self._refresh_tree_model(expand=self.view_mode != "all")
        self.update_detail()

    def on_search_changed(self, text: str) -> None:
        self.proxy_model.set_query(text)
        if text.strip():
            self.expand_search_matches()
        else:
            self.tree.collapseAll()

    def expand_search_matches(self) -> None:
        def visit(parent_index):
            row_count = self.proxy_model.rowCount(parent_index)
            for row in range(row_count):
                idx = self.proxy_model.index(row, 0, parent_index)
                if self.proxy_model.rowCount(idx) > 0:
                    self.tree.expand(idx)
                    visit(idx)

        visit(QModelIndex())

    def map_to_source(self, index):
        if not index.isValid():
            return index
        return self.proxy_model.mapToSource(index)

    def current_item_and_node(self):
        proxy_index = self.tree.currentIndex()
        if not proxy_index.isValid():
            return None, None
        source_index = self.map_to_source(proxy_index)
        if not source_index.isValid():
            return None, None
        item = self.source_model.itemFromIndex(source_index)
        if item is None:
            return None, None
        return item, item.data(NODE_ROLE)

    def _resolve_real_node(self, node) -> Node | None:
        if isinstance(node, Node):
            return node
        return None

    def current_selected_id(self) -> str | None:
        _, node = self.current_item_and_node()
        resolved = self._resolve_real_node(node)
        return resolved.id if isinstance(resolved, Node) else None

    def edit_detail_field(self, field_name: str) -> None:
        _, selected = self.current_item_and_node()
        node = self._resolve_real_node(selected)
        if node is None:
            return

        if field_name == "name":
            value, ok = QInputDialog.getText(self, "Edit name", "name:", text=node.name)
            if not ok:
                return
            self.apply_detail_update(node, new_name=value)
            return

        if field_name == "type":
            options = sorted(ALLOWED_NODE_TYPES)
            current_index = options.index(node.type) if node.type in options else 0
            new_type, ok = QInputDialog.getItem(self, "Edit type", "type:", options, current_index, False)
            if not ok:
                return

            target_candidate = node.target
            if new_type in {"path", "url"} and not target_candidate.strip():
                target_candidate, ok_target = QInputDialog.getText(
                    self, "Target required", "target:", text=target_candidate
                )
                if not ok_target:
                    return

            if new_type == "url" and target_candidate.strip() and not target_candidate.startswith(("http://", "https://")):
                res = QMessageBox.question(
                    self,
                    "URL scheme warning",
                    "URL は http/https を推奨します。続行しますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if res != QMessageBox.StandardButton.Yes:
                    return

            self.apply_detail_update(node, new_type=new_type, new_target=target_candidate)
            return

        if field_name == "target":
            if node.type in {"group", "separator"}:
                QMessageBox.information(self, "Target disabled", "group/separator の target は編集できません。")
                return

            value, ok = QInputDialog.getText(self, "Edit target", "target:", text=node.target)
            if not ok:
                return

            if node.type == "url" and value.strip() and not value.startswith(("http://", "https://")):
                res = QMessageBox.question(
                    self,
                    "URL scheme warning",
                    "URL は http/https を推奨します。続行しますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if res != QMessageBox.StandardButton.Yes:
                    return

            self.apply_detail_update(node, new_target=value)

    def apply_detail_update(
        self,
        node: Node,
        *,
        new_name: str | None = None,
        new_type: str | None = None,
        new_target: str | None = None,
    ) -> bool:
        ok, error = apply_node_update(node, new_name=new_name, new_type=new_type, new_target=new_target)
        if not ok:
            QMessageBox.warning(self, "Validation Error", error or "Invalid input")
            return False

        self._refresh_tree_model()
        self.persist()
        logging.info("Updated node id=%s name=%s type=%s target=%s", node.id, node.name, node.type, node.target)
        self.update_detail()
        return True

    def update_detail(self, *_):
        _, selected = self.current_item_and_node()
        node = self._resolve_real_node(selected)
        if node is None:
            self.name_value.setText("-")
            self.type_value.setText("-")
            self.target_value.setText("-")
            self.name_value.setEnabled(False)
            self.type_value.setEnabled(False)
            self.target_value.setEnabled(False)
            self.launch_button.setEnabled(False)
            self.copy_target_button.setEnabled(False)
            self.favorite_button.setEnabled(False)
            self.favorite_button.setChecked(False)
            return

        self.name_value.setText(node.name)
        self.type_value.setText(node.type)
        if node.type in {"group", "separator"}:
            self.target_value.setText("(disabled)")
            self.target_value.setEnabled(False)
        else:
            self.target_value.setText(node.target)
            self.target_value.setEnabled(True)

        self.name_value.setEnabled(True)
        self.type_value.setEnabled(True)

        launchable = self.can_launch_node(node)
        self.launch_button.setEnabled(launchable)
        self.copy_target_button.setEnabled(launchable)
        favorite_capable = node.type in {"path", "url"}
        self.favorite_button.setEnabled(favorite_capable)
        is_favorite = bool(self.user_state.get("favorites", {}).get(node.id))
        self.favorite_button.setChecked(is_favorite)

    def can_launch_node(self, node: Node | None) -> bool:
        return isinstance(node, Node) and node.type in {"path", "url"} and bool(node.target.strip())

    def toggle_current_favorite(self) -> None:
        _, selected = self.current_item_and_node()
        node = self._resolve_real_node(selected)
        if node is None or node.type not in {"path", "url"}:
            return

        favorites = self.user_state.setdefault("favorites", {})
        if not isinstance(favorites, dict):
            favorites = {}
            self.user_state["favorites"] = favorites

        if self.favorite_button.isChecked():
            favorites[node.id] = True
        else:
            favorites.pop(node.id, None)

        self._save_user_state()
        self._refresh_tree_model()
        self.update_detail()

    def _record_recent(self, node_id: str) -> None:
        self.user_state = update_recent(self.user_state, node_id)
        self._save_user_state()

    def on_tree_double_clicked(self, proxy_index):
        source_index = self.map_to_source(proxy_index)
        item = self.source_model.itemFromIndex(source_index)
        node = self._resolve_real_node(item.data(NODE_ROLE) if item is not None else None)
        if self.can_launch_node(node):
            self.safe_call(self.launch_node, node)

    def show_context_menu(self, pos: QPoint):
        self.safe_call(self._show_context_menu, pos)

    def _show_context_menu(self, pos: QPoint):
        click_proxy_index = self.tree.indexAt(pos)
        if click_proxy_index.isValid():
            self.tree.setCurrentIndex(click_proxy_index)

        _, selected = self.current_item_and_node()
        node = self._resolve_real_node(selected)
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
        self._refresh_tree_model(preferred_selected_id=node.id)

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

    def _node_from_source_index(self, source_index) -> Node | None:
        if not source_index.isValid():
            return None
        item = self.source_model.itemFromIndex(source_index)
        node = item.data(NODE_ROLE) if item is not None else None
        return node if isinstance(node, Node) else None

    def _is_under_virtual_node(self, source_index) -> bool:
        current = source_index
        while current.isValid():
            item = self.source_model.itemFromIndex(current)
            node = item.data(NODE_ROLE) if item is not None else None
            if isinstance(node, VirtualNode):
                return True
            current = current.parent()
        return False

    def _row_within_node_siblings(self, target_item) -> int:
        parent_item = target_item.parent()
        container = self.source_model.invisibleRootItem() if parent_item is None else parent_item

        node_row = 0
        for row in range(target_item.row()):
            sibling = container.child(row)
            sibling_node = sibling.data(NODE_ROLE) if sibling is not None else None
            if isinstance(sibling_node, Node):
                node_row += 1
        return node_row

    def _parent_node_and_row_for_drop(self, source_target_index, indicator) -> tuple[Node, int]:
        if not source_target_index.isValid() or indicator == QAbstractItemView.DropIndicatorPosition.OnViewport:
            return self.root, len(self.root.children)

        target_node = self._node_from_source_index(source_target_index)
        target_item = self.source_model.itemFromIndex(source_target_index)
        if target_node is None or target_item is None:
            return self.root, len(self.root.children)

        if indicator == QAbstractItemView.DropIndicatorPosition.OnItem:
            if target_node.type == "group":
                return target_node, len(target_node.children)
            parent_item = target_item.parent()
            parent_node = self.root if parent_item is None else parent_item.data(NODE_ROLE)
            parent_node = parent_node if isinstance(parent_node, Node) else self.root
            return parent_node, self._row_within_node_siblings(target_item) + 1

        parent_item = target_item.parent()
        parent_node = self.root if parent_item is None else parent_item.data(NODE_ROLE)
        parent_node = parent_node if isinstance(parent_node, Node) else self.root

        row = self._row_within_node_siblings(target_item)
        if indicator == QAbstractItemView.DropIndicatorPosition.BelowItem:
            row += 1
        return parent_node, row

    def handle_external_drop(self, raw_values: list[str], target_proxy_index, indicator) -> bool:
        return bool(self.safe_call(self._handle_external_drop, raw_values, target_proxy_index, indicator))

    def _handle_external_drop(self, raw_values: list[str], target_proxy_index, indicator) -> bool:
        entries = build_drop_entries(raw_values)
        if not entries:
            return False

        target_index = self.map_to_source(target_proxy_index)
        dest_parent, dest_row = self._parent_node_and_row_for_drop(target_index, indicator)

        # group配下 or root直下に追加可（rootはtypeがgroupじゃない可能性があるため特別扱い）
        if dest_parent is not self.root and dest_parent.type != "group":
            return False

        first_inserted_id: str | None = None
        for offset, entry in enumerate(entries):
            node = Node.make(name=entry.name, node_type=entry.item_type, target=entry.target)
            if first_inserted_id is None:
                first_inserted_id = node.id
            dest_parent.children.insert(dest_row + offset, node)


        self.persist()
        logging.info("Imported %d external drop entries", len(entries))
        return True

    def handle_tree_drop(self, source_proxy_index, target_proxy_index, indicator) -> bool:
        if self.search_box.text().strip():
            logging.info("Drag/drop disabled while search filter is active")
            return False
        if self.view_mode != "all":
            logging.info("Drag/drop disabled outside all view mode")
            return False
        return bool(self.safe_call(self._handle_tree_drop, source_proxy_index, target_proxy_index, indicator))

    def _handle_tree_drop(self, source_proxy_index, target_proxy_index, indicator) -> bool:
        source_index = self.map_to_source(source_proxy_index)
        target_index = self.map_to_source(target_proxy_index)

        if self._is_under_virtual_node(source_index):
            logging.info("Rejected drag/drop from virtual section")
            return False

        source_node = self._node_from_source_index(source_index)
        if source_node is None:
            return False

        if self._is_under_virtual_node(target_index):
            logging.info("Rejected drag/drop target in virtual section")
            return False

        dest_parent, dest_row = self._parent_node_and_row_for_drop(target_index, indicator)

        moved = move_node(
            root=self.root,
            source_id=source_node.id,
            destination_parent_id=dest_parent.id,
            destination_row=dest_row,
        )
        if not moved:
            logging.info("Rejected drag/drop move source=%s dest_parent=%s", source_node.id, dest_parent.id)
            return False


        self.persist()
        return True

    def launch_current(self):
        _, selected = self.current_item_and_node()
        node = self._resolve_real_node(selected)
        if self.can_launch_node(node):
            self.launch_node(node)

    def copy_current_target(self):
        _, selected = self.current_item_and_node()
        node = self._resolve_real_node(selected)
        if not self.can_launch_node(node):
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(node.target)

    def launch_node(self, node: Node):
        self._record_recent(node.id)
        if self.view_mode in {"all", "recent"}:
            self._refresh_tree_model()
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
        _, selected = self.current_item_and_node()
        node = self._resolve_real_node(selected)
        if node is None:
            return
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=node.name)
        if not ok or not name.strip():
            return
        node.name = name.strip()
        self._refresh_tree_model()
        self.persist()

    def delete_node(self):
        item, selected = self.current_item_and_node()
        node = self._resolve_real_node(selected)
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

        node_ref = find_node_ref(self.root, node.id)
        if node_ref is None or node_ref.parent is None:
            return
        node_ref.parent.children = [child for child in node_ref.parent.children if child.id != node.id]
        self._refresh_tree_model()
        self.persist()

    def persist(self):
        self.storage.save_tree(self.root)
