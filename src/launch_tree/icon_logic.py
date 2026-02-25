"""Pure icon selection helpers."""

from __future__ import annotations

from pathlib import PurePath

from .domain import Node


def icon_mode_for_node(node: Node) -> str:
    """Return icon mode used by UI icon resolver.

    - exe: path .exe (try real icon, fallback allowed)
    - path_optional: non-exe path (show only when real icon can be obtained)
    - none: no icon
    """

    if node.type == "path":
        target = (node.target or "").strip()
        if PurePath(target).suffix.lower() == ".exe":
            return "exe"
        return "path_optional"
    return "none"
