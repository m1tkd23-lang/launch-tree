"""Validation and update logic for editing node details."""

from __future__ import annotations

from .domain import Node

ALLOWED_NODE_TYPES = {"group", "path", "url", "separator"}


def apply_node_update(
    node: Node,
    *,
    new_name: str | None = None,
    new_type: str | None = None,
    new_target: str | None = None,
) -> tuple[bool, str | None]:
    final_name = node.name if new_name is None else new_name.strip()
    final_type = node.type if new_type is None else new_type.strip()

    if not final_name:
        return False, "name cannot be empty"

    if final_type not in ALLOWED_NODE_TYPES:
        return False, f"unsupported type: {final_type}"

    if final_type != "group" and len(node.children) > 0:
        return False, "cannot change type: non-group node cannot keep children"

    if final_type in {"group", "separator"}:
        final_target = ""
    else:
        raw_target = node.target if new_target is None else new_target
        final_target = raw_target.strip()
        if not final_target:
            return False, "target is required for path/url"

    node.name = final_name
    node.type = final_type
    node.target = final_target
    return True, None
