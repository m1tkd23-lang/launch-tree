"""JSON storage for launcher tree with backup support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import shutil

from .domain import Node, default_root


@dataclass
class JsonStorage:
    path: Path
    backup_keep_count: int = 50

    @property
    def backup_path(self) -> Path:
        return self.path.with_suffix(self.path.suffix + ".bak")

    @property
    def backup_dir(self) -> Path:
        return self.path.parent / "backup"

    @property
    def example_path(self) -> Path:
        return self.path.with_name("launcher.example.json")

    def _ensure_backup_dir(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _generation_backup_path(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return self.backup_dir / f"launcher_{stamp}.json"

    def _rotate_backups(self) -> None:
        files = sorted(self.backup_dir.glob("launcher_*.json"), key=lambda p: p.name, reverse=True)
        for stale in files[self.backup_keep_count :]:
            try:
                stale.unlink(missing_ok=True)
            except Exception:
                logging.warning("Failed deleting old backup: %s", stale, exc_info=True)

    def _write_json(self, path: Path, root: Node) -> None:
        serialized = json.dumps(root.to_dict(), ensure_ascii=False, indent=2)
        path.write_text(serialized + "\n", encoding="utf-8")

    def _read_json(self, path: Path) -> Node:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Node.from_dict(payload)

    def _recover_from_backup(self, reason: str) -> Node | None:
        if not self.backup_path.exists():
            return None
        shutil.copy2(self.backup_path, self.path)
        logging.info("Recovered launcher.json from .bak due to %s", reason)
        return self._read_json(self.path)

    def _bootstrap_from_example_if_missing(self) -> Node | None:
        if self.path.exists():
            return None
        if self.example_path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.example_path, self.path)
            logging.info("Initialized launcher.json from example: %s", self.example_path)
            return self._read_json(self.path)
        return None

    def load_tree(self) -> Node:
        try:
            bootstrapped = self._bootstrap_from_example_if_missing()
            if bootstrapped is not None:
                return bootstrapped

            if self.path.exists():
                node = self._read_json(self.path)
                logging.info("Loaded data from %s", self.path)
                return node

            recovered = self._recover_from_backup("missing launcher.json")
            if recovered is not None:
                return recovered
        except json.JSONDecodeError:
            logging.exception("Failed parsing %s", self.path)
            recovered = self._recover_from_backup("JSON decode error")
            if recovered is not None:
                return recovered
        except Exception:
            logging.exception("Failed loading launcher data")
            recovered = self._recover_from_backup("read error")
            if recovered is not None:
                return recovered

        logging.warning("Falling back to default empty root")
        root = default_root()
        self.save_tree(root)
        return root

    def save_tree(self, root: Node) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_backup_dir()

        if self.path.exists():
            try:
                shutil.copy2(self.path, self.backup_path)
                shutil.copy2(self.path, self._generation_backup_path())
            except Exception:
                logging.exception("Failed creating pre-save backups")

        self._write_json(self.path, root)

        # Ensure .bak exists even on first save.
        if not self.backup_path.exists():
            self._write_json(self.backup_path, root)

        self._rotate_backups()
        logging.info("Saved data to %s (bak: %s, generations: %s)", self.path, self.backup_path, self.backup_dir)
