---
name: obhrm-literature-monitor
description: Monitor OBHRM/HCI/preprint target-source articles, build and review journal/platform whitelists, run keyword-based weekly literature scans, generate Markdown/CSV reports, and optionally push compliant summaries through Lark. Use when the user asks for OBHRM literature monitoring, HCI journal monitoring, SSRN/NBER preprint monitoring, top-journal article scraping, weekly research alerts, whitelist generation from FT50/UTD24/AJG/ABDC/HCI sources, or maintaining this repo's literature monitor.
---

# OBHRM Literature Monitor

## Core Rules

- Treat the repository version as the source of truth. Install or sync to the local Codex skills directory only after the repo version is validated.
- Always build or refresh the journal/platform whitelist before adding new sources to a scan.
- Pause for user review after generating `data/whitelist/journals_review.md`; do not run production scans against a new whitelist until the user confirms it.
- Use Asia/Tokyo for all windows. The weekly production window is previous Monday 00:00 inclusive to current Monday 00:00 exclusive.
- Keep keywords easy to replace through `config/monitor.yaml` or command-line arguments.

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

Use `journals_review.md` for human review. The current target-source whitelist contains 198 sources: OBHRM candidates selected from FT50, UTD24, AJG/ABS 2024 `4`/`4*`, ABDC 2025 `A`/`A*`, 9 SJR Q1 HCI journals, and SSRN/NBER.

### Run Trial Scan

Only run this after the user approves the journal review list. The planned first trial window is:

```text
2026-05-25 08:00 <= article publication/update time < 2026-05-26 08:00
Timezone: Asia/Tokyo
```

Use active keywords from `config/monitor.yaml`, or pass a temporary keyword string separated by semicolons:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --keywords "work engagement; turnover; self-sacrifice leadership"
```

The default scan strategy is `openalex-keyword`: search OpenAlex by keyword/date first, filter to the approved OBHRM whitelist, then enrich by DOI through Crossref. Use `--strategy crossref-journal` only as a slower fallback when keyword-first discovery appears incomplete.

For weekly production-style scans, use the previous-week window:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --previous-week
```

To test a specific full week manually, pass Monday 00:00 to the following Monday 00:00:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --start 2026-05-18T00:00 --end 2026-05-25T00:00
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
- Tokyo-time window
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

CSV outputs must use the same field order. Do not include fields not listed above in per-article outputs.

Generate the standalone HTML report from Markdown with:

```powershell
python skills/obhrm-literature-monitor/scripts/render_report_html.py --input outputs/<run-folder>/obhrm_daily_report.md
```

Publish the HTML report into the Netlify static site directory with:

```powershell
python skills/obhrm-literature-monitor/scripts/publish_report_site.py --input outputs/<run-folder>/obhrm_daily_report.html
```

The generated public path is `site/reports/<run-folder>/`. Netlify should publish the repository's `site` directory.
The public site copy removes email addresses found in article metadata while leaving local Markdown/CSV/HTML outputs unchanged.
