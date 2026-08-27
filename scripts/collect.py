#!/usr/bin/env python3
"""Incrementally collect uncurated security and AI research candidates."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import ssl
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "inbox.json"
DEFAULT_STATE = ROOT / "data" / "source-state.json"
DEFAULT_PROCESSED = ROOT / "data" / "processed.json"
ARTICLES = ROOT / "content" / "articles.json"
USER_AGENT = "ThreatAndThesis/0.2 (+https://github.com/girrj/threat-and-thesis)"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "dc": "http://purl.org/dc/elements/1.1/",
}
STATE_OVERLAP = timedelta(minutes=10)
MAX_STATE_LOOKBACK = timedelta(days=7)
ARXIV_MIN_LOOKBACK = timedelta(days=3)
ARXIV_DAILY_RECOVERY_AFTER = timedelta(hours=24)
ARXIV_PAGE_SIZE = 100
CROSSREF_PAGE_SIZE = 1000
CROSSREF_MAX_WINDOW_RESULTS = 20000
NVD_PAGE_SIZE = 2000
AI_ARXIV_CATEGORIES = {"cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO"}
ARXIV_DAILY_FEED = "https://rss.arxiv.org/atom/cs.CR+cs.AI+cs.LG+stat.ML+cs.CL+cs.CV+cs.RO"
ARXIV_ANNOUNCEMENT_TYPES = {"new", "cross"}
OFFICIAL_FEEDS = (
    ("Google Security Blog", "https://security.googleblog.com/feeds/posts/default", "security", "industry", 74),
    ("Google Project Zero", "https://projectzero.google/feed.xml", "security", "industry", 82),
    ("Cloudflare Security Blog", "https://blog.cloudflare.com/tag/security/rss/", "security", "industry", 74),
    ("GitHub Security Blog", "https://github.blog/security/feed/", "security", "industry", 74),
    ("IACR Cryptology ePrint Archive", "https://eprint.iacr.org/rss/rss.xml", "security-paper", "preprint", 64),
)
AI_FOCUS_TERMS = re.compile(
    r"\b(?:large language models?|language models?|LLMs?|VLMs?|AI agents?|agentic|model card|"
    r"prompt injection|jailbreak|adversarial machine learning|model poisoning|"
    r"machine[ -]learning|deep[ -]learning|neural networks?)\b",
    re.IGNORECASE,
)
SECURITY_SYSTEM_TERMS = re.compile(
    r"\b(?:fuzz\w*|vulnerabilit\w*|malware|ransomware|intrusion|network|protocol|"
    r"kernel|operating system|side[ -]channel|honeypot|cryptograph\w*|authentication|"
    r"access control|exploit\w*|software update|threat intelligence)\b",
    re.IGNORECASE,
)
SECURITY_TERMS = re.compile(
    r"\b(?:cybersecurity|cyber[ -]security|computer security|information security|"
    r"network security|software security|system security|cyberspace security|data security|"
    r"cloud security|cryptograph\w*|malware|ransomware|"
    r"phishing|intrusion|vulnerabilit\w*|side[ -]channel|access control|authentication|"
    r"secure computation|threat intelligence|exploit\w*)\b",
    re.IGNORECASE,
)
CROSSREF_STRONG_SECURITY_TERMS = re.compile(
    r"\b(?:cybersecurity|cyber[ -]security|computer security|information security|"
    r"network security|software security|system security|cloud security|cyberspace security|"
    r"malware|ransomware|phishing|intrusion (?:detection|prevention)|CVE-\d+|"
    r"fuzz(?:ing|er|ers)|side[ -]channel|cryptograph\w*|secure computation|"
    r"cryptographic protocol|security protocol|forward secrecy|"
    r"secure (?:communication|transport|key exchange)|"
    r"threat intelligence|memory corruption|zero[ -]trust)\b",
    re.IGNORECASE,
)
CROSSREF_WEAK_SECURITY_TERMS = re.compile(
    r"\b(?:security|authentication|access control|privacy|threat\w*)\b",
    re.IGNORECASE,
)
CROSSREF_TECHNICAL_VULNERABILITY_TERMS = re.compile(
    r"\b(?:(?:software|hardware|firmware|kernel|browser|network|web[ -]application|"
    r"cloud[ -]service|smart[ -]contract|source[ -]code|memory[ -]safety) vulnerabilit\w*|"
    r"vulnerabilit\w* (?:in|of|within) (?:software|hardware|firmware|kernels?|browsers?|"
    r"networks?|web[ -]applications?|cloud[ -]services?|smart[ -]contracts?|source[ -]code))\b",
    re.IGNORECASE,
)
CROSSREF_EXPLICIT_EXPLOIT_TERMS = re.compile(
    r"\b(?:exploit (?:generation|development)|weaponized exploit|zero[ -]day exploit|"
    r"(?:software|kernel|browser|network|remote|local|memory[ -]corruption) exploit\w*|"
    r"exploit\w* (?:a |the )?(?:software |memory[ -]corruption )?vulnerabilit\w*)\b",
    re.IGNORECASE,
)
CROSSREF_COMPUTING_TERMS = re.compile(
    r"\b(?:computer|computing|cyber|software|hardware|firmware|kernel|operating system|"
    r"network(?:ing| protocol| traffic| packet| attack)|internet|web|cloud|database|"
    r"source code|computer program\w*|software program\w*|programming|IoT|blockchain|"
    r"smart contract|machine learning|"
    r"language model|neural network|cryptograph\w*|malware)\b",
    re.IGNORECASE,
)
CROSSREF_SECURITY_VENUE_TERMS = re.compile(
    r"\b(?:computer security|information security|cybersecurity|cyber[ -]security|"
    r"network security|software security|cryptography|privacy)\b",
    re.IGNORECASE,
)
CROSSREF_SECURITY_VENUE_ALLOWLIST = re.compile(
    r"(?:IEEE Symposium on Security and Privacy|USENIX Security|"
    r"ACM (?:SIGSAC )?Conference on Computer and Communications Security|"
    r"Network and Distributed System Security|NDSS Symposium|"
    r"International Cryptology Conference|Annual International Conference on the Theory and "
    r"Applications of Cryptographic Techniques|CRYPTO \d{4}|EUROCRYPT \d{4})",
    re.IGNORECASE,
)


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


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value) if value is not None else "").strip()


def clean_markup(value: object) -> str:
    text = str(value) if value is not None else ""
    return clean_text(html.unescape(re.sub(r"<[^>]+>", " ", text)))


def normalize_doi(value: object) -> str | None:
    text = urllib.parse.unquote(clean_text(value)).casefold()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    match = re.search(r"10\.\d{4,9}/[^\s?#]+", text, re.IGNORECASE)
    if not match:
        return None
    return match.group(0).rstrip("/.,;:)]}\"")


def record_doi(row: dict[str, Any]) -> str | None:
    raw = row.get("raw")
    raw_doi = raw.get("doi") if isinstance(raw, dict) else None
    aliases = raw.get("identityAliases", []) if isinstance(raw, dict) else []
    urls = raw.get("alternateSourceUrls", []) if isinstance(raw, dict) else []
    values = [raw_doi, row.get("identifier"), row.get("sourceUrl")]
    if isinstance(aliases, list):
        values.extend(aliases)
    if isinstance(urls, list):
        values.extend(urls)
    for value in values:
        doi = normalize_doi(value)
        if doi:
            return doi
    return None


def normalize_arxiv_id(value: object) -> str | None:
    text = urllib.parse.unquote(clean_text(value))
    modern = re.search(r"(?:arxiv:|/abs/|/pdf/)?(\d{4}\.\d{4,5})(?:v\d+)?", text, re.IGNORECASE)
    if modern:
        return modern.group(1).casefold()
    legacy = re.search(
        r"(?:arxiv:|/abs/|/pdf/)?([a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?",
        text,
        re.IGNORECASE,
    )
    return legacy.group(1).casefold() if legacy else None


def record_arxiv_id(row: dict[str, Any]) -> str | None:
    raw = row.get("raw")
    aliases = raw.get("identityAliases", []) if isinstance(raw, dict) else []
    urls = raw.get("alternateSourceUrls", []) if isinstance(raw, dict) else []
    values = [row.get("identifier"), row.get("sourceUrl"), row.get("id")]
    if isinstance(aliases, list):
        values.extend(aliases)
    if isinstance(urls, list):
        values.extend(urls)
    for value in values:
        arxiv_id = normalize_arxiv_id(value)
        if arxiv_id:
            return arxiv_id
    return None


def normalize_url(value: object) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    parsed = urllib.parse.urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return None
    return urllib.parse.urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            urllib.parse.unquote(parsed.path).rstrip("/") or "/",
            parsed.query,
            "",
        )
    )


def normalize_title(value: object) -> str:
    text = unicodedata.normalize("NFKC", clean_markup(value)).casefold()
    return clean_text(re.sub(r"[^\w]+", " ", text, flags=re.UNICODE))


def record_title(row: dict[str, Any]) -> str:
    return normalize_title(row.get("originalTitle") or row.get("title"))


def record_first_author_surname(row: dict[str, Any]) -> str | None:
    raw = row.get("raw")
    authors = raw.get("authors") if isinstance(raw, dict) else None
    if not isinstance(authors, list) or not authors:
        return None
    author = normalize_title(authors[0])
    return author.split()[-1] if author else None


def record_year(row: dict[str, Any]) -> int | None:
    match = re.match(r"(\d{4})", clean_text(row.get("publishedAt")))
    return int(match.group(1)) if match else None


def record_identity_keys(row: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    row_id = clean_text(row.get("id"))
    if row_id:
        keys.update({row_id, f"id:{row_id.casefold()}"})
    doi = record_doi(row)
    if doi:
        keys.add(f"doi:{doi}")
    arxiv_id = record_arxiv_id(row)
    if arxiv_id:
        keys.add(f"arxiv:{arxiv_id}")
    url = normalize_url(row.get("sourceUrl"))
    if url:
        keys.add(f"url:{url}")
    raw = row.get("raw")
    if isinstance(raw, dict):
        aliases = raw.get("identityAliases")
        if isinstance(aliases, list):
            for alias in aliases:
                normalized_alias = clean_text(alias)
                if normalized_alias:
                    keys.update(
                        {normalized_alias, f"id:{normalized_alias.casefold()}"}
                    )
    return keys


def records_match(
    left: dict[str, Any],
    right: dict[str, Any],
    allow_missing_author: bool = False,
) -> bool:
    if record_identity_keys(left).intersection(record_identity_keys(right)):
        return True
    left_doi, right_doi = record_doi(left), record_doi(right)
    left_arxiv, right_arxiv = record_arxiv_id(left), record_arxiv_id(right)
    left_family = "doi" if left_doi else "arxiv" if left_arxiv else "other"
    right_family = "doi" if right_doi else "arxiv" if right_arxiv else "other"
    if {left_family, right_family} != {"arxiv", "doi"}:
        return False
    left_title, right_title = record_title(left), record_title(right)
    if not left_title or left_title != right_title:
        return False
    left_author = record_first_author_surname(left)
    right_author = record_first_author_surname(right)
    left_year, right_year = record_year(left), record_year(right)
    if left_year is None or right_year is None:
        return False
    if left_author and right_author:
        return left_author == right_author and abs(left_year - right_year) <= 1
    return allow_missing_author and left_year == right_year


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso_date(value: str) -> str:
    return parse_datetime(value).date().isoformat()


def take_limit(rows: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    return rows[:limit] if limit is not None else rows


def cap_candidates_by_kind(
    rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            clean_text(row.get("publishedAt")),
            int(row.get("priority", 0)),
        ),
        reverse=True,
    )
    counts: dict[str, int] = {}
    selected = []
    for row in ordered:
        kind = clean_text(row.get("kind")) or "unknown"
        if counts.get(kind, 0) >= limit:
            continue
        counts[kind] = counts.get(kind, 0) + 1
        selected.append(row)
    return selected


def feed_datetime(value: object) -> datetime:
    text = clean_text(value)
    try:
        parsed = parse_datetime(text)
    except ValueError:
        parsed = parsedate_to_datetime(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def collect_official_feed(
    cutoff: datetime,
    limit: int | None,
    *,
    source: str,
    url: str,
    kind: str,
    evidence_level: str,
    priority: int = 70,
) -> list[dict[str, Any]]:
    root = ET.fromstring(fetch(url))
    atom = "{http://www.w3.org/2005/Atom}"
    entries = root.findall(f"{atom}entry") or root.findall("./channel/item")
    rows: list[dict[str, Any]] = []
    for entry in entries:
        title = clean_markup(entry.findtext(f"{atom}title") or entry.findtext("title"))
        published_text = clean_text(
            entry.findtext(f"{atom}published")
            or entry.findtext(f"{atom}updated")
            or entry.findtext("pubDate")
            or entry.findtext("{http://purl.org/dc/elements/1.1/}date")
        )
        if not title or not published_text:
            continue
        published = feed_datetime(published_text)
        if published < cutoff:
            continue
        source_url = ""
        for link in entry.findall(f"{atom}link"):
            if link.attrib.get("rel", "alternate") == "alternate" and link.attrib.get("href"):
                source_url = clean_text(link.attrib["href"])
                break
        if not source_url:
            source_url = clean_text(entry.findtext("link"))
        if not source_url.startswith(("http://", "https://")):
            continue
        summary = clean_markup(
            entry.findtext(f"{atom}summary")
            or entry.findtext(f"{atom}content")
            or entry.findtext("description")
        )
        normalized_url = normalize_url(source_url) or source_url
        digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:16]
        rows.append(
            {
                "id": f"feed-{digest}",
                "kind": kind,
                "title": title,
                "originalTitle": title,
                "source": source,
                "sourceUrl": source_url,
                "publishedAt": published.date().isoformat(),
                "summary": summary,
                "tags": [source],
                "priority": priority,
                "evidenceLevel": evidence_level,
                "raw": {"feedUrl": url, "publishedTimestamp": published.isoformat()},
            }
        )
    return take_limit(
        sorted(rows, key=lambda row: row["raw"]["publishedTimestamp"], reverse=True),
        limit,
    )


def collect_cisa(cutoff: datetime, limit: int | None) -> list[dict[str, Any]]:
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    payload = fetch_json(url)
    rows = []
    for item in payload.get("vulnerabilities", []):
        date_added = datetime.fromisoformat(item["dateAdded"]).replace(tzinfo=timezone.utc)
        # KEV exposes only a calendar date, so comparing it to a three-hour timestamp
        # would incorrectly discard entries added earlier on the same day.
        if date_added.date() < cutoff.date():
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
    return take_limit(sorted(rows, key=lambda row: row["publishedAt"], reverse=True), limit)


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


def collect_nvd(
    cutoff: datetime,
    now: datetime,
    limit: int | None,
) -> list[dict[str, Any]]:
    vulnerabilities: list[dict[str, Any]] = []
    start_index = 0
    while True:
        params = urllib.parse.urlencode(
            {
                "pubStartDate": cutoff.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "pubEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "cvssV3Severity": "CRITICAL",
                "noRejected": "",
                "resultsPerPage": str(NVD_PAGE_SIZE),
                "startIndex": str(start_index),
            }
        )
        endpoint = f"https://services.nvd.nist.gov/rest/json/cves/2.0?{params}"
        payload = fetch_json(endpoint)
        page = payload.get("vulnerabilities", [])
        if not isinstance(page, list):
            raise RuntimeError("NVD response does not contain a vulnerabilities array")
        page_rows = [wrapper for wrapper in page if isinstance(wrapper, dict)]
        vulnerabilities.extend(page_rows)
        total_results = payload.get("totalResults")
        if len(page) < NVD_PAGE_SIZE:
            break
        start_index += len(page)
        if isinstance(total_results, int) and start_index >= total_results:
            break
        time.sleep(6)

    rows = []
    for wrapper in vulnerabilities:
        cve = wrapper.get("cve", {})
        cve_id = cve.get("id")
        if not cve_id:
            continue
        metric = cvss_metric(cve)
        cvss = metric.get("cvssData", {})
        rows.append(
            {
                "id": f"nvd-{cve_id.lower()}",
                "kind": "security",
                "title": f"{cve_id}: NVD 신규 Critical 취약점",
                "source": "NIST National Vulnerability Database",
                "sourceUrl": f"https://nvd.nist.gov/vuln/detail/{urllib.parse.quote(cve_id)}",
                "publishedAt": iso_date(cve["published"]),
                "summary": english_description(cve),
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
    return take_limit(sorted(rows, key=lambda row: row["publishedAt"], reverse=True), limit)


def arxiv_kind(primary_category: str, fallback: str) -> str:
    if primary_category == "cs.CR":
        return "security-paper"
    if primary_category in AI_ARXIV_CATEGORIES:
        return "ai-paper"
    return fallback


def collect_arxiv(
    cutoff: datetime,
    limit: int | None,
    topic_query: str,
    fallback_kind: str,
) -> list[dict[str, Any]]:
    rows = []
    start = 0
    while True:
        params = urllib.parse.urlencode(
            {
                "search_query": topic_query,
                "start": start,
                "max_results": ARXIV_PAGE_SIZE,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        root = ET.fromstring(fetch(f"https://export.arxiv.org/api/query?{params}"))
        entries = root.findall("atom:entry", ARXIV_NS)
        reached_cutoff = False
        for entry in entries:
            published = clean_text(entry.findtext("atom:published", namespaces=ARXIV_NS))
            if not published:
                continue
            published_dt = parse_datetime(published)
            if published_dt < cutoff:
                reached_cutoff = True
                break
            entry_url = clean_text(entry.findtext("atom:id", namespaces=ARXIV_NS))
            arxiv_id = re.sub(r"v\d+$", "", entry_url.rstrip("/").split("/")[-1])
            title = clean_text(entry.findtext("atom:title", namespaces=ARXIV_NS))
            authors = [
                clean_text(author.findtext("atom:name", namespaces=ARXIV_NS))
                for author in entry.findall("atom:author", ARXIV_NS)
            ]
            categories = [
                node.attrib.get("term", "")
                for node in entry.findall("atom:category", ARXIV_NS)
            ]
            primary_node = entry.find("arxiv:primary_category", ARXIV_NS)
            primary_category = (
                primary_node.attrib.get("term", "") if primary_node is not None else ""
            )
            doi = clean_text(entry.findtext("arxiv:doi", namespaces=ARXIV_NS))
            rows.append(
                {
                    "id": f"arxiv-{arxiv_id.replace('.', '-')}",
                    "kind": arxiv_kind(primary_category, fallback_kind),
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
                    "raw": {
                        "authors": authors,
                        "categories": categories,
                        "primaryCategory": primary_category,
                        "doi": doi or None,
                    },
                }
            )
        if reached_cutoff or len(entries) < ARXIV_PAGE_SIZE:
            break
        start += ARXIV_PAGE_SIZE
        time.sleep(3)
    unique_rows = {row["id"]: row for row in rows}
    return take_limit(
        sorted(
            unique_rows.values(),
            key=lambda row: row["publishedAt"],
            reverse=True,
        ),
        limit,
    )


def collect_arxiv_security(cutoff: datetime, limit: int | None) -> list[dict[str, Any]]:
    return collect_arxiv(cutoff, limit, "cat:cs.CR", "security-paper")


def collect_arxiv_ai(cutoff: datetime, limit: int | None) -> list[dict[str, Any]]:
    query = "(cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV OR cat:cs.RO)"
    return collect_arxiv(cutoff, limit, query, "ai-paper")


def arxiv_daily_kind(
    categories: list[str],
    title: str,
    summary: str,
) -> tuple[str | None, bool]:
    has_security = "cs.CR" in categories
    has_ai = bool(AI_ARXIV_CATEGORIES.intersection(categories) or "stat.ML" in categories)
    ai_focus = bool(AI_FOCUS_TERMS.search(f"{title} {summary}"))
    security_focus = bool(SECURITY_SYSTEM_TERMS.search(f"{title} {summary}"))
    needs_review = has_security and has_ai and ai_focus and security_focus
    if has_ai and ai_focus and not security_focus:
        return "ai-paper", needs_review
    if has_security:
        return "security-paper", needs_review
    if has_ai:
        return "ai-paper", needs_review
    return None, needs_review


def collect_arxiv_daily(limit: int | None) -> list[dict[str, Any]]:
    root = ET.fromstring(fetch(ARXIV_DAILY_FEED))
    feed_updated = clean_text(root.findtext("atom:updated", namespaces=ARXIV_NS))
    lanes: dict[str, list[dict[str, Any]]] = {"security-paper": [], "ai-paper": []}
    entries = root.findall("atom:entry", ARXIV_NS)
    if len(entries) >= 1900:
        raise RuntimeError("arXiv combined feed is near its 2,000-entry limit; split the category feed")
    for entry in entries:
        announce_type = clean_text(
            entry.findtext("arxiv:announce_type", namespaces=ARXIV_NS)
        )
        if announce_type not in ARXIV_ANNOUNCEMENT_TYPES:
            continue
        entry_id = clean_text(entry.findtext("atom:id", namespaces=ARXIV_NS))
        arxiv_id = re.sub(r"v\d+$", "", entry_id.rsplit(":", 1)[-1].rsplit("/", 1)[-1])
        if not arxiv_id:
            continue
        title = clean_text(entry.findtext("atom:title", namespaces=ARXIV_NS))
        raw_summary = clean_text(entry.findtext("atom:summary", namespaces=ARXIV_NS))
        summary = re.sub(
            r"^arXiv:\S+\s+Announce Type:\s*\S+\s+Abstract:\s*",
            "",
            raw_summary,
            flags=re.IGNORECASE,
        )
        categories = [node.attrib.get("term", "") for node in entry.findall("atom:category", ARXIV_NS)]
        kind, needs_review = arxiv_daily_kind(categories, title, summary)
        if kind is None:
            continue
        published = clean_text(entry.findtext("atom:published", namespaces=ARXIV_NS))
        if not published:
            continue
        alternate = next(
            (
                node.attrib.get("href", "")
                for node in entry.findall("atom:link", ARXIV_NS)
                if node.attrib.get("rel") == "alternate"
            ),
            f"https://arxiv.org/abs/{arxiv_id}",
        )
        creators = clean_text(entry.findtext("dc:creator", namespaces=ARXIV_NS))
        doi = clean_text(entry.findtext("arxiv:DOI", namespaces=ARXIV_NS))
        score = 60 + (4 if announce_type == "new" else 0)
        if kind == "security-paper" and SECURITY_SYSTEM_TERMS.search(title):
            score += 4
        if kind == "ai-paper" and AI_FOCUS_TERMS.search(title):
            score += 4
        lanes[kind].append(
            {
                "id": f"arxiv-{arxiv_id.replace('.', '-')}",
                "kind": kind,
                "title": title,
                "originalTitle": title,
                "source": "arXiv",
                "sourceUrl": alternate,
                "publishedAt": iso_date(published),
                "summary": summary,
                "tags": ["arXiv", *categories[:3]],
                "priority": score,
                "identifier": f"arXiv:{arxiv_id}",
                "evidenceLevel": "preprint",
                "raw": {
                    "authors": [name for name in creators.split(", ") if name],
                    "categories": categories,
                    "announceType": announce_type,
                    "feedUpdated": feed_updated,
                    "doi": doi or None,
                    "rights": clean_text(entry.findtext("dc:rights", namespaces=ARXIV_NS)),
                    "needsEditorialReview": needs_review,
                },
            }
        )
    security_rows = sorted(lanes["security-paper"], key=lambda row: row["priority"], reverse=True)
    ai_rows = sorted(lanes["ai-paper"], key=lambda row: row["priority"], reverse=True)
    return [*take_limit(security_rows, limit), *take_limit(ai_rows, limit)]


def collect_arxiv_current_or_recover(
    cutoff: datetime,
    now: datetime,
    limit: int | None,
) -> list[dict[str, Any]]:
    if now - cutoff < ARXIV_DAILY_RECOVERY_AFTER:
        return collect_arxiv_daily(limit)
    recovery_cutoff = max(
        min(cutoff, now - ARXIV_MIN_LOOKBACK),
        now - MAX_STATE_LOOKBACK,
    )
    security_rows = collect_arxiv_security(recovery_cutoff, limit)
    time.sleep(3)
    return [*security_rows, *collect_arxiv_ai(recovery_cutoff, limit)]


def crossref_date_info(item: dict[str, Any]) -> tuple[str | None, str | None]:
    keys = (
        ("published",)
        if "published" in item
        else ("published-online", "published-print", "issued")
    )
    for key in keys:
        date_value = item.get(key)
        if not isinstance(date_value, dict):
            continue
        date_parts = date_value.get("date-parts", [])
        if not date_parts or not isinstance(date_parts[0], list):
            continue
        parts = date_parts[0]
        if len(parts) < 3:
            continue
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            value = datetime(year, month, day, tzinfo=timezone.utc).date().isoformat()
            return value, "day"
        except (TypeError, ValueError):
            continue
    return None, None


def crossref_date(item: dict[str, Any]) -> str | None:
    return crossref_date_info(item)[0]


def crossref_publication_is_recent(
    published_at: str,
    precision: str,
    cutoff: datetime,
    now: datetime,
) -> bool:
    published = datetime.fromisoformat(published_at).date()
    earliest = cutoff.date() - timedelta(days=7)
    latest = now.date()
    if precision == "day":
        return earliest <= published <= latest
    return False


def crossref_security_relevant(
    title: str,
    abstract: str,
    subjects: list[str],
    container: str,
) -> bool:
    body = " ".join([title, abstract, *subjects])
    if CROSSREF_SECURITY_VENUE_ALLOWLIST.search(container):
        return True
    if CROSSREF_STRONG_SECURITY_TERMS.search(body):
        return True
    if CROSSREF_EXPLICIT_EXPLOIT_TERMS.search(body):
        return True
    if CROSSREF_TECHNICAL_VULNERABILITY_TERMS.search(body):
        return True
    has_weak_signal = bool(CROSSREF_WEAK_SECURITY_TERMS.search(body))
    has_computing_context = bool(CROSSREF_COMPUTING_TERMS.search(body))
    venue_is_specific = bool(CROSSREF_SECURITY_VENUE_TERMS.search(container))
    return has_weak_signal and (has_computing_context or venue_is_specific)


def crossref_page_key(item: dict[str, Any]) -> str:
    doi = clean_text(item.get("DOI"))
    titles = item.get("title")
    title = clean_markup(titles[0]) if isinstance(titles, list) and titles else ""
    created = item.get("created")
    created_at = clean_text(created.get("date-time")) if isinstance(created, dict) else ""
    return doi or f"{title}|{created_at}"


def fetch_crossref_items(
    cutoff: datetime,
    now: datetime,
    work_type: str,
    split_depth: int = 0,
    publication_window: tuple[str, str] | None = None,
) -> list[dict[str, Any]]:
    if work_type not in {"journal-article", "proceedings-article"}:
        raise ValueError(f"unsupported Crossref type: {work_type}")
    cutoff = cutoff.replace(microsecond=0)
    now = now.replace(microsecond=0)
    if publication_window is None:
        publication_window = (
            (cutoff.date() - timedelta(days=7)).isoformat(),
            now.date().isoformat(),
        )
    publication_floor, publication_ceiling = publication_window
    cursor = "*"
    items: list[dict[str, Any]] = []
    page_fingerprints: set[tuple[str, ...]] = set()
    while True:
        params = urllib.parse.urlencode(
            {
                "filter": (
                    f"from-update-date:{cutoff.strftime('%Y-%m-%dT%H:%M:%S')},"
                    f"until-update-date:{now.strftime('%Y-%m-%dT%H:%M:%S')},"
                    f"from-pub-date:{publication_floor},"
                    f"until-pub-date:{publication_ceiling},"
                    f"type:{work_type}"
                ),
                "cursor": cursor,
                "rows": CROSSREF_PAGE_SIZE,
                "sort": "updated",
                "order": "asc",
                "mailto": "girrj@users.noreply.github.com",
            }
        )
        payload = fetch_json(f"https://api.crossref.org/works?{params}")
        message = payload.get("message", {})
        page = message.get("items", []) if isinstance(message, dict) else []
        if not isinstance(page, list):
            raise RuntimeError("Crossref response does not contain an items array")
        total_results = message.get("total-results") if isinstance(message, dict) else None
        if (
            cursor == "*"
            and isinstance(total_results, int)
            and total_results > CROSSREF_MAX_WINDOW_RESULTS
        ):
            span = now - cutoff
            midpoint = (cutoff + span / 2).replace(microsecond=0)
            if split_depth >= 20 or midpoint <= cutoff or midpoint >= now:
                raise RuntimeError("Crossref result window is too large to split safely")
            return [
                *fetch_crossref_items(
                    cutoff,
                    midpoint,
                    work_type,
                    split_depth + 1,
                    publication_window,
                ),
                *fetch_crossref_items(
                    midpoint,
                    now,
                    work_type,
                    split_depth + 1,
                    publication_window,
                ),
            ]
        page_items = [item for item in page if isinstance(item, dict)]
        fingerprint = tuple(crossref_page_key(item) for item in page_items)
        if page and fingerprint in page_fingerprints:
            span = now - cutoff
            midpoint = (cutoff + span / 2).replace(microsecond=0)
            if split_depth >= 20 or midpoint <= cutoff or midpoint >= now:
                raise RuntimeError("Crossref repeated a page inside an unsplittable time window")
            return [
                *fetch_crossref_items(
                    cutoff,
                    midpoint,
                    work_type,
                    split_depth + 1,
                    publication_window,
                ),
                *fetch_crossref_items(
                    midpoint,
                    now,
                    work_type,
                    split_depth + 1,
                    publication_window,
                ),
            ]
        page_fingerprints.add(fingerprint)
        items.extend(page_items)
        if len(page) < CROSSREF_PAGE_SIZE:
            break
        next_cursor = message.get("next-cursor")
        if not isinstance(next_cursor, str) or not next_cursor:
            raise RuntimeError("Crossref pagination ended without a usable next cursor")
        cursor = next_cursor
    return items


def collect_crossref_security(
    cutoff: datetime,
    now: datetime,
    limit: int | None,
    work_type: str,
) -> list[dict[str, Any]]:
    items = fetch_crossref_items(cutoff, now, work_type)

    rows = []
    for item in items:
        doi = clean_text(item.get("DOI"))
        titles = item.get("title", [])
        title = clean_markup(titles[0] if isinstance(titles, list) and titles else "")
        published_at, date_precision = crossref_date_info(item)
        if not doi or not title or not published_at:
            continue
        if not date_precision or not crossref_publication_is_recent(
            published_at,
            date_precision,
            cutoff,
            now,
        ):
            continue
        subjects = item.get("subject", [])
        containers = item.get("container-title", [])
        abstract = clean_markup(item.get("abstract"))
        container = clean_markup(containers[0]) if isinstance(containers, list) and containers else ""
        clean_subjects = (
            [clean_markup(value) for value in subjects if clean_markup(value)]
            if isinstance(subjects, list)
            else []
        )
        if not crossref_security_relevant(title, abstract, clean_subjects, container):
            continue
        ai_focus = bool(AI_FOCUS_TERMS.search(f"{title} {abstract}"))
        authors = []
        for author in item.get("author", []):
            if not isinstance(author, dict):
                continue
            name = clean_text(
                f"{clean_text(author.get('given'))} {clean_text(author.get('family'))}"
            )
            if name:
                authors.append(name)
        created = item.get("created")
        created_at = clean_text(created.get("date-time")) if isinstance(created, dict) else ""
        rows.append(
            {
                "id": f"doi-{re.sub(r'[^a-z0-9]+', '-', doi.lower()).strip('-')}",
                "kind": "ai-paper" if ai_focus else "security-paper",
                "title": title,
                "originalTitle": title,
                "source": container or clean_text(item.get("publisher")) or "Crossref",
                "sourceUrl": f"https://doi.org/{urllib.parse.quote(doi, safe='/')}",
                "publishedAt": published_at,
                "summary": abstract,
                "tags": [
                    "Crossref",
                    *clean_subjects[:2],
                ],
                "priority": 68,
                "identifier": f"DOI:{doi}",
                "evidenceLevel": "publication-record",
                "raw": {
                    "authors": authors,
                    "containerTitle": container,
                    "subjects": clean_subjects,
                    "publisher": item.get("publisher"),
                    "type": item.get("type"),
                    "createdAt": created_at,
                    "publicationDatePrecision": date_precision,
                    "license": item.get("license", []),
                    "links": item.get("link", []),
                    "needsEditorialReview": ai_focus,
                    "reviewStatus": "Verify on the publisher or conference page before curation.",
                },
            }
        )
    unique_rows = {row["id"]: row for row in rows}
    return take_limit(
        sorted(
            unique_rows.values(),
            key=lambda row: (row["publishedAt"], bool(row["summary"])),
            reverse=True,
        ),
        limit,
    )


def processed_ids(path: Path) -> set[str]:
    return {
        row["id"]
        for row in processed_records(path)
        if isinstance(row.get("id"), str)
    }


def processed_records(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path, {"items": []})
    values = payload.get("items", [])
    if not isinstance(values, list):
        return []
    return [
        {"id": value} if isinstance(value, str) else value
        for value in values
        if isinstance(value, (str, dict))
    ]


def curated_ids() -> set[str]:
    return {
        item["id"]
        for item in curated_records()
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def curated_records() -> list[dict[str, Any]]:
    payload = load_json(ARTICLES, {"items": []})
    values = payload.get("items", [])
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def pending_candidate_is_relevant(row: dict[str, Any]) -> bool:
    if row.get("evidenceLevel") != "publication-record":
        return True
    raw = row.get("raw")
    raw = raw if isinstance(raw, dict) else {}
    subjects = raw.get("subjects")
    clean_subjects = (
        [clean_markup(value) for value in subjects if clean_markup(value)]
        if isinstance(subjects, list)
        else [clean_markup(value) for value in row.get("tags", [])[1:]]
        if isinstance(row.get("tags"), list)
        else []
    )
    return crossref_security_relevant(
        clean_markup(row.get("originalTitle") or row.get("title")),
        clean_markup(row.get("summary")),
        clean_subjects,
        clean_markup(raw.get("containerTitle")),
    )


def merge_candidates(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    if not clean_text(merged.get("summary")) and clean_text(incoming.get("summary")):
        merged["summary"] = incoming["summary"]
    merged["priority"] = max(
        int(existing.get("priority", 0)),
        int(incoming.get("priority", 0)),
    )

    existing_raw = existing.get("raw")
    incoming_raw = incoming.get("raw")
    raw = dict(existing_raw) if isinstance(existing_raw, dict) else {}
    if isinstance(incoming_raw, dict):
        for key, value in incoming_raw.items():
            if key not in raw or raw[key] in (None, "", []):
                raw[key] = value

    aliases = {
        clean_text(value)
        for value in (
            existing.get("identifier"),
            incoming.get("identifier"),
            existing.get("id"),
            incoming.get("id"),
            *(raw.get("identityAliases", []) if isinstance(raw.get("identityAliases"), list) else []),
        )
        if clean_text(value)
    }
    urls = {
        clean_text(value)
        for value in (
            existing.get("sourceUrl"),
            incoming.get("sourceUrl"),
            *(
                raw.get("alternateSourceUrls", [])
                if isinstance(raw.get("alternateSourceUrls"), list)
                else []
            ),
        )
        if clean_text(value)
    }
    raw["identityAliases"] = sorted(aliases)
    raw["alternateSourceUrls"] = sorted(urls)
    doi = record_doi(existing) or record_doi(incoming)
    if doi:
        raw["doi"] = doi

    existing_kind = clean_text(existing.get("kind"))
    incoming_kind = clean_text(incoming.get("kind"))
    if existing_kind != incoming_kind and existing_kind.endswith("paper") and incoming_kind.endswith("paper"):
        if "ai-paper" in {existing_kind, incoming_kind}:
            merged["kind"] = "ai-paper"
        raw["needsEditorialReview"] = True
    merged["raw"] = raw
    return merged


def deduplicate_candidates(
    rows: list[dict[str, Any]],
    excluded: set[str],
    excluded_records: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    deduplicated: dict[str, dict[str, Any]] = {}
    blocked_records = excluded_records or []
    for row in rows:
        row_id = row.get("id")
        if not isinstance(row_id, str):
            continue
        normalized = row
        if row.get("kind") == "paper":
            raw_value = row.get("raw")
            raw = raw_value if isinstance(raw_value, dict) else {}
            categories = raw.get("categories", [])
            if not isinstance(categories, list):
                categories = []
            suggested_kind, needs_review = arxiv_daily_kind(
                [str(category) for category in categories],
                clean_text(row.get("title")),
                clean_text(row.get("summary")),
            )
            normalized = {**row, "kind": suggested_kind or "ai-paper"}
            raw = dict(raw)
            raw["needsEditorialReview"] = needs_review
            normalized["raw"] = raw
        elif row.get("evidenceLevel") == "publication-record" and AI_FOCUS_TERMS.search(
            f"{clean_text(row.get('title'))} {clean_text(row.get('summary'))}"
        ):
            raw_value = row.get("raw")
            raw = dict(raw_value) if isinstance(raw_value, dict) else {}
            raw["needsEditorialReview"] = True
            normalized = {**row, "kind": "ai-paper", "raw": raw}
        duplicate_id = next(
            (
                existing_id
                for existing_id, existing in deduplicated.items()
                if records_match(existing, normalized)
            ),
            None,
        )
        if duplicate_id is None:
            deduplicated[row_id] = normalized
        else:
            deduplicated[duplicate_id] = merge_candidates(
                deduplicated[duplicate_id],
                normalized,
            )
    return {
        row_id: row
        for row_id, row in deduplicated.items()
        if not record_identity_keys(row).intersection(excluded)
        and not any(
            records_match(row, blocked, allow_missing_author=True)
            for blocked in blocked_records
        )
    }


def persist_run(
    output_path: Path,
    output: dict[str, Any],
    state_path: Path,
    state: dict[str, Any],
) -> None:
    # Inbox first gives at-least-once behavior: if the state write fails, the
    # next run refetches the window and candidate deduplication absorbs it.
    write_json(output_path, output)
    write_json(state_path, state)


def collection_exit_code(source_status: list[dict[str, Any]]) -> int:
    paper_sources = [
        status
        for status in source_status
        if clean_text(status.get("source")).startswith(("arXiv", "Crossref"))
    ]
    if paper_sources and not any(status.get("status") == "ok" for status in paper_sources):
        return 2
    return 0 if any(status.get("status") == "ok" for status in source_status) else 1


def source_cutoff(
    name: str,
    state: dict[str, Any],
    now: datetime,
    fallback: datetime,
    force_days: int | None,
    minimum_lookback: timedelta | None = None,
) -> datetime:
    if force_days is not None:
        return now - timedelta(days=force_days)
    sources = state.get("sources", {})
    source = sources.get(name, {}) if isinstance(sources, dict) else {}
    last_success = source.get("lastSuccessfulAt") if isinstance(source, dict) else None
    if not isinstance(last_success, str):
        return min(fallback, now - minimum_lookback) if minimum_lookback else fallback
    try:
        cutoff = max(parse_datetime(last_success) - STATE_OVERLAP, now - MAX_STATE_LOOKBACK)
        return min(cutoff, now - minimum_lookback) if minimum_lookback else cutoff
    except ValueError:
        return min(fallback, now - minimum_lookback) if minimum_lookback else fallback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since-hours", type=int, default=3, help="fallback window without state")
    parser.add_argument("--days", type=int, help="explicit backfill window; ignores saved cursors")
    parser.add_argument("--max-per-source", type=int, default=30)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    args = parser.parse_args()

    if args.since_hours < 1 or args.max_per_source < 1 or (args.days is not None and args.days < 1):
        parser.error("collection windows and --max-per-source must be positive")

    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    state_path = args.state if args.state.is_absolute() else ROOT / args.state
    processed_path = args.processed if args.processed.is_absolute() else ROOT / args.processed
    now = datetime.now(timezone.utc)
    fallback = now - timedelta(hours=args.since_hours)
    state = load_json(state_path, {"updatedAt": None, "sources": {}})
    if not isinstance(state.get("sources"), dict):
        state["sources"] = {}
    blocked_records = [*curated_records(), *processed_records(processed_path)]
    excluded = {
        key
        for record in blocked_records
        for key in record_identity_keys(record)
    }
    candidates: list[dict[str, Any]] = []
    discovered_candidates: list[dict[str, Any]] = []
    source_status: list[dict[str, Any]] = []

    collectors: list[
        tuple[str, Callable[[datetime], list[dict[str, Any]]], timedelta | None, int]
    ] = [
        ("CISA KEV", lambda cutoff: collect_cisa(cutoff, None), None, 0),
        ("NIST NVD", lambda cutoff: collect_nvd(cutoff, now, None), None, 0),
        (
            "Crossref Journal Security",
            lambda cutoff: collect_crossref_security(
                cutoff,
                now,
                None,
                "journal-article",
            ),
            None,
            0,
        ),
        (
            "Crossref Proceedings Security",
            lambda cutoff: collect_crossref_security(
                cutoff,
                now,
                None,
                "proceedings-article",
            ),
            None,
            0,
        ),
    ]
    collectors[2:2] = [
        (
            source,
            lambda cutoff, source=source, url=url, kind=kind,
            evidence_level=evidence_level, priority=priority: collect_official_feed(
                cutoff,
                None,
                source=source,
                url=url,
                kind=kind,
                evidence_level=evidence_level,
                priority=priority,
            ),
            None,
            0,
        )
        for source, url, kind, evidence_level, priority in OFFICIAL_FEEDS
    ]
    paper_offset = 2 + len(OFFICIAL_FEEDS)
    if args.days is None:
        collectors.insert(
            paper_offset,
            (
                "arXiv Daily",
                lambda cutoff: collect_arxiv_current_or_recover(
                    cutoff,
                    now,
                    None,
                ),
                None,
                0,
            ),
        )
    else:
        collectors[paper_offset:paper_offset] = [
            (
                "arXiv Security",
                lambda cutoff: collect_arxiv_security(cutoff, None),
                ARXIV_MIN_LOOKBACK,
                0,
            ),
            (
                "arXiv AI",
                lambda cutoff: collect_arxiv_ai(cutoff, None),
                ARXIV_MIN_LOOKBACK,
                3,
            ),
        ]
    for name, collector, minimum_lookback, request_delay in collectors:
        cutoff = source_cutoff(name, state, now, fallback, args.days, minimum_lookback)
        source_entry = state["sources"].setdefault(name, {})
        source_entry["lastAttemptAt"] = now.isoformat(timespec="seconds")
        try:
            if request_delay:
                time.sleep(request_delay)
            discovered = collector(cutoff)
            discovered_candidates.extend(
                {**row, "collectorSource": name}
                for row in discovered
            )
            source_entry.update(
                {
                    "lastSuccessfulAt": now.isoformat(timespec="seconds"),
                    "status": "ok",
                    "error": None,
                }
            )
            source_status.append(
                {
                    "source": name,
                    "status": "ok",
                    "count": 0,
                    "discoveredCount": len(discovered),
                    "since": cutoff.isoformat(),
                }
            )
        except Exception as exc:  # keep other feeds usable when one upstream is unavailable
            source_entry.update({"status": "error", "error": str(exc)})
            source_status.append(
                {"source": name, "status": "error", "error": str(exc), "since": cutoff.isoformat()}
            )

    eligible_discovered = deduplicate_candidates(
        discovered_candidates,
        excluded,
        blocked_records,
    )
    for status in source_status:
        if status["status"] != "ok":
            continue
        source_rows = [
            row
            for row in eligible_discovered.values()
            if row.get("collectorSource") == status["source"]
        ]
        selected = cap_candidates_by_kind(source_rows, args.max_per_source)
        status["count"] = len(selected)
        candidates.extend(selected)

    existing = load_json(output_path, {"candidates": []}).get("candidates", [])
    pending = (
        [
            row
            for row in existing
            if isinstance(row, dict) and pending_candidate_is_relevant(row)
        ]
        if isinstance(existing, list)
        else []
    )
    pending.extend(candidates)
    deduplicated = deduplicate_candidates(pending, excluded, blocked_records)
    output = {
        "collectedAt": now.isoformat(timespec="seconds"),
        "fallbackHours": args.since_hours,
        "notice": "Uncurated candidates. Verify every primary source before publishing.",
        "sources": source_status,
        "candidates": sorted(
            deduplicated.values(),
            key=lambda row: (row["publishedAt"], row["priority"]),
            reverse=True,
        ),
    }
    state["updatedAt"] = now.isoformat(timespec="seconds")
    persist_run(output_path, output, state_path, state)

    print(f"Collected {len(candidates)} new candidate(s); {len(output['candidates'])} pending -> {output_path}")
    for status in source_status:
        detail = status.get("count", status.get("error", "unknown"))
        print(f"- {status['source']}: {status['status']} ({detail})")
    exit_code = collection_exit_code(source_status)
    if exit_code == 2:
        print("No paper discovery source completed successfully.", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
