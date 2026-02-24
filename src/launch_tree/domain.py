"""Domain model for launcher tree nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class Node:
    """Tree node for groups/items."""

    id: str
    name: str
    type: str = "group"
    target: str = ""
    children: list["Node"] = field(default_factory=list)

    @staticmethod
    def make(name: str, node_type: str = "group", target: str = "") -> "Node":
        return Node(id=str(uuid.uuid4()), name=name, type=node_type, target=target)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "target": self.target,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        node_id = str(data.get("id") or uuid.uuid4())
        name = str(data.get("name") or "Unnamed")
        node_type = str(data.get("type") or "group")
        target = str(data.get("target") or "")
        children_raw = data.get("children") or []
        children = [cls.from_dict(child) for child in children_raw if isinstance(child, dict)]
        return cls(id=node_id, name=name, type=node_type, target=target, children=children)


@dataclass
class NodeRef:
    node: Node
    parent: Node | None
    index: int


def default_root() -> Node:
    return Node(id="root", name="Root", type="group", target="", children=[])


def find_node_ref(root: Node, node_id: str, parent: Node | None = None) -> NodeRef | None:
    if root.id == node_id:
        return NodeRef(node=root, parent=parent, index=-1)

    for idx, child in enumerate(root.children):
        if child.id == node_id:
            return NodeRef(node=child, parent=root, index=idx)
        found = find_node_ref(child, node_id, root)
        if found is not None:
            return found
    return None


def contains_node_id(node: Node, node_id: str) -> bool:
    if node.id == node_id:
        return True
    return any(contains_node_id(child, node_id) for child in node.children)


def resolve_insert_parent_and_row(root: Node, selected_id: str | None) -> tuple[Node, int]:
    if not selected_id:
        return root, len(root.children)

    selected_ref = find_node_ref(root, selected_id)
    if selected_ref is None:
        return root, len(root.children)

    selected = selected_ref.node
    if selected.type == "group":
        return selected, len(selected.children)

    if selected_ref.parent is None:
        return root, len(root.children)

    return selected_ref.parent, selected_ref.index + 1


def insert_relative_to_selection(root: Node, selected_id: str | None, new_node: Node) -> bool:
    parent, row = resolve_insert_parent_and_row(root, selected_id)
    if parent.type != "group":
        return False
    parent.children.insert(row, new_node)
    return True


def move_node(root: Node, source_id: str, destination_parent_id: str, destination_row: int) -> bool:
    """Move node safely. Returns False when move is rejected."""

    source_ref = find_node_ref(root, source_id)
    dest_ref = find_node_ref(root, destination_parent_id)
    if source_ref is None or dest_ref is None:
        return False

    source = source_ref.node
    dest_parent = dest_ref.node

    if source.id == root.id:
        return False
    if source.id == dest_parent.id:
        return False
    if contains_node_id(source, dest_parent.id):
        return False
    if dest_parent.type != "group":
        return False
    if source_ref.parent is None:
        return False

    src_parent = source_ref.parent
    src_index = source_ref.index

    node = src_parent.children.pop(src_index)

    if src_parent.id == dest_parent.id and destination_row > src_index:
        destination_row -= 1

    bounded_row = max(0, min(destination_row, len(dest_parent.children)))
    dest_parent.children.insert(bounded_row, node)
    return True
