# Source and publication policy

## Source order

Prefer sources in this order:

1. Government and standards bodies: KISA/KrCERT, CISA, NIST/NVD, ENISA, CERT/CC.
2. Primary research records: publisher or conference pages, DOI landing pages, arXiv author submissions.
3. Maintained security knowledge bases: MITRE ATT&CK/ATLAS, OWASP projects.
4. Vendor security advisories and official engineering/research blogs.
5. Reputable secondary reporting only as discovery context, never as the sole support for a technical claim.

Use the most specific stable URL available. A search results page, social post, newsletter excerpt, or generated answer is not a primary source.

## Evidence labels

- `official`: government, standards body, maintained official knowledge base, or vendor advisory.
- `peer-reviewed`: the source explicitly identifies publication in a peer-reviewed venue.
- `preprint`: arXiv or another manuscript that does not establish peer review.
- `industry`: an official company technical release, benchmark, or engineering post that is not a security advisory.

When uncertain, use the less authoritative label and state the uncertainty in `limitations`.

## Minimum checks

For vulnerabilities, confirm identifier, affected product, publication/update date, exploitation status, severity basis, and remediation. Do not turn a CVSS score into an exploitation claim.

For papers, confirm authorship, title, version date, venue status, studied task/data, reported result, and limitations. Avoid converting correlation, a benchmark gain, or a lab demonstration into a general real-world claim.

For frameworks and technology releases, confirm document status such as draft/final, version, scope, and official release or update date.

## Duplicate rules

Treat records as duplicates if they share a source URL or identifier. When a later source materially changes an existing item, update that item and use `dateLabel: 수정일`; do not create a near-identical card.
