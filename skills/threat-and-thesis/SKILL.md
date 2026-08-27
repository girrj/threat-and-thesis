---
name: threat-and-thesis
description: Operate and modify the Threat & Thesis GitHub Pages service. Use whenever the user mentions Threat & Thesis, threat-and-thesis, its homepage or design, category and ranking changes, collectors, research curation, deployment, or the three-hour refresh. Supports both interactive Telegram maintenance and scheduled content-only updates.
---

# Threat & Thesis

## Overview

Maintain the repository's daily ranked research letter and its website. Prefer primary sources, preserve a clear distinction between facts and interpretation, and keep scheduled collection separate from user-requested code changes.

## Repository

- Worktree: `/Users/jaydev/codex_dev/threat-and-thesis-hermes`
- Remote: `https://github.com/girrj/threat-and-thesis.git`
- Public site: `https://girrj.github.io/threat-and-thesis/`
- After entering the worktree, read `AGENTS.md` and `EDITORIAL.md`. For collection work also read `HERMES_PROMPT.md` and `skills/threat-and-thesis/references/source-policy.md` from the repository.

## Choose the mode

- **Scheduled refresh:** when invoked by `threat-and-thesis-3h`, follow the content workflow below. Do not alter UI, schemas, automation policy, dependencies, or collection code.
- **Interactive maintenance:** when the authenticated user directly asks in Telegram to change, fix, apply, or deploy the site, follow the interactive workflow. This mode may change design, code, schemas, collectors, and operating instructions within the requested scope.
- Treat requests for analysis, review, ideas, or status as read-only. Treat direct imperatives such as `수정해`, `바꿔`, `적용해`, or `배포해` as authorization to implement and publish after validation. Ask before destructive deletion, credential changes, or materially ambiguous choices.

## Scheduled content workflow

1. Work from the repository root and read `AGENTS.md`, `EDITORIAL.md`, and `skills/threat-and-thesis/references/source-policy.md`.
2. Run `python3 scripts/collect.py --since-hours 3` with a terminal timeout of at least 900 seconds. The script uses per-source cursors and automatically catches up after a missed run. Use `--days N` only for an explicit backfill. After a timeout, confirm that no `collect.py` process is still running before retrying.
3. Inspect `data/inbox.json` and `data/source-state.json`. Report individual source errors; do not treat one failed feed as proof that no updates exist. Treat arXiv `kind` as a classification suggestion, and treat Crossref `publication-record` as discovery metadata rather than proof of peer review.
4. Deduplicate candidates against `content/articles.json` by URL, identifier, and normalized title.
5. Open the primary source for every candidate under consideration. Exclude items whose date, identity, or material claim cannot be verified.
6. Select only consequential items. For papers, read at least the abstract, methodology/result claims, and stated limitations. For vulnerabilities, confirm affected products, exploitation status, and remediation from official records.
7. For each selected paper, check the publisher or DOI page and lawful open-access locations. Add `requiresLibraryAccess: true` only when no public full text exists and payment or institutional subscription is required. Keep the DOI or publisher record in `sourceUrl`; never store a university proxy URL there. If the gated full text has not been read, restrict the entry to claims supported by the public abstract and disclose that limit.
8. Update `content/articles.json`, today's `content/daily/YYYY-MM-DD.json`, and `data/processed.json`. Set today's edition to `selectionMode: new-only` and include only items first published by the site on that KST date. Preserve older articles, valid source URLs, and completed daily snapshots.
9. Never create a combined overall ranking. Rank at most 10 newly published items inside each category, restarting at rank 1 for every category. Empty categories are valid. Every new-only ranking uses `previousRank: null` and `status: new`; never carry an older item into today's edition. If no item is selected, create one empty edition for the new KST date so the homepage does not keep showing yesterday's material.
10. Run `npm run content:validate`, `npm run lint`, and `npm test`. For repository Pages, also run `SITE_BASE_PATH=/REPOSITORY_NAME npm run build:pages` when the repository name is known.
11. Summarize additions, exclusions, rank changes, feed failures, and verification results. Do not commit or push unless explicitly asked. If nothing public changed, do not make an empty commit.

## Interactive maintenance workflow

1. Change to the repository worktree above. Confirm the remote is `girrj/threat-and-thesis`, inspect `git status`, and preserve unexpected changes. If clean, run `git pull --ff-only origin main`.
2. Confirm no scheduled refresh or `collect.py` process is modifying the same worktree. If another run is active, report it and wait instead of editing concurrently.
3. Read the files relevant to the request. Use `EDITORIAL.md` for visual and writing rules; inspect the rendered page before making visual judgments.
4. Create a `hermes/<short-task>` branch before editing. Keep changes limited to the user's request and never overwrite unrelated work.
5. Implement the change. When behavior or responsibilities change, update `AGENTS.md`, `HERMES_PROMPT.md`, this skill, and README only where needed so the scheduled agent and interactive agent remain consistent.
6. Run checks proportional to risk. For any code or content change run `npm test`; for UI or Pages changes also run `SITE_BASE_PATH=/threat-and-thesis npm run build:pages` and inspect the rendered result in a browser.
7. If the user asked to apply or deploy, commit only the intended paths, fast-forward the verified branch into `main`, push `origin/main`, and confirm the GitHub Pages workflow succeeds. Do not create an empty commit.
8. Report the changed behavior, tests, commit, deployment URL, and any remaining limitation in the same Telegram conversation.

## Curation Requirements

- Write concise Korean titles and summaries. Keep the original title in `originalTitle` when available.
- Attribute every concrete claim to the linked source. Never infer version numbers, CVSS values, publication dates, or experimental results.
- Keep `summary` factual, `whyItMatters` interpretive, and `limitations` explicit.
- Use `evidenceLevel: preprint` for unreviewed arXiv work. Do not describe a preprint as established evidence.
- Classify research by its primary contribution: use `ai-paper` for work centered on AI models, agents, or machine learning, and `security-paper` for systems, network, cryptography, or software-security research. Choose one primary class for cross-disciplinary work and explain the judgment in the report.
- Use defensive `action` text. Do not add exploit instructions, payloads, credential theft steps, or attack automation.
- Set priority using the ranges in `AGENTS.md`; priority is an internal editorial aid, not a probability or CVSS substitute, and is not shown on the site.
- Build each category's daily ranks from urgency, verified exploitation, source authority, freshness, practical impact, and research contribution. Do not rank by priority alone or compare unlike categories.
- Update `generatedAt` only after the curated file changes.

## Output Checklist

- The public JSON validates.
- Today's daily edition exists, its ranks are sequential, and the generated index is current.
- The static and runtime builds pass.
- Every new item has a working primary-source URL.
- `requiresLibraryAccess` appears only on papers with no verified public full text.
- Preprints and official publications are labeled correctly.
- The report names items deliberately excluded and why.
