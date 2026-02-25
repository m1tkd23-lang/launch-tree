"""Pure icon category selection logic."""

from __future__ import annotations

from pathlib import PurePath

from .domain import Node


def icon_category_for_node(node: Node) -> str:
    if node.type == "group":
        return "group"
    if node.type == "url":
        return "url"
    if node.type == "separator":
        return "separator"
    if node.type == "path":
        target = (node.target or "").strip()
        suffix = PurePath(target).suffix.lower()
        if suffix == ".exe":
            return "path_exe"
        looks_folder = target.endswith("/") or target.endswith("\\") or suffix == ""
        if looks_folder:
            return "path_folder"
        return "path_file"
    return "default"
