from __future__ import annotations

import json

from launch_tree.storage_json import (
    load_user_state,
    save_user_state,
    set_user_state_path,
    update_recent,
)


def test_user_state_roundtrip(tmp_path):
    state_path = tmp_path / "user_state.json"
    set_user_state_path(state_path)

    original = {
        "favorites": {"n1": True},
        "recent": [{"id": "n1", "ts": 1730000100}],
        "ui": {"view_mode": "favorites"},
    }
    save_user_state(original)

    loaded = load_user_state()
    assert loaded == original


def test_recent_duplicate_promotes_to_front(tmp_path):
    set_user_state_path(tmp_path / "user_state.json")
    state = {
        "favorites": {},
        "recent": [
            {"id": "a", "ts": 10},
            {"id": "b", "ts": 9},
        ],
        "ui": {"view_mode": "all"},
    }

    updated = update_recent(state, "b", now=100)

    assert updated["recent"][0] == {"id": "b", "ts": 100}
    assert updated["recent"][1]["id"] == "a"
    assert [entry["id"] for entry in updated["recent"]].count("b") == 1


def test_recent_limit_to_20(tmp_path):
    set_user_state_path(tmp_path / "user_state.json")
    state = {"favorites": {}, "recent": [], "ui": {"view_mode": "all"}}

    for idx in range(25):
        state = update_recent(state, f"id-{idx}", now=idx)

    assert len(state["recent"]) == 20
    assert state["recent"][0]["id"] == "id-24"
    assert state["recent"][-1]["id"] == "id-5"


def test_view_mode_persist_restore(tmp_path):
    state_path = tmp_path / "user_state.json"
    set_user_state_path(state_path)

    save_user_state({"favorites": {}, "recent": [], "ui": {"view_mode": "recent"}})
    loaded = load_user_state()

    assert loaded["ui"]["view_mode"] == "recent"

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["ui"]["view_mode"] == "recent"
