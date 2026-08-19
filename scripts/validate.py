#!/usr/bin/env python3
"""Validate curated Threat & Thesis content before build or publication."""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "articles.json"
REQUIRED = {
    "id",
    "kind",
    "title",
    "source",
    "sourceUrl",
    "publishedAt",
    "summary",
    "whyItMatters",
    "details",
    "tags",
    "priority",
    "evidenceLevel",
}
KINDS = {"security", "ai-security", "paper", "technology"}
EVIDENCE = {"official", "peer-reviewed", "preprint", "industry"}
SEVERITIES = {"critical", "high", "medium", "info"}
DATE_LABELS = {"게시일", "수정일", "확인일", "기준일"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]*$")


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_url(value: object) -> bool:
    if not nonempty_string(value):
        return False
    parsed = urlparse(str(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main() -> int:
    errors: list[str] = []
    try:
        payload = json.loads(
            CONTENT.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: cannot read {CONTENT}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        errors.append("root must be an object")
        payload = {}
    generated_at = payload.get("generatedAt")
    try:
        generated_date = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00")).date()
    except ValueError:
        generated_date = date.today()
        errors.append("generatedAt must be an ISO 8601 timestamp")

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items must be a non-empty array")
        items = []

    ids: set[str] = set()
    urls: set[str] = set()
    for index, item in enumerate(items):
        label = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = sorted(REQUIRED - item.keys())
        if missing:
            errors.append(f"{label} missing: {', '.join(missing)}")
        item_id = item.get("id")
        if not nonempty_string(item_id) or not ID_PATTERN.fullmatch(str(item_id)):
            errors.append(f"{label}.id must use lowercase letters, numbers, dots, or hyphens")
        elif item_id in ids:
            errors.append(f"duplicate id: {item_id}")
        else:
            ids.add(str(item_id))
        if item.get("kind") not in KINDS:
            errors.append(f"{label}.kind must be one of {sorted(KINDS)}")
        if item.get("evidenceLevel") not in EVIDENCE:
            errors.append(f"{label}.evidenceLevel must be one of {sorted(EVIDENCE)}")
        if "severity" in item and item.get("severity") not in SEVERITIES:
            errors.append(f"{label}.severity must be one of {sorted(SEVERITIES)}")
        if "dateLabel" in item and item.get("dateLabel") not in DATE_LABELS:
            errors.append(f"{label}.dateLabel must be one of {sorted(DATE_LABELS)}")
        for key in ("title", "source", "summary", "whyItMatters"):
            if not nonempty_string(item.get(key)):
                errors.append(f"{label}.{key} must be a non-empty string")
        source_url = item.get("sourceUrl")
        if not valid_url(source_url):
            errors.append(f"{label}.sourceUrl must be an absolute http(s) URL")
        elif source_url in urls:
            errors.append(f"duplicate sourceUrl: {source_url}")
        else:
            urls.add(str(source_url))
        try:
            published = date.fromisoformat(str(item.get("publishedAt")))
            if published > generated_date:
                errors.append(f"{label}.publishedAt is later than generatedAt")
        except ValueError:
            errors.append(f"{label}.publishedAt must use YYYY-MM-DD")
        priority = item.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 100:
            errors.append(f"{label}.priority must be an integer from 0 to 100")
        for key in ("details", "tags"):
            values = item.get(key)
            if not isinstance(values, list) or not values or not all(nonempty_string(value) for value in values):
                errors.append(f"{label}.{key} must be a non-empty string array")
        limitations = item.get("limitations")
        if limitations is not None and (
            not isinstance(limitations, list) or not all(nonempty_string(value) for value in limitations)
        ):
            errors.append(f"{label}.limitations must be a string array")

    if errors:
        print(f"Content validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(items)} curated items in {CONTENT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
