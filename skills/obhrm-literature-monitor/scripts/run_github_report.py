"""Run the full GitHub Actions literature-report pipeline."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from run_daily_scan import JOURNAL_LISTS, normalize_journal_list_names, output_dir_for, parse_local_datetime, safe_label


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
TIMEZONE_CHOICES = ["Asia/Tokyo", "America/Chicago", "Asia/Shanghai"]


def split_legacy_keywords(keywords: str | None) -> list[str]:
    if not keywords:
        return []
    return [item.strip() for item in re.split(r"[;\n]", keywords) if item.strip()]


def normalized_keywords(keyword_lines: list[str] | None, legacy_keywords: str | None) -> list[str]:
    concepts = [item.strip() for item in keyword_lines or [] if item.strip()]
    if not concepts:
        concepts = split_legacy_keywords(legacy_keywords)
    if not concepts:
        raise ValueError("At least one keyword is required.")
    if len(concepts) > 5:
        raise ValueError("At most 5 keyword concepts are supported.")
    return concepts


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


def run_actor() -> str:
    return (
        os.environ.get("GITHUB_TRIGGERING_ACTOR")
        or os.environ.get("GITHUB_ACTOR")
        or os.environ.get("USERNAME")
        or os.environ.get("USER")
        or "local"
    )


def run_started_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scan, render HTML, publish site, and optionally push Lark.")
    parser.add_argument("--keyword", action="append", default=[], help="One keyword concept. Repeat up to 5 times.")
    parser.add_argument("--keywords", help="Legacy semicolon-separated keyword concepts.")
    parser.add_argument("--start", required=True, help="Local start datetime, e.g. 2026-05-18T00:00.")
    parser.add_argument("--end", required=True, help="Local end datetime, e.g. 2026-05-25T00:00.")
    parser.add_argument("--timezone", default="Asia/Tokyo", choices=TIMEZONE_CHOICES)
    parser.add_argument("--match-mode", default="any", choices=["any", "all"])
    parser.add_argument("--output-label", help="Optional output folder label.")
    parser.add_argument(
        "--strategy",
        choices=["openalex-source", "openalex-keyword", "crossref-journal"],
        default="openalex-source",
    )
    parser.add_argument("--per-keyword", type=int, default=200)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Optional OpenAlex page cap per query. 0 means exhaustive cursor paging.",
    )
    parser.add_argument("--public-site-url", default="")
    parser.add_argument("--push-lark", action="store_true")
    parser.add_argument(
        "--journal-list",
        action="append",
        choices=list(JOURNAL_LISTS),
        help="Named source subset to scan. Repeat to scan the union of multiple lists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    actor = run_actor()
    started_at = run_started_at()
    concepts = normalized_keywords(args.keyword, args.keywords)
    keyword_text = "; ".join(concepts)
    journal_lists = normalize_journal_list_names(args.journal_list)

    label = args.output_label or default_label(keyword_text, args.start, args.end)
    start = parse_local_datetime(args.start, args.timezone)
    end = parse_local_datetime(args.end, args.timezone)
    if end <= start:
        raise ValueError(
            "Invalid time window: end must be later than start. "
            f"Got start={start.isoformat()} and end={end.isoformat()}."
        )
    output_dir, _ = output_dir_for(end, label)
    report_md = output_dir / "obhrm_daily_report.md"
    report_html = output_dir / "obhrm_daily_report.html"
    csv_path = output_dir / "obhrm_daily_records.csv"
    report_slug = output_dir.name

    scan_args = [
            sys.executable,
            str(SCRIPT_DIR / "run_daily_scan.py"),
            "--start",
            args.start,
            "--end",
            args.end,
            "--timezone",
            args.timezone,
            "--match-mode",
            args.match_mode,
            "--output-label",
            label,
            "--strategy",
            args.strategy,
            "--per-keyword",
            str(args.per_keyword),
            "--max-pages",
            str(args.max_pages),
    ]
    for journal_list in journal_lists:
        scan_args.extend(["--journal-list", journal_list])
    for concept in concepts:
        scan_args.extend(["--keyword", concept])
    run_command(scan_args)
    run_command([sys.executable, str(SCRIPT_DIR / "render_report_html.py"), "--input", str(report_md)])
    run_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "publish_report_site.py"),
            "--input",
            str(report_html),
            "--slug",
            report_slug,
            "--run-actor",
            actor,
            "--run-started-at",
            started_at,
        ]
    )

    public_base = (
        args.public_site_url
        or os.environ.get("OBHRM_PUBLIC_SITE_URL")
        or "https://obhrm-literature-monitor.netlify.app"
    ).rstrip("/")
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
                    keyword_text,
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
            f"- Keywords: {keyword_text}",
            f"- Match mode: {args.match_mode}",
            f"- Journal lists: {'; '.join(journal_lists)}",
            f"- Timezone: {args.timezone}",
            f"- Window: {start.isoformat()} to {end.isoformat()}",
            f"- Run actor: {actor}",
            f"- Run started: {started_at}",
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
