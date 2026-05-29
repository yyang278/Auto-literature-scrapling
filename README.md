# OBHRM Literature Monitor

This repository packages a reusable Codex skill for monitoring new articles from an approved OBHRM/HCI/preprint target-source whitelist.

The current whitelist contains 198 target sources: OBHRM candidates selected from FT50, UTD24, AJG/ABS 2024 `4`/`4*`, ABDC 2025 `A`/`A*`, 9 SJR Q1 HCI journals from `uni.ubicomp.net/hci/`, plus SSRN and NBER.

## Safety Boundary

The project does not automate institutional login, bypass paywalls, solve CAPTCHAs, bypass anti-bot checks, or download PDFs. Reports keep per-article access information to DOI URLs. Readers use their own authorized university access manually if they want full text.

## What The Skill Produces

- Markdown weekly literature report.
- CSV record table with stable field order.
- Standalone HTML report suitable for static hosting.
- Optional short Lark webhook summary containing only concepts, time window, and journal/platform counts.

Per-article report fields are:

```text
title
journal
publication date
doi url
authors
affiliations
abstract status
abstract
keywords
matched concepts
```

## Setup

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Use `.env.example` as a template for local environment variables. Never commit `.env`, `config/monitor.yaml`, outputs, logs, or Lark webhook secrets.

## Build Or Refresh The Whitelist

The repository includes the generated whitelist files:

```text
data/whitelist/journals.csv
data/whitelist/journals_review.md
```

The original ABDC workbook is not committed to this repository. To rebuild the whitelist from a local copy of the ABDC JQL workbook, pass its path explicitly:

```powershell
python skills/obhrm-literature-monitor/scripts/build_whitelist.py --abdc-file "C:\path\to\ABDC-JQL-2025-v1-260326.xlsx"
```

Review `data/whitelist/journals_review.md` before using a newly rebuilt whitelist for production monitoring.

## Run A Weekly Scan

Copy and edit the example monitor config if needed:

```powershell
Copy-Item config/monitor.example.yaml config/monitor.yaml
```

Run the previous full Tokyo-time week:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --previous-week
```

Run a specific Tokyo-time window:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --start 2026-05-18T00:00 --end 2026-05-25T00:00 --keywords "AI; LLM; Large Language Model"
```

Render the Markdown report as standalone HTML:

```powershell
python skills/obhrm-literature-monitor/scripts/render_report_html.py --input outputs/<run-folder>/obhrm_daily_report.md
```

Publish a rendered HTML report into the static Netlify site directory:

```powershell
python skills/obhrm-literature-monitor/scripts/publish_report_site.py --input outputs/<run-folder>/obhrm_daily_report.html
```

The published report will be available under:

```text
site/reports/<run-folder>/
```

The public site copy removes email addresses found in article metadata. Local Markdown/CSV/HTML outputs remain unchanged.

## Netlify Hosting

This repository includes `netlify.toml`. In Netlify, connect this GitHub repository and use:

```text
Build command: leave empty
Publish directory: site
```

After each weekly report, run `publish_report_site.py`, commit the updated `site/` files, and push to GitHub. Netlify will redeploy the public report link automatically.

## Lark Push

Check local configuration:

```powershell
python skills/obhrm-literature-monitor/scripts/check_config.py
```

Send a test message:

```powershell
python skills/obhrm-literature-monitor/scripts/check_config.py --test-lark
```

Send the short summary after a scan:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --previous-week --push-lark
```

Send the short summary for an already generated CSV and hosted report:

```powershell
python skills/obhrm-literature-monitor/scripts/push_lark_report_summary.py --csv outputs/<run-folder>/obhrm_daily_records.csv --start 2026-05-18T00:00 --end 2026-05-25T00:00 --concepts "AI; LLM; Large Language Model" --public-report-url https://example.netlify.app/reports/<run-folder>/ --public-index-url https://example.netlify.app/
```

The Lark message is intentionally brief. It includes concepts, the Tokyo-time window, and matched article counts by journal/platform. It does not include article titles, DOI lists, local file paths, or the full report text.
