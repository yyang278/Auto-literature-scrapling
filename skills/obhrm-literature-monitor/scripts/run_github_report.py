"""Run the full GitHub Actions literature-report pipeline."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from run_daily_scan import output_dir_for, parse_local_datetime, safe_label


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent


def concept_slug(keywords: str) -> str:
    first = keywords.split(";")[0].strip() or "keywords"
    return safe_label(re.sub(r"\s+", "-", first.lower())) or "keywords"


def default_label(keywords: str, start: str, end: str) -> str:
    start_date = start.replace(" ", "T").split("T", 1)[0]
    end_date = end.replace(" ", "T").split("T", 1)[0]
    return safe_label(f"github-{concept_slug(keywords)}-{start_date}-to-{end_date}")


def run_command(args: list[str]) -> None:
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=REPO_ROOT, check=True)


def write_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def append_github_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scan, render HTML, publish site, and optionally push Lark.")
    parser.add_argument("--keywords", required=True, help="Semicolon-separated keyword concepts.")
    parser.add_argument("--start", required=True, help="Tokyo-time start datetime, e.g. 2026-05-18T00:00.")
    parser.add_argument("--end", required=True, help="Tokyo-time end datetime, e.g. 2026-05-25T00:00.")
    parser.add_argument("--timezone", default="Asia/Tokyo")
    parser.add_argument("--match-mode", default="any", choices=["any"])
    parser.add_argument("--output-label", help="Optional output folder label.")
    parser.add_argument(
        "--strategy",
        choices=["openalex-source", "openalex-keyword", "crossref-journal"],
        default="openalex-source",
    )
    parser.add_argument("--per-keyword", type=int, default=200)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--public-site-url", default="https://obhrm-literature-monitor.netlify.app")
    parser.add_argument("--push-lark", action="store_true")
    parser.add_argument(
        "--journal-list",
        choices=["all-198", "abs-4-and-4-star", "abs-4-star", "ft50", "utd24"],
        default="all-198",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timezone != "Asia/Tokyo":
        raise ValueError("This monitor currently supports Asia/Tokyo windows only.")

    label = args.output_label or default_label(args.keywords, args.start, args.end)
    start = parse_local_datetime(args.start, args.timezone)
    end = parse_local_datetime(args.end, args.timezone)
    output_dir, _ = output_dir_for(end, label)
    report_md = output_dir / "obhrm_daily_report.md"
    report_html = output_dir / "obhrm_daily_report.html"
    csv_path = output_dir / "obhrm_daily_records.csv"
    report_slug = output_dir.name

    run_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "run_daily_scan.py"),
            "--keywords",
            args.keywords,
            "--start",
            args.start,
            "--end",
            args.end,
            "--output-label",
            label,
            "--strategy",
            args.strategy,
            "--per-keyword",
            str(args.per_keyword),
            "--max-pages",
            str(args.max_pages),
            "--journal-list",
            args.journal_list,
        ]
    )
    run_command([sys.executable, str(SCRIPT_DIR / "render_report_html.py"), "--input", str(report_md)])
    run_command([sys.executable, str(SCRIPT_DIR / "publish_report_site.py"), "--input", str(report_html), "--slug", report_slug])

    public_base = args.public_site_url.rstrip("/")
    public_report_url = f"{public_base}/reports/{quote(report_slug)}/"
    public_index_url = f"{public_base}/"

    if args.push_lark:
        if os.environ.get("OBHRM_LARK_WEBHOOK_URL"):
            run_command(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "push_lark_report_summary.py"),
                    "--csv",
                    str(csv_path),
                    "--start",
                    args.start,
                    "--end",
                    args.end,
                    "--timezone",
                    args.timezone,
                    "--concepts",
                    args.keywords,
                    "--public-report-url",
                    public_report_url,
                    "--public-index-url",
                    public_index_url,
                ]
            )
            lark_status = "sent"
        else:
            lark_status = "skipped: missing OBHRM_LARK_WEBHOOK_URL"
            print(f"Lark push {lark_status}.", flush=True)
    else:
        lark_status = "disabled"

    write_github_output("report_dir", report_slug)
    write_github_output("public_report_url", public_report_url)
    write_github_output("public_index_url", public_index_url)
    append_github_summary(
        [
            "## OBHRM Literature Report",
            "",
            f"- Keywords: {args.keywords}",
            f"- Journal list: {args.journal_list}",
            f"- Window: {start.isoformat()} to {end.isoformat()}",
            f"- Output folder: `{report_slug}`",
            f"- Public report: {public_report_url}",
            f"- Public index: {public_index_url}",
            "- Trace artifact: `obhrm_scan_trace.csv` shows source-by-source OpenAlex traversal.",
            f"- Lark: {lark_status}",
        ]
    )
    print(f"Public report: {public_report_url}")
    print(f"Public index: {public_index_url}")
    print(f"Lark: {lark_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
