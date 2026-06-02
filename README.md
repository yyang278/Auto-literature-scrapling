# OBHRM Literature Monitor

This repository packages a reusable Codex skill for monitoring new articles from an approved OBHRM/HCI/preprint target-source whitelist.

The current whitelist contains approved OBHRM/HCI/preprint target sources selected from FT50, UTD24, AJG/ABS 2024 `4`/`4*`, ABDC 2025 `A`/`A*`, 9 SJR Q1 HCI journals from `uni.ubicomp.net/hci/`, plus SSRN and NBER. `Operations Research` is excluded from all selectable source lists.

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

The default production scan uses the `openalex-source` strategy. It resolves each whitelist source to an OpenAlex source id, searches each source/concept/window combination, and writes `obhrm_scan_trace.csv` so the traversal can be audited.

Run a specific Tokyo-time window:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --start 2026-05-18T00:00 --end 2026-05-25T00:00 --keywords "AI; LLM; Large Language Model"
```

Choose a narrower source list when broad keywords would produce too many articles:

```text
all-whitelist       all approved OBHRM/HCI/preprint whitelist sources
abs-4-and-4-star    ABS/AJG 2024 4 and 4* sources within the whitelist
abs-4-star          ABS/AJG 2024 4* sources within the whitelist
ft50                FT50 sources within the whitelist
utd24               UTD24 sources within the whitelist
```

Example:

```powershell
python skills/obhrm-literature-monitor/scripts/run_daily_scan.py --journal-list abs-4-star --start 2000-01-01T00:00 --end 2026-06-01T00:00 --keywords "Asia; Asian"
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

## Run From GitHub Web Page

Collaborators do not need Codex, Python, or this repository on their own computers if they use the GitHub Actions workflow.

Important permission rule: most users cannot click `Run workflow` inside another person's repository unless they have sufficient write/collaborator access. For ordinary teacher/student self-service use, fork this repository first and run Actions inside the fork. The workflow publishes that fork's reports to that fork's GitHub Pages site.

1. Fork this GitHub repository into your own GitHub account.
2. Click `Actions`.
3. Choose `Generate OBHRM Literature Report`.
4. Click `Run workflow`.
5. Fill in:
   - `keywords`: semicolon-separated concepts, such as `AI; LLM; Large Language Model`.
   - `start_jst`: Tokyo-time inclusive start, such as `2026-05-18T00:00`.
   - `end_jst`: Tokyo-time exclusive end, such as `2026-05-25T00:00`.
   - `match_mode`: keep `any`.
   - `journal_list`: choose `all-whitelist`, `abs-4-and-4-star`, `abs-4-star`, `ft50`, or `utd24`.
   - `public_site_url`: leave blank unless you maintain a custom Netlify or GitHub Pages domain.
6. Start the workflow and wait for it to finish.

The workflow runs on GitHub-hosted servers. It generates Markdown, CSV, and HTML artifacts, publishes the public HTML copy into `site/reports/<run-folder>/`, commits the updated `site/` directory, and deploys the `site/` directory to GitHub Pages.
It also uploads `obhrm_scan_trace.csv`, which shows source-by-source traversal details: journal/platform name, OpenAlex source id, concept, API total count, fetched count, pages fetched, status, and query URL.

When `public_site_url` is blank, report links are generated from the running repository's GitHub Pages URL:

```text
https://<github-user>.github.io/<repo-name>/
https://<github-user>.github.io/<repo-name>/reports/<run-folder>/
```

If GitHub asks for a Pages source, choose `GitHub Actions` in `Settings` -> `Pages`. The workflow uses GitHub Pages deployment actions, so forks do not need the original Netlify project.

If Lark secrets are configured, the workflow also sends the short Lark summary. Add these repository secrets under GitHub `Settings` -> `Secrets and variables` -> `Actions`:

```text
OBHRM_LARK_WEBHOOK_URL
OBHRM_LARK_WEBHOOK_SECRET
```

The Lark summary includes only concepts, Tokyo-time window, journal/platform counts, and public report links.

## Optional Netlify Hosting

This repository includes `netlify.toml`. Netlify is optional and mainly useful for a central project site. In Netlify, connect a GitHub repository and use:

```text
Build command: leave empty
Publish directory: site
```

After each weekly report, `publish_report_site.py` updates `site/`, and the workflow commits those site files. Netlify will redeploy if it is connected to that repository. Fork users can ignore Netlify and use the GitHub Pages links produced by the workflow.

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
