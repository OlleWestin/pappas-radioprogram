#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]

BASE_PATH = REPO / "feed_base.xml"
FEED_PATH = REPO / "feed.xml"
STATE_PATH = REPO / "state.json"
EP_DIR = REPO / "episodes"

TZ = ZoneInfo("Europe/Stockholm")

RELEASE_WEEKDAY = 6  # Sunday (Mon=0 ... Sun=6)
RELEASE_TIME_LOCAL = time(2, 0)  # 02:00 local time

MARKER = "<!-- AUTO_EPISODES_INSERT_HERE -->"


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now_local() -> datetime:
    return datetime.now(tz=TZ)


def should_release(now: datetime) -> bool:
    return now.weekday() == RELEASE_WEEKDAY and now.time() >= RELEASE_TIME_LOCAL


def read_episode_xml(n: int) -> str:
    p = EP_DIR / f"{n:02d}.xml"
    if not p.exists():
        raise FileNotFoundError(f"Missing episode file: {p}")
    return p.read_text(encoding="utf-8").rstrip()  # keep indentation from file


def build_items_xml(upto_episode: int) -> str:
    # Concatenate episodes 1..upto_episode (inclusive)
    parts = []
    for n in range(1, upto_episode + 1):
        ep_path = EP_DIR / f"{n:02d}.xml"
        if not ep_path.exists():
            break
        parts.append(read_episode_xml(n))
    return ("\n\n".join(parts)).strip()


def build_feed(base_xml: str, items_xml: str) -> str:
    if MARKER not in base_xml:
        raise RuntimeError("Marker not found in feed_base.xml")
    insertion = (items_xml + "\n\n  " + MARKER) if items_xml else MARKER
    return base_xml.replace(MARKER, insertion)


def main() -> None:
    base = BASE_PATH.read_text(encoding="utf-8")

    state = load_state()
    next_ep = int(state.get("next_episode", 1))
    last_release = state.get("last_release_local_date", None)

    now = now_local()
    today = now.date().isoformat()

    # Determine how many episodes are already released (next_ep-1)
    released_upto = max(0, next_ep - 1)

    # Release exactly ONE episode per Sunday after 02:00 local time
    if should_release(now):
        if last_release != today:
            ep_file = EP_DIR / f"{next_ep:02d}.xml"
            if ep_file.exists():
                released_upto = next_ep  # include the new one
                state["next_episode"] = next_ep + 1
                state["last_release_local_date"] = today
                save_state(state)
        # else: already released today, do nothing

    items_xml = build_items_xml(released_upto)

    feed = build_feed(base, items_xml)
    FEED_PATH.write_text(feed, encoding="utf-8")


if __name__ == "__main__":
    main()
