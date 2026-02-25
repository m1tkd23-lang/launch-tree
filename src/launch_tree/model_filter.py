"""Qt proxy model for tree search filtering."""

from __future__ import annotations

from PyQt6.QtCore import QSortFilterProxyModel

from .domain import Node
from .filter_logic import compute_visible_node_ids
from .model_qt import NODE_ROLE, VirtualNode


class TreeFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, root: Node):
        super().__init__()
        self.root = root
        self.query = ""
        self.visible_ids = compute_visible_node_ids(self.root, self.query)

    def set_query(self, query: str) -> None:
        self.query = query
        self.visible_ids = compute_visible_node_ids(self.root, self.query)
        self.invalidateFilter()

    def refresh_for_tree_change(self) -> None:
        """Recompute visible ids from the current tree after structural changes."""
        self.visible_ids = compute_visible_node_ids(self.root, self.query)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        if not index.isValid():
            return False
        node = index.data(NODE_ROLE)
        if isinstance(node, VirtualNode):
            if not self.query.strip():
                return True
            # 検索時は、仮想ノード名ヒット or 子が表示対象なら表示
            if self.query.strip().lower() in node.name.lower():
                return True
            for row in range(self.sourceModel().rowCount(index)):
                if self.filterAcceptsRow(row, index):
                    return True
            return False
        if not isinstance(node, Node):
            return False
        return node.id in self.visible_ids
