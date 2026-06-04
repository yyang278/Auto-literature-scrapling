---
name: obhrm-literature-monitor
description: Monitor OBHRM/HCI/preprint target-source articles, build and review journal/platform whitelists, run keyword-based weekly literature scans, generate Markdown/CSV reports, and optionally push compliant summaries through Lark. Use when the user asks for OBHRM literature monitoring, HCI journal monitoring, SSRN/NBER preprint monitoring, top-journal article scraping, weekly research alerts, whitelist generation from FT50/UTD24/AJG/ABDC/HCI sources, or maintaining this repo's literature monitor.
---

# OBHRM Literature Monitor

## Core Rules

- Treat the repository version as the source of truth. Install or sync to the local Codex skills directory only after the repo version is validated.
- Always build or refresh the journal/platform whitelist before adding new sources to a scan.
- Pause for user review after generating `data/whitelist/journals_review.md`; do not run production scans against a new whitelist until the user confirms it.
- Support `Asia/Tokyo`, `America/Chicago`, and `Asia/Shanghai` for user-entered windows. The weekly production window is previous Monday 00:00 inclusive to current Monday 00:00 exclusive in the selected timezone.
- Keep keywords easy to replace through `config/monitor.yaml`, command-line arguments, or GitHub Actions keyword fields.
- Treat quoted multi-word inputs such as `"Business History"` as ordered phrases by stripping only the outer quotes before matching. Do not imply full Web of Science query-builder support unless it is explicitly implemented.
- For team self-service runs, prefer the GitHub Actions manual workflow over asking every teacher/student to install Codex locally.

## Compliance Boundary

Never automate institutional login, SSO, paywall bypass, CAPTCHA solving, anti-bot circumvention, or PDF/full-text downloading. Per-article reports include DOI URLs only; authorized readers must manually use their own university access for full text.

Read `references/source_policy.md` before implementing or changing source access, publisher enrichment, full-text access boundaries, or delivery behavior.

## Workflows

### Build Journal Whitelist

Run:

```powershell
python skills/obhrm-literature-monitor/scripts/build_whitelist.py --abdc-file "C:\path\to\ABDC-JQL-2025-v1-260326.xlsx"
```

Expected outputs:

- `data/whitelist/journals.csv`
- `data/whitelist/journals_review.md`

Use `journals_review.md` for human review. The current target-source whitelist contains approved OBHRM/HCI/preprint sources selected from FT50, UTD24, AJG/ABS 2024 `4`/`4*`, ABDC 2025 `A`/`A*`, 9 SJR Q1 HCI journals, and SSRN/NBER. `Operations Research` is excluded from all selectable source lists.

### Run Trial Scan

Only run this after the user approves the journal review list. The planned first trial window is:

```text
2026-05-25 08:00 <= article publication/update time < 2026-05-26 08:00
Timezone: Asia/Tokyo
```

Use active keywords from `config/monitor.yaml`, or pass up to five temporary keyword concepts. Use `--match-mode any` for OR logic and `--match-mode all` for AND logic:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --keyword "work engagement" --keyword turnover --keyword "self-sacrifice leadership" --match-mode any
```

For ordered phrase searches, keep the phrase as one keyword. Quoted inputs are accepted and normalized:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --keyword '"Business History"' --keyword Asia --match-mode all
```

The production pipeline retrieves candidates by OpenAlex source/concept/window and then performs local matching over public title, abstract, and keyword metadata. The `matched_fields` output shows whether the hit came from title, abstract, keywords, or a combination.

The default scan strategy is `openalex-source`: resolve each whitelist source to its OpenAlex source id, then query each source/concept/window combination and write a source-by-source traversal trace. Use this for production and any research-sensitive search.
Use `--strategy openalex-keyword` only as a fast exploratory shortcut: it searches OpenAlex globally by keyword/date first and then filters to the whitelist, so it can miss many whitelist articles in broad keywords or long windows. Use `--strategy crossref-journal` only as a fallback when OpenAlex source metadata appears incomplete.
Production GitHub runs use OpenAlex cursor pagination exhaustively. `--max-pages` is an optional local/debug safety cap; keep it at `0` for comprehensive source-first scans. The trace file flags source/concept rows as incomplete if a manual cap or API interruption prevents full retrieval.

For weekly production-style scans, use the previous-week window:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --previous-week
```

To test a specific full week manually, pass Monday 00:00 to the following Monday 00:00:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --start "2026/05/18 00:00" --end "2026/05/25 00:00"
```

Use `--journal-list` to reduce scope for broad concepts. Available lists:

- `all-whitelist`: all approved OBHRM/HCI/preprint whitelist sources.
- `abs-4-and-4-star`: ABS/AJG 2024 4 and 4* sources within the whitelist.
- `abs-4-star`: ABS/AJG 2024 4* sources within the whitelist.
- `ft50`: FT50 sources within the whitelist.
- `utd24`: UTD24 sources within the whitelist.

When a hosted HTML report exists and the scan has already been run, push only the short Lark summary without re-scanning:

