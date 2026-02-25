"""Pure filtering logic independent of Qt."""

from __future__ import annotations

from .domain import Node


def node_matches_query(node: Node, query: str) -> bool:
    needle = query.strip().lower()
    if not needle:
        return True
    haystacks = [node.name, node.target, node.type]
    return any(needle in (text or "").lower() for text in haystacks)


def _collect_all_ids(node: Node, output: set[str]) -> None:
    output.add(node.id)
    for child in node.children:
        _collect_all_ids(child, output)


def compute_visible_node_ids(root: Node, query: str) -> set[str]:
    needle = query.strip().lower()
    if not needle:
        all_ids: set[str] = set()
        _collect_all_ids(root, all_ids)
        return all_ids

    visible_ids: set[str] = set()

    def walk(node: Node, force_visible_by_group_ancestor: bool = False) -> bool:
        matched_self = node_matches_query(node, needle)

        child_force_visible = force_visible_by_group_ancestor or (node.type == "group" and matched_self)

        child_visible_map: dict[str, bool] = {}
        for child in node.children:
            child_visible_map[child.id] = walk(child, child_force_visible)

        has_visible_non_separator_child = any(
            child_visible_map.get(child.id, False) and child.type != "separator" for child in node.children
        )

        visible = matched_self or force_visible_by_group_ancestor
        if node.type == "group":
            visible = visible or any(child_visible_map.values())
        elif node.type == "separator":
            visible = visible or has_visible_non_separator_child

        if visible:
            visible_ids.add(node.id)
        return visible

    walk(root)
    return visible_ids
