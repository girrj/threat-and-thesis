---
name: threat-and-thesis
description: Collect, verify, rank, and preserve daily information-security alerts, AI security guidance, research papers, and technology updates for the Threat & Thesis GitHub Pages repository. Use when asked to run the three-hour refresh, prepare a daily security/AI ranking, review data/inbox.json, or update public content with source-backed Korean summaries.
---

# Threat & Thesis

## Overview

Maintain the repository's daily ranked research letter without publishing unverified collector output. Prefer primary sources and preserve a clear distinction between facts, interpretation, and limitations.

## Workflow

1. Work from the repository root and read `AGENTS.md`, `EDITORIAL.md`, plus [references/source-policy.md](references/source-policy.md).
2. Run `python3 scripts/collect.py --since-hours 3`. The script uses per-source cursors and automatically catches up after a missed run. Use `--days N` only for an explicit backfill.
3. Inspect `data/inbox.json` and `data/source-state.json`. Report individual source errors; do not treat one failed feed as proof that no updates exist.
4. Deduplicate candidates against `content/articles.json` by URL, identifier, and normalized title.
5. Open the primary source for every candidate under consideration. Exclude items whose date, identity, or material claim cannot be verified.
6. Select only consequential items. For papers, read at least the abstract, methodology/result claims, and stated limitations. For vulnerabilities, confirm affected products, exploitation status, and remediation from official records.
7. Update `content/articles.json`, today's `content/daily/YYYY-MM-DD.json`, and `data/processed.json`. Preserve older articles, valid source URLs, and completed daily snapshots.
8. Rank at most 10 current items. Compare them with the immediately preceding daily edition and record `previousRank`, `status`, and a factual one-sentence `reason`. Use `returning` when an item reappears after missing an edition.
9. Run `npm run content:validate`, `npm run lint`, and `npm test`. For repository Pages, also run `SITE_BASE_PATH=/REPOSITORY_NAME npm run build:pages` when the repository name is known.
10. Summarize additions, exclusions, rank changes, feed failures, and verification results. Do not commit or push unless explicitly asked. If nothing public changed, do not make an empty commit.

## Curation Requirements

- Write concise Korean titles and summaries. Keep the original title in `originalTitle` when available.
- Attribute every concrete claim to the linked source. Never infer version numbers, CVSS values, publication dates, or experimental results.
- Keep `summary` factual, `whyItMatters` interpretive, and `limitations` explicit.
- Use `evidenceLevel: preprint` for unreviewed arXiv work. Do not describe a preprint as established evidence.
- Classify research by its primary contribution: use `ai-paper` for work centered on AI models, agents, or machine learning, and `security-paper` for systems, network, cryptography, or software-security research. Choose one primary class for cross-disciplinary work and explain the judgment in the report.
- Use defensive `action` text. Do not add exploit instructions, payloads, credential theft steps, or attack automation.
- Set priority using the ranges in `AGENTS.md`; priority is an internal editorial aid, not a probability or CVSS substitute, and is not shown on the site.
- Build daily ranks from urgency, verified exploitation, source authority, freshness, practical impact, and research contribution. Do not rank by priority alone.
- Update `generatedAt` only after the curated file changes.

## Output Checklist

- The public JSON validates.
- Today's daily edition exists, its ranks are sequential, and the generated index is current.
- The static and runtime builds pass.
- Every new item has a working primary-source URL.
- Preprints and official publications are labeled correctly.
- The report names items deliberately excluded and why.