```powershell
python skills/obhrm-literature-monitor/scripts/push_lark_report_summary.py --csv outputs/<run-folder>/obhrm_daily_records.csv --start "2026/05/18 00:00" --end "2026/05/25 00:00" --concepts "Presenteeism" --public-report-url https://example.netlify.app/reports/<run-folder>/ --public-index-url https://example.netlify.app/
```

### Check Push Configuration

Run:

```powershell
python skills/obhrm-literature-monitor/scripts/check_config.py
```

Required environment variables for push channels:

- `OBHRM_LARK_WEBHOOK_URL`
- optional `OBHRM_LARK_WEBHOOK_SECRET`

Local report generation must still work when push variables are missing.

Lark push summaries must stay short. Include only:

- active concepts/keywords
- selected timezone window
- journal/platform names with matched article counts

Do not include article titles, DOI lists, local file paths, Missing Abstract counts, or full report text in the Lark summary. Add full-report links only after a public/shared HTML hosting location is configured.

## Report Requirements

Reports must include:

- title
- journal
- publication date
- DOI URL
- authors
- affiliations
- abstract status
- abstract
- keywords
- matched concepts
- matched fields

CSV outputs must use the same field order. Do not include fields not listed above in per-article outputs.
When a scan uses multiple keyword concepts, split the Markdown/HTML `At a Glance`, `Articles With Abstracts`, and `Missing Abstract` presentation by keyword concept while keeping the CSV as one stable record table.

Generate the standalone HTML report from Markdown with:

```powershell
python skills/obhrm-literature-monitor/scripts/render_report_html.py --input outputs/<run-folder>/obhrm_daily_report.md
```

When `obhrm_keyword_trends.json` exists beside the Markdown report, the HTML renderer adds a `Keyword Trajectories` section with clickable per-keyword SVG charts and a combined multi-line chart. The combined chart defaults to `% of keyword peak` so low-frequency keywords remain legible, and also provides `Raw counts`. Hover details use raw yearly counts and the top-cited OpenAlex candidate for that keyword/year. Single-keyword reports show one interactive trajectory chart instead of a combined chart plus duplicate card; multi-keyword reports add jump links to each keyword-specific article list, and enlarged per-keyword charts keep the same hover and scale-toggle interactions as the combined chart. The trend charts show per-keyword yearly candidate counts within the selected sources/window; final article inclusion is still controlled by `match_mode`.

Publish the HTML report into the Netlify static site directory with:

```powershell
python skills/obhrm-literature-monitor/scripts/publish_report_site.py --input outputs/<run-folder>/obhrm_daily_report.html
```

The generated public path is `site/reports/<run-folder>/`. Netlify should publish the repository's `site` directory.
The public site copy removes email addresses found in article metadata while leaving local Markdown/CSV/HTML outputs unchanged.

## GitHub Web UI Workflow

Use `.github/workflows/generate-literature-report.yml` when a collaborator needs to generate a report without local Codex or Python setup. The workflow exposes a GitHub `Run workflow` form with:

- `keyword_1` to `keyword_5`: up to five concepts, one per field; blank fields are ignored.
- `timezone`: one of `Asia/Tokyo`, `America/Chicago`, or `Asia/Shanghai`.
- `start_date` and `start_clock`: inclusive start date and time, such as `2026/05/18` and `00:00`.
- `end_date` and `end_clock`: exclusive end date and time, such as `2026/05/25` and `00:00`; the script rejects windows where end is not later than start.
- `match_mode`: `any` for OR logic, or `all` for AND logic.
- journal list checkboxes: one or more of `all-whitelist`, `abs-4-and-4-star`, `abs-4-star`, `ft50`, and `utd24`. The workflow scans the union of all selected lists. `abs-4-star` is selected by default as the most selective option.
- optional output label and public site URL.

The web workflow intentionally hides low-level OpenAlex controls from ordinary users. It uses the production `openalex-source` traversal with repository defaults.

GitHub only shows `Run workflow` to users with sufficient permission on that repository. For teacher/student self-service, direct them to fork the repository and run the workflow in their fork.

The workflow runs `scripts/run_github_report.py`, which scans, renders standalone HTML, publishes the public copy under `site/reports/<run-folder>/`, uploads Markdown/HTML/CSV/log artifacts to the workflow run, commits `site/`, and deploys `site/` to GitHub Pages. If `public_site_url` is left blank in the workflow form, the workflow computes the fork's default GitHub Pages URL: `https://<github-user>.github.io/<repo-name>/`.

The workflow also uploads `obhrm_scan_trace.csv`. Use this file to audit the traversal process: it records each source, source id, concept, API total count, fetched count, page count, status, and query URL.
The workflow also uploads `obhrm_keyword_trends.json`, which stores the yearly keyword counts and top-cited candidate metadata used by the HTML chart section.

Repository secrets for Lark push:

- `OBHRM_LARK_WEBHOOK_URL`
- optional `OBHRM_LARK_WEBHOOK_SECRET`

If the Lark webhook secret is missing, report generation and GitHub Pages publishing still proceed; the workflow logs that Lark push was skipped.
