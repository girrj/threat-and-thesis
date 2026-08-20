#!/usr/bin/env python3
"""Build the static daily-edition index from immutable dated snapshots."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "content" / "daily"
OUTPUT = DAILY_DIR / "index.json"


def main() -> int:
    editions = []
    for path in sorted(DAILY_DIR.glob("????-??-??.json"), reverse=True):
        editions.append(json.loads(path.read_text(encoding="utf-8")))

    if not editions:
        raise SystemExit("No daily snapshots found in content/daily")

    payload = {
        "generatedAt": editions[0]["generatedAt"],
        "editions": editions,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(editions)} daily edition(s) -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
