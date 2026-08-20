#!/usr/bin/env python3
"""Validate curated articles and dated Threat & Thesis rankings before publication."""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "articles.json"
DAILY_DIR = ROOT / "content" / "daily"
DAILY_INDEX = DAILY_DIR / "index.json"
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
KINDS = {"security", "ai-security", "security-paper", "ai-paper", "technology"}
EVIDENCE = {"official", "peer-reviewed", "preprint", "industry"}
SEVERITIES = {"critical", "high", "medium", "info"}
DATE_LABELS = {"게시일", "수정일", "확인일", "기준일"}
RANKING_STATUSES = {"new", "up", "down", "same", "returning"}
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


def load_object(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(ROOT)} root must be an object")
        return {}
    return payload


def validate_articles(errors: list[str]) -> tuple[dict[str, str], int]:
    payload = load_object(CONTENT, errors)
    generated_at = payload.get("generatedAt")
    try:
        generated_date = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00")).date()
    except ValueError:
        generated_date = date.today()
        errors.append("articles.generatedAt must be an ISO 8601 timestamp")

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        errors.append("articles.items must be a non-empty array")
        items = []

    ids: set[str] = set()
    article_kinds: dict[str, str] = {}
    urls: set[str] = set()
    for index, item in enumerate(items):
        label = f"articles.items[{index}]"
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
            errors.append(f"duplicate article id: {item_id}")
        else:
            ids.add(str(item_id))
        if item.get("kind") not in KINDS:
            errors.append(f"{label}.kind must be one of {sorted(KINDS)}")
        elif isinstance(item_id, str):
            article_kinds[item_id] = str(item["kind"])
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
                errors.append(f"{label}.publishedAt is later than articles.generatedAt")
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
    return article_kinds, len(items)


def validate_daily(errors: list[str], article_kinds: dict[str, str]) -> int:
    paths = sorted(DAILY_DIR.glob("????-??-??.json"))
    if not paths:
        errors.append("content/daily must contain at least one YYYY-MM-DD.json snapshot")
        return 0

    editions: list[dict[str, Any]] = []
    prior_positions: dict[str, dict[str, int]] = {kind: {} for kind in KINDS}
    seen_ids: dict[str, set[str]] = {kind: set() for kind in KINDS}
    for path in paths:
        payload = load_object(path, errors)
        editions.append(payload)
        label = f"daily/{path.name}"
        edition_date = payload.get("date")
        if edition_date != path.stem:
            errors.append(f"{label}.date must match its filename")
        try:
            date.fromisoformat(str(edition_date))
        except ValueError:
            errors.append(f"{label}.date must use YYYY-MM-DD")
        try:
            generated_date = datetime.fromisoformat(
                str(payload.get("generatedAt")).replace("Z", "+00:00")
            ).date()
            if generated_date != date.fromisoformat(str(edition_date)):
                errors.append(f"{label}.generatedAt must fall on the edition date")
        except ValueError:
            errors.append(f"{label}.generatedAt must be an ISO 8601 timestamp")

        rankings_by_kind = payload.get("rankings")
        if not isinstance(rankings_by_kind, dict):
            errors.append(f"{label}.rankings must be an object grouped by category")
            rankings_by_kind = {}
        elif set(rankings_by_kind) != KINDS:
            errors.append(f"{label}.rankings must contain exactly {sorted(KINDS)}")

        all_current_ids: set[str] = set()
        edition_count = 0
        next_positions: dict[str, dict[str, int]] = {kind: {} for kind in KINDS}
        for kind in sorted(KINDS):
            rankings = rankings_by_kind.get(kind, [])
            kind_label = f"{label}.rankings.{kind}"
            if not isinstance(rankings, list):
                errors.append(f"{kind_label} must be an array")
                rankings = []
            elif len(rankings) > 10:
                errors.append(f"{kind_label} must contain at most 10 items")
            edition_count += len(rankings)

            ranks = [row.get("rank") for row in rankings if isinstance(row, dict)]
            if (
                any(isinstance(rank, bool) or not isinstance(rank, int) for rank in ranks)
                or ranks != list(range(1, len(rankings) + 1))
            ):
                errors.append(f"{kind_label} rank values must be sequential from 1")

            current_positions = next_positions[kind]
            for index, row in enumerate(rankings):
                row_label = f"{kind_label}[{index}]"
                if not isinstance(row, dict):
                    errors.append(f"{row_label} must be an object")
                    continue
                if set(row) != {"rank", "itemId", "previousRank", "status", "reason"}:
                    errors.append(
                        f"{row_label} must contain only rank, itemId, previousRank, status, reason"
                    )
                item_id = row.get("itemId")
                rank = row.get("rank")
                previous_rank = row.get("previousRank")
                status = row.get("status")
                if item_id not in article_kinds:
                    errors.append(f"{row_label}.itemId does not exist in articles.json: {item_id}")
                elif article_kinds[item_id] != kind:
                    errors.append(
                        f"{row_label}.itemId belongs to {article_kinds[item_id]}, not {kind}"
                    )
                if item_id in all_current_ids:
                    errors.append(f"{label} contains duplicate itemId: {item_id}")
                elif isinstance(item_id, str):
                    all_current_ids.add(item_id)
                if isinstance(item_id, str) and isinstance(rank, int) and not isinstance(rank, bool):
                    current_positions[item_id] = rank
                if status not in RANKING_STATUSES:
                    errors.append(f"{row_label}.status must be one of {sorted(RANKING_STATUSES)}")
                if previous_rank is not None and (
                    isinstance(previous_rank, bool)
                    or not isinstance(previous_rank, int)
                    or previous_rank < 1
                ):
                    errors.append(f"{row_label}.previousRank must be null or a positive integer")
                if not nonempty_string(row.get("reason")):
                    errors.append(f"{row_label}.reason must be a non-empty string")

                if isinstance(item_id, str) and isinstance(rank, int) and not isinstance(rank, bool):
                    actual_previous = prior_positions[kind].get(item_id)
                    if actual_previous is not None:
                        expected = (
                            "same"
                            if actual_previous == rank
                            else "up"
                            if actual_previous > rank
                            else "down"
                        )
                        if previous_rank != actual_previous or status != expected:
                            errors.append(
                                f"{row_label} must use previousRank {actual_previous} and status {expected}"
                            )
                    else:
                        expected = "returning" if item_id in seen_ids[kind] else "new"
                        if previous_rank is not None or status != expected:
                            errors.append(f"{row_label} must use previousRank null and status {expected}")

        if edition_count == 0:
            errors.append(f"{label}.rankings must contain at least one ranked item")
        for kind in KINDS:
            seen_ids[kind].update(next_positions[kind])
        prior_positions = next_positions

    index_payload = load_object(DAILY_INDEX, errors)
    expected_index = {
        "generatedAt": editions[-1].get("generatedAt"),
        "editions": list(reversed(editions)),
    }
    if index_payload != expected_index:
        errors.append("content/daily/index.json is stale; run scripts/build_daily_index.py")
    return len(editions)


def main() -> int:
    errors: list[str] = []
    article_kinds, article_count = validate_articles(errors)
    edition_count = validate_daily(errors, article_kinds)

    if errors:
        print(f"Content validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Validated {article_count} curated items and {edition_count} daily edition(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
