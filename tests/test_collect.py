import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "collect.py"
SPEC = importlib.util.spec_from_file_location("threat_and_thesis_collect", MODULE_PATH)
assert SPEC and SPEC.loader
collect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collect)


class CollectorStateTests(unittest.TestCase):
    def test_source_cursor_uses_overlap(self):
        now = datetime(2026, 8, 20, 9, tzinfo=timezone.utc)
        state = {
            "sources": {
                "arXiv": {"lastSuccessfulAt": "2026-08-20T08:00:00+00:00"},
            }
        }

        cutoff = collect.source_cutoff(
            "arXiv",
            state,
            now,
            now - timedelta(hours=3),
            None,
        )

        self.assertEqual(cutoff, datetime(2026, 8, 20, 7, 50, tzinfo=timezone.utc))

    def test_source_cursor_catchup_is_capped_at_seven_days(self):
        now = datetime(2026, 8, 20, 9, tzinfo=timezone.utc)
        state = {
            "sources": {
                "arXiv": {"lastSuccessfulAt": "2026-08-01T00:00:00+00:00"},
            }
        }

        cutoff = collect.source_cutoff(
            "arXiv",
            state,
            now,
            now - timedelta(hours=3),
            None,
        )

        self.assertEqual(cutoff, now - timedelta(days=7))

    def test_cisa_keeps_same_day_records_with_date_only_precision(self):
        payload = {
            "vulnerabilities": [
                {
                    "dateAdded": "2026-08-20",
                    "cveID": "CVE-2026-12345",
                    "vulnerabilityName": "Example vulnerability",
                    "shortDescription": "Example description",
                    "requiredAction": "Apply the vendor update",
                    "vendorProject": "Example Vendor",
                    "product": "Example Product",
                    "dueDate": "2026-08-21",
                    "knownRansomwareCampaignUse": "Unknown",
                }
            ]
        }

        with patch.object(collect, "fetch_json", return_value=payload):
            rows = collect.collect_cisa(
                datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
                10,
            )

        self.assertEqual([row["identifier"] for row in rows], ["CVE-2026-12345"])

    def test_processed_ids_accepts_string_and_object_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "processed.json"
            path.write_text(
                json.dumps({"items": ["first", {"id": "second", "decision": "excluded"}]}),
                encoding="utf-8",
            )

            self.assertEqual(collect.processed_ids(path), {"first", "second"})


if __name__ == "__main__":
    unittest.main()
