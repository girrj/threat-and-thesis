#!/usr/bin/env python3
"""Collect uncurated security and AI research candidates into data/inbox.json."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "inbox.json"
USER_AGENT = "ThreatAndThesis/0.1 (+https://github.com/girrj/threat-and-thesis)"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


def tls_context() -> ssl.SSLContext:
    """Use certifi when available; otherwise rely on the operating system CA store."""
    try:
        import certifi  # type: ignore[import-not-found]

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


TLS_CONTEXT = tls_context()


def fetch(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json, application/atom+xml;q=0.9", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout, context=TLS_CONTEXT) as response:
        return response.read()


def fetch_json(url: str) -> dict[str, Any]:
    return json.loads(fetch(url).decode("utf-8"))


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def iso_date(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()


def collect_cisa(cutoff: datetime, limit: int) -> list[dict[str, Any]]:
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    payload = fetch_json(url)
    rows = []
    for item in payload.get("vulnerabilities", []):
        date_added = datetime.fromisoformat(item["dateAdded"]).replace(tzinfo=timezone.utc)
        if date_added < cutoff:
            continue
        cve = item["cveID"]
        rows.append(
            {
                "id": f"cisa-{cve.lower()}",
                "kind": "security",
                "title": f"{cve}: {clean_text(item.get('vulnerabilityName'))}",
                "originalTitle": clean_text(item.get("vulnerabilityName")),
                "source": "CISA Known Exploited Vulnerabilities",
                "sourceUrl": (
                    "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
                    f"?search_api_fulltext={urllib.parse.quote(cve)}"
                ),
                "publishedAt": item["dateAdded"],
                "summary": clean_text(item.get("shortDescription")),
                "action": clean_text(item.get("requiredAction")),
                "tags": ["CISA KEV", cve, clean_text(item.get("vendorProject"))],
                "priority": 98,
                "identifier": cve,
                "evidenceLevel": "official",
                "raw": {
                    "vendor": item.get("vendorProject"),
                    "product": item.get("product"),
                    "dueDate": item.get("dueDate"),
                    "knownRansomwareCampaignUse": item.get("knownRansomwareCampaignUse"),
                    "catalogUrl": url,
                },
            }
        )
    return sorted(rows, key=lambda row: row["publishedAt"], reverse=True)[:limit]


def cvss_metric(cve: dict[str, Any]) -> dict[str, Any]:
    metrics = cve.get("metrics", {})
    candidates = [
        metric
        for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30")
        for metric in metrics.get(key, [])
    ]
    return max(
        candidates,
        key=lambda metric: metric.get("cvssData", {}).get("baseScore", -1),
        default={},
    )


def english_description(cve: dict[str, Any]) -> str:
    descriptions = cve.get("descriptions", [])
    match = next((entry for entry in descriptions if entry.get("lang") == "en"), None)
    return clean_text((match or (descriptions[0] if descriptions else {})).get("value"))


def collect_nvd(cutoff: datetime, now: datetime, limit: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "pubStartDate": cutoff.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "pubEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "cvssV3Severity": "CRITICAL",
            "noRejected": "",
            "resultsPerPage": str(min(limit, 50)),
        }
    )
    endpoint = f"https://services.nvd.nist.gov/rest/json/cves/2.0?{params}"
    payload = fetch_json(endpoint)
    rows = []
    for wrapper in payload.get("vulnerabilities", []):
        cve = wrapper.get("cve", {})
        cve_id = cve.get("id")
        if not cve_id:
            continue
        metric = cvss_metric(cve)
        cvss = metric.get("cvssData", {})
        description = english_description(cve)
        rows.append(
            {
                "id": f"nvd-{cve_id.lower()}",
                "kind": "security",
                "title": f"{cve_id}: NVD 신규 Critical 취약점",
                "source": "NIST National Vulnerability Database",
                "sourceUrl": f"https://nvd.nist.gov/vuln/detail/{urllib.parse.quote(cve_id)}",
                "publishedAt": iso_date(cve["published"]),
                "summary": description,
                "tags": ["NVD", cve_id, "Critical"],
                "priority": 90,
                "severity": "critical",
                "identifier": cve_id,
                "evidenceLevel": "official",
                "raw": {
                    "lastModified": cve.get("lastModified"),
                    "cvssScore": cvss.get("baseScore"),
                    "cvssVector": cvss.get("vectorString"),
                    "sourceIdentifier": cve.get("sourceIdentifier"),
                },
            }
        )
    return sorted(rows, key=lambda row: row["publishedAt"], reverse=True)[:limit]


def collect_arxiv(cutoff: datetime, limit: int) -> list[dict[str, Any]]:
    topic_query = (
        'cat:cs.CR AND (all:"large language model" OR all:"AI agent" OR '
        'all:"prompt injection" OR all:"adversarial machine learning" OR '
        'all:"model poisoning" OR all:"privacy")'
    )
    params = urllib.parse.urlencode(
        {
            "search_query": topic_query,
            "start": 0,
            "max_results": max(limit * 2, 20),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    payload = fetch(f"https://export.arxiv.org/api/query?{params}")
    root = ET.fromstring(payload)
    rows = []
    for entry in root.findall("atom:entry", ARXIV_NS):
        published = clean_text(entry.findtext("atom:published", namespaces=ARXIV_NS))
        if not published:
            continue
        published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if published_dt < cutoff:
            continue
        entry_url = clean_text(entry.findtext("atom:id", namespaces=ARXIV_NS))
        arxiv_id = entry_url.rstrip("/").split("/")[-1].split("v")[0]
        title = clean_text(entry.findtext("atom:title", namespaces=ARXIV_NS))
        authors = [
            clean_text(author.findtext("atom:name", namespaces=ARXIV_NS))
            for author in entry.findall("atom:author", ARXIV_NS)
        ]
        categories = [node.attrib.get("term", "") for node in entry.findall("atom:category", ARXIV_NS)]
        rows.append(
            {
                "id": f"arxiv-{arxiv_id.replace('.', '-')}",
                "kind": "paper",
                "title": title,
                "originalTitle": title,
                "source": "arXiv",
                "sourceUrl": f"https://arxiv.org/abs/{urllib.parse.quote(arxiv_id)}",
                "publishedAt": published_dt.date().isoformat(),
                "summary": clean_text(entry.findtext("atom:summary", namespaces=ARXIV_NS)),
                "tags": ["arXiv", *categories[:3]],
                "priority": 60,
                "identifier": f"arXiv:{arxiv_id}",
                "evidenceLevel": "preprint",
                "raw": {"authors": authors, "categories": categories},
            }
        )
        if len(rows) >= limit:
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, help="lookback window (default: 14)")
    parser.add_argument("--max-per-source", type=int, default=15)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.days < 1 or args.max_per_source < 1:
        parser.error("--days and --max-per-source must be positive")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.days)
    candidates: list[dict[str, Any]] = []
    source_status: list[dict[str, Any]] = []

    collectors = (
        ("CISA KEV", lambda: collect_cisa(cutoff, args.max_per_source)),
        ("NIST NVD", lambda: collect_nvd(cutoff, now, args.max_per_source)),
        ("arXiv", lambda: collect_arxiv(cutoff, args.max_per_source)),
    )
    for name, collector in collectors:
        try:
            collected = collector()
            candidates.extend(collected)
            source_status.append({"source": name, "status": "ok", "count": len(collected)})
        except Exception as exc:  # keep other feeds usable when one upstream is unavailable
            source_status.append({"source": name, "status": "error", "error": str(exc)})

    deduplicated = {row["id"]: row for row in candidates}
    output = {
        "collectedAt": now.isoformat(timespec="seconds"),
        "lookbackDays": args.days,
        "notice": "Uncurated candidates. Verify every primary source before publishing.",
        "sources": source_status,
        "candidates": sorted(
            deduplicated.values(),
            key=lambda row: (row["publishedAt"], row["priority"]),
            reverse=True,
        ),
    }
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Collected {len(output['candidates'])} candidates -> {output_path}")
    for status in source_status:
        detail = status.get("count", status.get("error", "unknown"))
        print(f"- {status['source']}: {status['status']} ({detail})")
    return 0 if any(status["status"] == "ok" for status in source_status) else 1


if __name__ == "__main__":
    sys.exit(main())
