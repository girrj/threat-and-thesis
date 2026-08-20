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
    @staticmethod
    def arxiv_feed(primary_category: str, categories: list[str] | None = None) -> bytes:
        category_nodes = "".join(
            f'<category term="{category}" scheme="http://arxiv.org/schemas/atom" />'
            for category in (categories or [primary_category])
        )
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom"
              xmlns:arxiv="http://arxiv.org/schemas/atom">
          <entry>
            <id>https://arxiv.org/abs/2608.19191v1</id>
            <title>Security without AI keywords</title>
            <summary>A systems security result.</summary>
            <published>2026-08-19T17:57:18Z</published>
            <arxiv:primary_category term="{primary_category}" />
            {category_nodes}
            <author><name>Example Author</name></author>
          </entry>
        </feed>""".encode()

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

    def test_arxiv_source_keeps_a_three_day_overlap(self):
        now = datetime(2026, 8, 20, 9, tzinfo=timezone.utc)
        state = {
            "sources": {
                "arXiv Security": {"lastSuccessfulAt": "2026-08-20T08:00:00+00:00"},
            }
        }

        cutoff = collect.source_cutoff(
            "arXiv Security",
            state,
            now,
            now - timedelta(hours=3),
            None,
            collect.ARXIV_MIN_LOOKBACK,
        )

        self.assertEqual(cutoff, now - timedelta(days=3))

    def test_arxiv_security_collects_non_ai_paper(self):
        with patch.object(collect, "fetch", return_value=self.arxiv_feed("cs.CR")) as mocked:
            rows = collect.collect_arxiv_security(
                datetime(2026, 8, 18, tzinfo=timezone.utc),
                10,
            )

        self.assertEqual(rows[0]["kind"], "security-paper")
        self.assertEqual(rows[0]["raw"]["primaryCategory"], "cs.CR")
        self.assertIn("search_query=cat%3Acs.CR", mocked.call_args.args[0])

    def test_arxiv_primary_category_keeps_ai_cross_listing_in_ai_lane(self):
        feed = self.arxiv_feed("cs.AI", ["cs.AI", "cs.CR"])
        with patch.object(collect, "fetch", return_value=feed):
            rows = collect.collect_arxiv_security(
                datetime(2026, 8, 18, tzinfo=timezone.utc),
                10,
            )

        self.assertEqual(rows[0]["kind"], "ai-paper")

    def test_arxiv_api_backfill_preserves_doi(self):
        feed = self.arxiv_feed("cs.CR").replace(
            b"</entry>",
            b"<arxiv:doi>10.1234/EXAMPLE</arxiv:doi></entry>",
        )
        with patch.object(collect, "fetch", return_value=feed):
            rows = collect.collect_arxiv_security(
                datetime(2026, 8, 18, tzinfo=timezone.utc),
                10,
            )

        self.assertEqual(rows[0]["raw"]["doi"], "10.1234/EXAMPLE")

    def test_arxiv_ai_uses_a_separate_query(self):
        with patch.object(collect, "fetch", return_value=self.arxiv_feed("cs.LG")) as mocked:
            rows = collect.collect_arxiv_ai(
                datetime(2026, 8, 18, tzinfo=timezone.utc),
                7,
            )

        self.assertEqual(rows[0]["kind"], "ai-paper")
        url = mocked.call_args.args[0]
        self.assertIn("cat%3Acs.AI", url)
        self.assertIn("max_results=100", url)

    def test_ai_focus_terms_accept_plural_and_hyphenated_forms(self):
        self.assertIsNotNone(collect.AI_FOCUS_TERMS.search("Large Language Models in practice"))
        self.assertIsNotNone(collect.AI_FOCUS_TERMS.search("A machine-learning benchmark"))

    def test_arxiv_recovery_pages_until_it_reaches_the_cutoff(self):
        def feed(arxiv_id: str, published: str) -> bytes:
            return f"""<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom"
                  xmlns:arxiv="http://arxiv.org/schemas/atom">
              <entry>
                <id>https://arxiv.org/abs/{arxiv_id}v1</id>
                <title>A network protocol security study {arxiv_id}</title>
                <summary>A systems security result.</summary>
                <published>{published}</published>
                <arxiv:primary_category term="cs.CR" />
                <category term="cs.CR" />
                <author><name>Example Author</name></author>
              </entry>
            </feed>""".encode()

        pages = [
            feed("2608.10001", "2026-08-20T10:00:00Z"),
            feed("2608.10002", "2026-08-20T09:00:00Z"),
            feed("2608.09999", "2026-08-17T09:00:00Z"),
        ]
        with (
            patch.object(collect, "ARXIV_PAGE_SIZE", 1),
            patch.object(collect, "fetch", side_effect=pages) as mocked,
            patch.object(collect.time, "sleep"),
        ):
            rows = collect.collect_arxiv_security(
                datetime(2026, 8, 18, tzinfo=timezone.utc),
                10,
            )

        self.assertEqual([row["id"] for row in rows], ["arxiv-2608-10001", "arxiv-2608-10002"])
        self.assertEqual(mocked.call_count, 3)

    def test_arxiv_daily_is_used_for_a_gap_under_24_hours(self):
        now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
        with patch.object(collect, "collect_arxiv_daily", return_value=[]) as daily:
            collect.collect_arxiv_current_or_recover(
                now - timedelta(hours=23, minutes=59),
                now,
                30,
            )

        daily.assert_called_once_with(30)

    def test_arxiv_gap_over_24_hours_recovers_at_least_three_days(self):
        now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
        with (
            patch.object(collect, "collect_arxiv_daily") as daily,
            patch.object(collect, "collect_arxiv_security", return_value=[]) as security,
            patch.object(collect, "collect_arxiv_ai", return_value=[]) as ai,
            patch.object(collect.time, "sleep"),
        ):
            collect.collect_arxiv_current_or_recover(
                now - timedelta(hours=24, minutes=1),
                now,
                30,
            )

        daily.assert_not_called()
        security.assert_called_once_with(now - timedelta(days=3), 30)
        ai.assert_called_once_with(now - timedelta(days=3), 30)

    def test_arxiv_daily_feed_uses_announcement_date_and_canonical_id(self):
        feed = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom"
              xmlns:arxiv="http://arxiv.org/schemas/atom"
              xmlns:dc="http://purl.org/dc/elements/1.1/">
          <updated>2026-08-20T04:00:09+00:00</updated>
          <entry>
            <id>oai:arXiv.org:2608.18187v1</id>
            <title>A TCP Protocol Security Study</title>
            <summary>arXiv:2608.18187v1 Announce Type: new Abstract: A network result.</summary>
            <published>2026-08-20T00:00:00-04:00</published>
            <link href="https://arxiv.org/abs/2608.18187" rel="alternate" />
            <category term="cs.CR" />
            <arxiv:announce_type>new</arxiv:announce_type>
            <dc:creator>Ada Lovelace, Alan Turing</dc:creator>
          </entry>
          <entry>
            <id>oai:arXiv.org:2608.11111v2</id>
            <title>A replacement</title>
            <summary>arXiv:2608.11111v2 Announce Type: replace Abstract: Updated.</summary>
            <published>2026-08-20T00:00:00-04:00</published>
            <category term="cs.CR" />
            <arxiv:announce_type>replace</arxiv:announce_type>
          </entry>
        </feed>"""

        with patch.object(collect, "fetch", return_value=feed):
            rows = collect.collect_arxiv_daily(30)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "arxiv-2608-18187")
        self.assertEqual(rows[0]["publishedAt"], "2026-08-20")
        self.assertEqual(rows[0]["kind"], "security-paper")
        self.assertEqual(rows[0]["summary"], "A network result.")

    def test_crossref_security_collects_recent_relevant_publication_records(self):
        payload = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1234/example",
                        "type": "proceedings-article",
                        "title": ["A Network Security Study"],
                        "abstract": "<jats:p>Measured intrusion detection behavior.</jats:p>",
                        "published-online": {"date-parts": [[2026, 8, 19]]},
                        "container-title": ["Example Security Symposium"],
                        "subject": ["Computer security"],
                        "author": [
                            {"given": "Ada", "family": "Lovelace"},
                            {"given": None, "family": "Turing"},
                        ],
                        "created": None,
                    },
                    {
                        "DOI": "10.1234/unrelated",
                        "type": "journal-article",
                        "title": ["Marine Biology"],
                        "published-online": {"date-parts": [[2026, 8, 19]]},
                    },
                ]
            }
        }

        with patch.object(collect, "fetch_json", return_value=payload):
            rows = collect.collect_crossref_security(
                datetime(2026, 8, 18, tzinfo=timezone.utc),
                datetime(2026, 8, 20, tzinfo=timezone.utc),
                10,
                "proceedings-article",
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "security-paper")
        self.assertEqual(rows[0]["summary"], "Measured intrusion detection behavior.")
        self.assertEqual(rows[0]["raw"]["authors"], ["Ada Lovelace", "Turing"])

    def test_crossref_filter_rejects_non_computing_security_and_vulnerability(self):
        self.assertFalse(
            collect.crossref_security_relevant(
                "Food Security and Rural Households",
                "A study of agricultural resilience.",
                ["Agriculture"],
                "Food Security",
            )
        )
        self.assertFalse(
            collect.crossref_security_relevant(
                "Exploiting Seasonal Variation in Crop Yield",
                "The model exploits rainfall patterns.",
                ["Agriculture"],
                "Field Studies",
            )
        )
        self.assertFalse(
            collect.crossref_security_relevant(
                "Fuzzy Clustering for Clinical Risk",
                "A fuzzy inference system for diagnosis.",
                ["Medicine"],
                "Clinical Computing",
            )
        )
        self.assertFalse(
            collect.crossref_security_relevant(
                "Maternal Vulnerability After Flooding",
                "A clinical cohort study.",
                ["Public health"],
                "Security and Safety",
            )
        )
        self.assertFalse(
            collect.crossref_security_relevant(
                "Dynamic trajectories of inflammatory biomarkers",
                "Machine learning may predict a patient's clinical vulnerability.",
                ["Neurology"],
                "Frontiers in Neurology",
            )
        )
        self.assertFalse(
            collect.crossref_security_relevant(
                "A neural network for predictive maintenance",
                "The model exploits temporal patterns in sensor data.",
                ["Artificial intelligence"],
                "Engineering Journal",
            )
        )

    def test_crossref_filter_keeps_explicit_cybersecurity_and_security_subjects(self):
        self.assertTrue(
            collect.crossref_security_relevant(
                "Cybersecurity for Food Supply Chains",
                "An analysis of software controls.",
                [],
                "Supply Chain Review",
            )
        )
        self.assertTrue(
            collect.crossref_security_relevant(
                "A Secure Key Exchange Protocol with Forward Secrecy",
                "We prove a protocol property.",
                [],
                "Distributed Systems",
            )
        )
        self.assertTrue(
            collect.crossref_security_relevant(
                "Generalizing AI-Based Software Vulnerability Detection",
                "We evaluate source-code models.",
                [],
                "Software Systems Journal",
            )
        )
        self.assertTrue(
            collect.crossref_security_relevant(
                "Automatic Exploit Generation",
                "We evaluate exploit generation against benchmark targets.",
                [],
                "Systems Journal",
            )
        )
        self.assertTrue(
            collect.crossref_security_relevant(
                "A Measurement Study",
                "",
                [],
                "2026 IEEE Symposium on Security and Privacy",
            )
        )
        self.assertTrue(
            collect.crossref_security_relevant(
                "A Measurement Study",
                "",
                [],
                "Proceedings of the 2026 ACM SIGSAC Conference on Computer and Communications Security",
            )
        )
        self.assertTrue(
            collect.crossref_security_relevant(
                "A Measurement Study",
                "We evaluate access control implementations.",
                ["Computer security"],
                "Systems Journal",
            )
        )

    def test_crossref_year_only_date_is_not_invented_as_january_first(self):
        published_at, precision = collect.crossref_date_info(
            {"published": {"date-parts": [[2026]]}}
        )

        self.assertIsNone(published_at)
        self.assertIsNone(precision)

    def test_crossref_month_only_date_is_not_invented_as_the_first_day(self):
        published_at, precision = collect.crossref_date_info(
            {"published": {"date-parts": [[2026, 8]]}}
        )

        self.assertIsNone(published_at)
        self.assertIsNone(precision)

    def test_crossref_generic_publication_date_takes_precedence_over_later_online_date(self):
        published_at, precision = collect.crossref_date_info(
            {
                "published": {"date-parts": [[2025, 1, 1]]},
                "published-online": {"date-parts": [[2026, 8, 20]]},
            }
        )

        self.assertEqual(published_at, "2025-01-01")
        self.assertEqual(precision, "day")
        self.assertFalse(
            collect.crossref_publication_is_recent(
                published_at,
                precision,
                datetime(2026, 8, 20, 9, tzinfo=timezone.utc),
                datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            )
        )

    def test_crossref_old_publication_is_not_a_daily_candidate(self):
        payload = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1234/old",
                        "title": ["A Cybersecurity Study"],
                        "published-online": {"date-parts": [[2025, 1, 1]]},
                    }
                ]
            }
        }
        with patch.object(collect, "fetch_json", return_value=payload):
            rows = collect.collect_crossref_security(
                datetime(2026, 8, 20, 9, tzinfo=timezone.utc),
                datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
                30,
                "journal-article",
            )

        self.assertEqual(rows, [])

    def test_crossref_reuses_the_same_stateful_cursor_until_a_short_page(self):
        def item(number: int):
            return {"DOI": f"10.1234/{number}", "title": [f"Cybersecurity Study {number}"]}

        pages = [
            {"message": {"items": [item(1), item(2)], "next-cursor": "TOKEN"}},
            {"message": {"items": [item(3), item(4)], "next-cursor": "TOKEN"}},
            {"message": {"items": [item(5)], "next-cursor": "TOKEN"}},
        ]
        with (
            patch.object(collect, "CROSSREF_PAGE_SIZE", 2),
            patch.object(collect, "fetch_json", side_effect=pages) as mocked,
        ):
            rows = collect.fetch_crossref_items(
                datetime(2026, 8, 20, 9, tzinfo=timezone.utc),
                datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
                "journal-article",
            )

        self.assertEqual([row["DOI"] for row in rows], [f"10.1234/{n}" for n in range(1, 6)])
        urls = [call.args[0] for call in mocked.call_args_list]
        self.assertIn("from-update-date%3A2026-08-20T09%3A00%3A00", urls[0])
        self.assertIn("from-pub-date%3A2026-08-13", urls[0])
        self.assertIn("until-pub-date%3A2026-08-20", urls[0])
        self.assertIn("sort=updated", urls[0])
        self.assertIn("cursor=%2A", urls[0])
        self.assertIn("cursor=TOKEN", urls[1])
        self.assertIn("cursor=TOKEN", urls[2])

    def test_crossref_repeated_page_splits_the_time_window(self):
        item = {
            "DOI": "10.1234/example",
            "type": "journal-article",
            "title": ["A Cybersecurity Study"],
            "published-online": {"date-parts": [[2026, 8, 20]]},
        }
        stalled = {"message": {"items": [item] * 2, "next-cursor": "TOKEN"}}
        complete = {"message": {"items": [item]}}

        def fake_fetch(url: str):
            full_window = (
                "from-update-date%3A2026-08-20T09%3A00%3A00" in url
                and "until-update-date%3A2026-08-20T12%3A00%3A00" in url
            )
            return stalled if full_window else complete

        with (
            patch.object(collect, "CROSSREF_PAGE_SIZE", 2),
            patch.object(collect, "fetch_json", side_effect=fake_fetch) as mocked,
        ):
            rows = collect.collect_crossref_security(
                datetime(2026, 8, 20, 9, tzinfo=timezone.utc),
                datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
                30,
                "journal-article",
            )

        self.assertEqual(mocked.call_count, 4)
        self.assertEqual(len(rows), 1)
        for call in mocked.call_args_list:
            self.assertIn("from-pub-date%3A2026-08-13", call.args[0])
            self.assertIn("until-pub-date%3A2026-08-20", call.args[0])

    def test_candidate_deduplication_keeps_one_cross_listed_arxiv_record(self):
        rows = [
            {"id": "arxiv-2608-19191", "kind": "security-paper"},
            {"id": "arxiv-2608-19191", "kind": "security-paper"},
        ]

        self.assertEqual(len(collect.deduplicate_candidates(rows, set())), 1)

    def test_candidate_deduplication_merges_arxiv_and_crossref_by_doi(self):
        rows = [
            {
                "id": "arxiv-2608-19191",
                "kind": "ai-paper",
                "title": "An AI Security Study",
                "sourceUrl": "https://arxiv.org/abs/2608.19191",
                "publishedAt": "2026-08-20",
                "summary": "Public preprint abstract.",
                "priority": 60,
                "identifier": "arXiv:2608.19191",
                "raw": {"doi": "10.1234/EXAMPLE", "authors": ["Ada Lovelace"]},
            },
            {
                "id": "doi-10-1234-example",
                "kind": "security-paper",
                "title": "An AI Security Study",
                "sourceUrl": "https://doi.org/10.1234/example",
                "publishedAt": "2026-08-20",
                "summary": "",
                "priority": 68,
                "identifier": "DOI:10.1234/example",
                "raw": {"authors": ["Ada Lovelace"]},
            },
        ]

        merged = collect.deduplicate_candidates(rows, set())

        self.assertEqual(list(merged), ["arxiv-2608-19191"])
        self.assertEqual(merged["arxiv-2608-19191"]["kind"], "ai-paper")
        self.assertEqual(merged["arxiv-2608-19191"]["summary"], "Public preprint abstract.")
        self.assertTrue(merged["arxiv-2608-19191"]["raw"]["needsEditorialReview"])
        self.assertEqual(len(merged["arxiv-2608-19191"]["raw"]["alternateSourceUrls"]), 2)

    def test_processed_member_excludes_the_entire_cross_source_group(self):
        rows = [
            {
                "id": "arxiv-2608-19191",
                "kind": "security-paper",
                "title": "A Security Study",
                "sourceUrl": "https://arxiv.org/abs/2608.19191",
                "publishedAt": "2026-08-20",
                "summary": "Public preprint abstract.",
                "priority": 60,
                "identifier": "arXiv:2608.19191",
                "raw": {"doi": "10.1234/example", "authors": ["Ada Lovelace"]},
            },
            {
                "id": "doi-10-1234-example",
                "kind": "security-paper",
                "title": "A Security Study",
                "sourceUrl": "https://doi.org/10.1234/example",
                "publishedAt": "2026-08-20",
                "summary": "",
                "priority": 68,
                "identifier": "DOI:10.1234/example",
                "raw": {"authors": ["Ada Lovelace"]},
            },
        ]

        self.assertEqual(
            collect.deduplicate_candidates(rows, {"doi-10-1234-example"}),
            {},
        )

    def test_cross_source_title_match_requires_the_same_first_author(self):
        base = {
            "kind": "security-paper",
            "title": "The Same Security Paper",
            "publishedAt": "2026-08-20",
            "summary": "Abstract",
            "priority": 60,
        }
        rows = [
            {
                **base,
                "id": "arxiv-2608-11111",
                "identifier": "arXiv:2608.11111",
                "sourceUrl": "https://arxiv.org/abs/2608.11111",
                "raw": {"authors": ["Ada Lovelace"]},
            },
            {
                **base,
                "id": "doi-10-1234-other",
                "identifier": "DOI:10.1234/other",
                "sourceUrl": "https://doi.org/10.1234/other",
                "raw": {"authors": ["Grace Hopper"]},
            },
        ]

        self.assertEqual(len(collect.deduplicate_candidates(rows, set())), 2)

    def test_cross_source_title_and_author_merge_without_a_known_doi_alias(self):
        rows = [
            {
                "id": "arxiv-2608-11111",
                "kind": "security-paper",
                "title": "The Same Security Paper",
                "sourceUrl": "https://arxiv.org/abs/2608.11111",
                "publishedAt": "2026-08-20",
                "summary": "Abstract",
                "priority": 60,
                "identifier": "arXiv:2608.11111",
                "raw": {"authors": ["Ada Lovelace"]},
            },
            {
                "id": "doi-10-1234-other",
                "kind": "security-paper",
                "title": "The Same Security Paper",
                "sourceUrl": "https://doi.org/10.1234/other",
                "publishedAt": "2026-08-20",
                "summary": "",
                "priority": 68,
                "identifier": "DOI:10.1234/other",
                "raw": {"authors": ["Ada Lovelace"]},
            },
        ]

        self.assertEqual(len(collect.deduplicate_candidates(rows, set())), 1)

    def test_curated_cross_source_title_blocks_duplicate_without_stored_authors(self):
        candidate = {
            "id": "doi-10-1234-published",
            "kind": "security-paper",
            "title": "A Published Security Paper",
            "originalTitle": "A Published Security Paper",
            "sourceUrl": "https://doi.org/10.1234/published",
            "publishedAt": "2026-08-20",
            "summary": "Abstract",
            "priority": 68,
            "identifier": "DOI:10.1234/published",
            "raw": {"authors": ["Ada Lovelace"]},
        }
        curated = {
            "id": "arxiv-2608-11111",
            "kind": "security-paper",
            "title": "게시된 보안 논문",
            "originalTitle": "A Published Security Paper",
            "sourceUrl": "https://arxiv.org/abs/2608.11111",
            "publishedAt": "2026-08-20",
            "identifier": "arXiv:2608.11111",
        }

        self.assertEqual(
            collect.deduplicate_candidates([candidate], set(), [curated]),
            {},
        )

    def test_legacy_paper_candidate_is_normalized(self):
        rows = [
            {
                "id": "arxiv-2608-17722",
                "kind": "paper",
                "title": "Data Auditing on Vision-Language Models",
                "summary": "A VLM data-poisoning method.",
                "raw": {"categories": ["cs.CR", "cs.LG"]},
            }
        ]

        normalized = collect.deduplicate_candidates(rows, set())["arxiv-2608-17722"]

        self.assertEqual(normalized["kind"], "ai-paper")

    def test_legacy_paper_with_non_object_raw_is_normalized(self):
        rows = [
            {
                "id": "arxiv-2608-17723",
                "kind": "paper",
                "title": "An AI benchmark",
                "summary": "A language model result.",
                "raw": None,
            }
        ]

        normalized = collect.deduplicate_candidates(rows, set())["arxiv-2608-17723"]

        self.assertEqual(normalized["kind"], "ai-paper")
        self.assertFalse(normalized["raw"]["needsEditorialReview"])

    def test_existing_crossref_ai_candidate_is_reclassified_for_review(self):
        rows = [
            {
                "id": "doi-10-1234-fedmarl",
                "kind": "security-paper",
                "title": "Deep Learning for Intrusion Detection",
                "summary": "A neural network benchmark.",
                "evidenceLevel": "publication-record",
                "publishedAt": "2026-08-20",
                "priority": 68,
            }
        ]

        normalized = collect.deduplicate_candidates(rows, set())["doi-10-1234-fedmarl"]

        self.assertEqual(normalized["kind"], "ai-paper")
        self.assertTrue(normalized["raw"]["needsEditorialReview"])

    def test_nvd_paginates_before_candidate_limiting(self):
        def wrapper(number: int):
            return {
                "cve": {
                    "id": f"CVE-2026-{number:05d}",
                    "published": "2026-08-20T10:00:00.000Z",
                    "descriptions": [{"lang": "en", "value": "Critical vulnerability"}],
                    "metrics": {},
                }
            }

        payloads = [
            {"totalResults": 3, "vulnerabilities": [wrapper(1), wrapper(2)]},
            {"totalResults": 3, "vulnerabilities": [wrapper(3)]},
        ]
        with (
            patch.object(collect, "NVD_PAGE_SIZE", 2),
            patch.object(collect, "fetch_json", side_effect=payloads) as mocked,
            patch.object(collect.time, "sleep"),
        ):
            rows = collect.collect_nvd(
                datetime(2026, 8, 20, 9, tzinfo=timezone.utc),
                datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
                None,
            )

        self.assertEqual(len(rows), 3)
        self.assertIn("startIndex=0", mocked.call_args_list[0].args[0])
        self.assertIn("startIndex=2", mocked.call_args_list[1].args[0])

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

    def test_persist_run_writes_inbox_before_advancing_state(self):
        output_path = Path("inbox.json")
        state_path = Path("state.json")
        with patch.object(collect, "write_json") as writer:
            collect.persist_run(output_path, {"candidates": []}, state_path, {"sources": {}})

        self.assertEqual(
            [call.args[0] for call in writer.call_args_list],
            [output_path, state_path],
        )

    def test_atomic_writer_preserves_existing_json_when_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text('{"old": true}\n', encoding="utf-8")
            with patch.object(collect.os, "replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    collect.write_json(path, {"old": False})

            self.assertEqual(path.read_text(encoding="utf-8"), '{"old": true}\n')
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_candidate_cap_is_applied_after_processed_items_are_removed(self):
        rows = [
            {
                "id": f"paper-{number}",
                "kind": "security-paper",
                "publishedAt": f"2026-08-{21 - number:02d}",
                "priority": 70 - number,
            }
            for number in range(1, 4)
        ]

        eligible = collect.deduplicate_candidates(rows, {"paper-1"})
        selected = collect.cap_candidates_by_kind(list(eligible.values()), 2)

        self.assertEqual([row["id"] for row in selected], ["paper-2", "paper-3"])

    def test_paper_source_outage_has_a_distinct_nonzero_exit_code(self):
        statuses = [
            {"source": "CISA KEV", "status": "ok"},
            {"source": "NIST NVD", "status": "ok"},
            {"source": "arXiv Daily", "status": "error"},
            {"source": "Crossref Journal Security", "status": "error"},
            {"source": "Crossref Proceedings Security", "status": "error"},
        ]

        self.assertEqual(collect.collection_exit_code(statuses), 2)


if __name__ == "__main__":
    unittest.main()
