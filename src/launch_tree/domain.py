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


def default_root() -> Node:
    return Node(id="root", name="Root", type="group", target="", children=[])
