"""JSON storage for launcher tree with backup support."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import time

from .domain import Node, default_root


USER_STATE_FILE = "user_state.json"
USER_STATE_PATH: Path | None = None
MAX_RECENT_ITEMS = 20


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


def set_user_state_path(path: Path) -> None:
    global USER_STATE_PATH
    USER_STATE_PATH = path


def _state_path() -> Path:
    if USER_STATE_PATH is None:
        return Path("data") / USER_STATE_FILE
    return USER_STATE_PATH


def _default_user_state() -> dict:
    return {
        "favorites": {},
        "recent": [],
        "ui": {"view_mode": "all"},
    }


def _normalize_user_state(payload: dict | None) -> dict:
    state = _default_user_state()
    if not isinstance(payload, dict):
        return state

    favorites_raw = payload.get("favorites")
    if isinstance(favorites_raw, dict):
        favorites: dict[str, bool] = {}
        for node_id, enabled in favorites_raw.items():
            if enabled:
                favorites[str(node_id)] = True
        state["favorites"] = favorites

    recent_raw = payload.get("recent")
    normalized_recent: list[dict[str, int | str]] = []
    if isinstance(recent_raw, list):
        for entry in recent_raw:
            if not isinstance(entry, dict):
                continue
            node_id = str(entry.get("id") or "").strip()
            if not node_id:
                continue
            try:
                ts = int(entry.get("ts"))
            except Exception:
                continue
            normalized_recent.append({"id": node_id, "ts": ts})
    normalized_recent.sort(key=lambda entry: int(entry["ts"]), reverse=True)
    deduped_recent: list[dict[str, int | str]] = []
    seen: set[str] = set()
    for entry in normalized_recent:
        node_id = str(entry["id"])
        if node_id in seen:
            continue
        deduped_recent.append(entry)
        seen.add(node_id)
        if len(deduped_recent) >= MAX_RECENT_ITEMS:
            break
    state["recent"] = deduped_recent

    ui_raw = payload.get("ui")
    if isinstance(ui_raw, dict):
        mode = str(ui_raw.get("view_mode") or "all")
        if mode in {"all", "favorites", "recent"}:
            state["ui"]["view_mode"] = mode
    return state


def load_user_state() -> dict:
    path = _state_path()
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return _normalize_user_state(payload)
    except Exception:
        logging.exception("Failed loading user state: %s", path)
    return _default_user_state()


def save_user_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_user_state(state)
    serialized = json.dumps(normalized, ensure_ascii=False, indent=2)
    path.write_text(serialized + "\n", encoding="utf-8")
    logging.info("Saved user state to %s", path)


def update_recent(state: dict, node_id: str, now: int | None = None) -> dict:
    normalized = _normalize_user_state(state)
    ts = int(time.time()) if now is None else int(now)
    recent = [entry for entry in normalized["recent"] if entry.get("id") != node_id]
    recent.insert(0, {"id": node_id, "ts": ts})
    normalized["recent"] = recent[:MAX_RECENT_ITEMS]
    return normalized
