"""JSON storage for launcher tree with backup support."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path

from .domain import Node, default_root


@dataclass
class JsonStorage:
    path: Path

    @property
    def backup_path(self) -> Path:
        return self.path.with_suffix(self.path.suffix + ".bak")

    def load_tree(self) -> Node:
        for candidate in (self.path, self.backup_path):
            try:
                if candidate.exists():
                    payload = json.loads(candidate.read_text(encoding="utf-8"))
                    node = Node.from_dict(payload)
                    logging.info("Loaded data from %s", candidate)
                    return node
            except Exception:
                logging.exception("Failed loading %s", candidate)
        logging.warning("Falling back to default empty root")
        return default_root()

    def save_tree(self, root: Node) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(root.to_dict(), ensure_ascii=False, indent=2)
        self.path.write_text(serialized + "\n", encoding="utf-8")
        self.backup_path.write_text(serialized + "\n", encoding="utf-8")
        logging.info("Saved data to %s and %s", self.path, self.backup_path)
