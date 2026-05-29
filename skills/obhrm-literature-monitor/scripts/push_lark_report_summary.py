"""Push a short Lark summary for an existing literature report CSV."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from run_daily_scan import csv_value, format_lark_summary, load_dotenv, parse_local_datetime, send_lark


REPO_ROOT = Path(__file__).resolve().parents[3]


def concepts_from_rows(rows: list[dict[str, str]]) -> list[str]:
    concepts: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for concept in row.get("matched_concepts", "").split(";"):
            value = concept.strip()
            key = value.lower()
            if value and key not in seen:
                seen.add(key)
                concepts.append(value)
    return concepts


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push Lark summary for an existing report CSV.")
    parser.add_argument("--csv", type=Path, required=True, help="Existing obhrm_daily_records.csv path.")
    parser.add_argument("--start", required=True, help="Tokyo-time start datetime, e.g. 2026-05-18T00:00.")
    parser.add_argument("--end", required=True, help="Tokyo-time end datetime, e.g. 2026-05-25T00:00.")
    parser.add_argument("--timezone", default="Asia/Tokyo")
    parser.add_argument("--concepts", help="Optional semicolon-separated concept list.")
    parser.add_argument("--public-report-url", required=True)
    parser.add_argument("--public-index-url", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv()
    rows = read_rows(args.csv)
    concepts = (
        [part.strip() for part in args.concepts.split(";") if part.strip()]
        if args.concepts
        else concepts_from_rows(rows)
    )
    journal_counts = Counter(row.get("journal", "").strip() or "Unknown journal" for row in rows)
    start = parse_local_datetime(args.start, args.timezone)
    end = parse_local_datetime(args.end, args.timezone)
    text = format_lark_summary(
        journal_counts=journal_counts,
        concepts=concepts,
        start=start,
        end=end,
        public_report_url=args.public_report_url,
        public_index_url=args.public_index_url,
    )
    if args.dry_run:
        print(text)
        return 0
    send_lark(text)
    print(f"Lark summary sent for {len(rows)} articles and {len(journal_counts)} journals.")
    print(f"Concepts: {csv_value(concepts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
