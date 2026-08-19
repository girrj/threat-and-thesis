---
name: threat-and-thesis
description: Collect, verify, curate, and validate current information-security alerts, AI security guidance, research papers, and technology updates for the Threat & Thesis GitHub Pages repository. Use when asked to refresh the feed, prepare a security/AI briefing, review data/inbox.json, or update content/articles.json with source-backed Korean summaries.
---

# Threat & Thesis

## Overview

Maintain the repository's public intelligence feed without publishing unverified collector output. Prefer primary sources and preserve a clear distinction between facts, interpretation, and limitations.

## Workflow

1. Work from the repository root and read `AGENTS.md`, `EDITORIAL.md`, plus [references/source-policy.md](references/source-policy.md).
2. Run `python3 scripts/collect.py --days 14` unless the user supplied a narrower period.
3. Inspect `data/inbox.json`. Report individual source errors; do not treat one failed feed as proof that no updates exist.
4. Deduplicate candidates against `content/articles.json` by URL, identifier, and normalized title.
5. Open the primary source for every candidate under consideration. Exclude items whose date, identity, or material claim cannot be verified.
6. Select only consequential items. For papers, read at least the abstract, methodology/result claims, and stated limitations. For vulnerabilities, confirm affected products, exploitation status, and remediation from official records.
7. Edit only `content/articles.json` unless the user requested a code or policy change. Preserve older entries and valid source URLs.
8. Run `python3 scripts/validate.py` and `npm test`. For repository Pages, also run `SITE_BASE_PATH=/REPOSITORY_NAME npm run build:pages` when the repository name is known.
9. Summarize additions, exclusions, feed failures, and verification results. Do not commit or push unless explicitly asked.

## Curation Requirements

- Write concise Korean titles and summaries. Keep the original title in `originalTitle` when available.
- Attribute every concrete claim to the linked source. Never infer version numbers, CVSS values, publication dates, or experimental results.
- Keep `summary` factual, `whyItMatters` interpretive, and `limitations` explicit.
- Use `evidenceLevel: preprint` for unreviewed arXiv work. Do not describe a preprint as established evidence.
- Classify research by its primary contribution: use `ai-paper` for work centered on AI models, agents, or machine learning, and `security-paper` for systems, network, cryptography, or software-security research. Choose one primary class for cross-disciplinary work and explain the judgment in the report.
- Use defensive `action` text. Do not add exploit instructions, payloads, credential theft steps, or attack automation.
- Set priority using the ranges in `AGENTS.md`; priority is editorial ordering, not a probability or CVSS substitute.
- Update `generatedAt` only after the curated file changes.

## Output Checklist

- The public JSON validates.
- The static and runtime builds pass.
- Every new item has a working primary-source URL.
- Preprints and official publications are labeled correctly.
- The report names items deliberately excluded and why.
