# Source and Access Policy

## Ranking Sources

Use these sources for the top-journal whitelist:

- FT50 journal list.
- UTD24 journal list.
- AJG/ABS 2024 entries with rating `4` or `4*`.
- ABDC 2025 JQL entries with rating `A` or `A*`.
- Selected Journals and Magazines in HCI entries marked `SJR Q1` on `https://uni.ubicomp.net/hci/`.
- SSRN and NBER as approved preprint/working-paper platforms.

For ABDC, use a local copy of `ABDC-JQL-2025-v1-260326.xlsx` supplied through `build_whitelist.py --abdc-file`. Read sheet `2025 JQL`, with the header row at Excel row 8, and strip whitespace from `2025 rating`.

## Article Metadata Sources

Prefer public metadata APIs first:

1. Crossref for DOI, title, journal, date, publisher, and URL discovery.
2. OpenAlex for author affiliations, abstract index, concepts, and metadata enrichment.
3. Publisher pages only for public, compliant metadata enrichment.

Do not use scraping tactics that bypass access controls. If a publisher page blocks access, preserve the metadata already found and note the limitation.

## Full Text Boundary

Allowed:

- DOI links.
- Manual instructions telling readers to use their own university accounts.

Not allowed:

- Automated institutional login.
- SSO automation.
- CAPTCHA or anti-bot bypass.
- Paywall bypass.
- Automatic PDF downloads.
- Bulk full-text storage.
- Sending copyrighted full text to external messaging channels.

## Missing Abstracts

If no abstract is available from public metadata or compliant publisher enrichment, keep the article in the report when it otherwise matches the keyword/search logic. Mark `abstract_status=missing` and list it in a separate Missing Abstract section.

## University Access Links

Do not emit unverified university search or guide URLs in article outputs. Keep per-article reports to DOI URLs unless the user later provides a verified direct link resolver template.
