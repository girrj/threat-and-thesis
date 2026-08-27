import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate.py"
SPEC = importlib.util.spec_from_file_location("threat_and_thesis_validate", MODULE_PATH)
assert SPEC and SPEC.loader
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)


def ranking(item_id: str) -> dict[str, object]:
    return {
        "rank": 1,
        "itemId": item_id,
        "previousRank": None,
        "status": "new",
        "reason": "오늘 새로 확인된 자료다.",
    }


def edition(day: str, item_id: str, *, new_only: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "date": day,
        "generatedAt": f"{day}T12:00:00+09:00",
        "rankings": {
            "security": [ranking(item_id)],
            "ai-security": [],
            "security-paper": [],
            "ai-paper": [],
            "technology": [],
        },
    }
    if new_only:
        payload["selectionMode"] = "new-only"
    return payload


class DailyNewOnlyValidationTests(unittest.TestCase):
    def test_new_only_edition_rejects_an_item_seen_on_an_earlier_day(self):
        with tempfile.TemporaryDirectory() as directory:
            daily_dir = Path(directory)
            first = edition("2026-08-26", "old-item")
            second = edition("2026-08-27", "old-item", new_only=True)
            (daily_dir / "2026-08-26.json").write_text(json.dumps(first), encoding="utf-8")
            (daily_dir / "2026-08-27.json").write_text(json.dumps(second), encoding="utf-8")
            (daily_dir / "index.json").write_text(
                json.dumps({"generatedAt": second["generatedAt"], "editions": [second, first]}),
                encoding="utf-8",
            )
            errors: list[str] = []
            with patch.object(validate, "DAILY_DIR", daily_dir), patch.object(
                validate, "DAILY_INDEX", daily_dir / "index.json"
            ):
                validate.validate_daily(errors, {"old-item": "security"})

        self.assertTrue(any("new-only" in error and "old-item" in error for error in errors))

    def test_new_only_edition_allows_empty_categories_and_fresh_items(self):
        with tempfile.TemporaryDirectory() as directory:
            daily_dir = Path(directory)
            first = edition("2026-08-26", "old-item")
            second = edition("2026-08-27", "fresh-item", new_only=True)
            (daily_dir / "2026-08-26.json").write_text(json.dumps(first), encoding="utf-8")
            (daily_dir / "2026-08-27.json").write_text(json.dumps(second), encoding="utf-8")
            (daily_dir / "index.json").write_text(
                json.dumps({"generatedAt": second["generatedAt"], "editions": [second, first]}),
                encoding="utf-8",
            )
            errors: list[str] = []
            with patch.object(validate, "DAILY_DIR", daily_dir), patch.object(
                validate, "DAILY_INDEX", daily_dir / "index.json"
            ):
                validate.validate_daily(
                    errors,
                    {"old-item": "security", "fresh-item": "security"},
                )

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
