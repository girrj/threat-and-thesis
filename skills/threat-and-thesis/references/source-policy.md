# Source and publication policy

## Source order

Prefer sources in this order:

1. Government and standards bodies: KISA/KrCERT, CISA, NIST/NVD, ENISA, CERT/CC.
2. Primary research records: publisher or conference pages, DOI landing pages, arXiv author submissions.
3. Maintained security knowledge bases: MITRE ATT&CK/ATLAS, OWASP projects.
4. Vendor security advisories and official engineering/research blogs.
5. Reputable secondary reporting only as discovery context, never as the sole support for a technical claim.

The incremental collector currently monitors CISA KEV, NIST NVD, arXiv, Crossref, Google Security Blog, Google Project Zero, Cloudflare Security Blog, GitHub Security Blog, and the IACR Cryptology ePrint Archive. A feed entry is only a discovery candidate: open and verify the linked primary page before publication.

Use the most specific stable URL available. A search results page, social post, newsletter excerpt, or generated answer is not a primary source.

arXiv category labels and Crossref metadata are discovery signals. They may suggest a paper class or publication venue, but they do not replace reading the abstract and confirming venue status on the author, publisher, or conference page. A Crossref DOI record alone does not establish peer review.

## Evidence labels

- `official`: government, standards body, maintained official knowledge base, or vendor advisory.
- `peer-reviewed`: the source explicitly identifies publication in a peer-reviewed venue.
- `preprint`: arXiv or another manuscript that does not establish peer review.
- `industry`: an official company technical release, benchmark, or engineering post that is not a security advisory.

When uncertain, use the less authoritative label and state the uncertainty in `limitations`.

## Minimum checks

For vulnerabilities, confirm identifier, affected product, publication/update date, exploitation status, severity basis, and remediation. Do not turn a CVSS score into an exploitation claim.

For papers, confirm authorship, title, version date, venue status, studied task/data, reported result, and limitations. Avoid converting correlation, a benchmark gain, or a lab demonstration into a general real-world claim.

Before marking a paper as library-only, check the publisher or DOI landing page, an author or institutional repository, arXiv, and an OpenAlex or Unpaywall open-access location when available. Omit `requiresLibraryAccess` whenever a lawful public full text exists. Set `requiresLibraryAccess: true` only for an `ai-paper` or `security-paper` whose full text is actually gated by payment or subscription. Keep `sourceUrl` pointed at the DOI or publisher record, not the university proxy. If the gated full text has not been read, limit claims to the public abstract and say so in `limitations`.

For frameworks and technology releases, confirm document status such as draft/final, version, scope, and official release or update date.

## Duplicate rules

Treat records as duplicates if they share a source URL or identifier. When a later source materially changes an existing item, update that item and use `dateLabel: 수정일`; do not create a near-identical card.

Each KST daily edition uses `selectionMode: new-only`. Include an item only on the first date it is published by this site, use `previousRank: null` and `status: new`, and never carry it forward into a later edition. An empty new-only edition is valid and must be created once when a new KST date begins so the latest view cannot repeat yesterday's items.
