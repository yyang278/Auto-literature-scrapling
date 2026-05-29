"""Build the OBHRM top-journal whitelist and human review file.

The script creates two artifacts:
- data/whitelist/journals.csv
- data/whitelist/journals_review.md

It uses the local ABDC workbook as the most reliable local source, adds
FT50/UTD24 seed flags, and attempts to fetch AJG/ABS 2024 from
journalranking.org. If the web fetch is unavailable, it falls back to a compact
OBHRM-relevant AJG seed list so the review workflow can still proceed.
"""

from __future__ import annotations

import argparse
import csv
import re
from io import StringIO
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ABDC = REPO_ROOT / "ABDC-JQL-2025-v1-260326.xlsx"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "whitelist"

FT50_SOURCE_URL = "https://www.ft.com/ft50-journals"
UTD24_SOURCE_URL = (
    "https://jsom.utdallas.edu/the-utd-top-100-business-school-research-rankings/"
    "list-of-journals"
)
AJG_SOURCE_URL = "https://journalranking.org/"
ABDC_SOURCE_NOTE = "ABDC JQL 2025 workbook, sheet 2025 JQL"
HCI_SOURCE_URL = "https://uni.ubicomp.net/hci/"
SSRN_SOURCE_URL = "https://www.ssrn.com/ssrn/"
NBER_SOURCE_URL = "https://www.nber.org/"


FT50_TITLES = [
    "Academy of Management Annals",
    "Academy of Management Journal",
    "Academy of Management Review",
    "Accounting, Organizations and Society",
    "Administrative Science Quarterly",
    "American Economic Review",
    "American Sociological Review",
    "Contemporary Accounting Research",
    "Econometrica",
    "Entrepreneurship Theory and Practice",
    "Harvard Business Review",
    "Human Relations",
    "Human Resource Management",
    "Information Systems Research",
    "Journal of Accounting and Economics",
    "Journal of Accounting Research",
    "Journal of Applied Psychology",
    "Journal of Business Ethics",
    "Journal of Business Venturing",
    "Journal of Consumer Psychology",
    "Journal of Consumer Research",
    "Journal of Finance",
    "Journal of Financial and Quantitative Analysis",
    "Journal of Financial Economics",
    "Journal of International Business Studies",
    "Journal of Management",
    "Journal of Management Information Systems",
    "Journal of Management Studies",
    "Journal of Marketing",
    "Journal of Marketing Research",
    "Journal of Operations Management",
    "Journal of Political Economy",
    "Journal of the Academy of Marketing Science",
    "Management Science",
    "Manufacturing and Service Operations Management",
    "Marketing Science",
    "MIS Quarterly",
    "Operations Research",
    "Organization Science",
    "Organization Studies",
    "Organizational Behavior and Human Decision Processes",
    "Production and Operations Management",
    "Psychological Science",
    "Quarterly Journal of Economics",
    "Research Policy",
    "Review of Accounting Studies",
    "Review of Economic Studies",
    "Review of Finance",
    "Review of Financial Studies",
    "MIT Sloan Management Review",
    "Strategic Entrepreneurship Journal",
    "Strategic Management Journal",
    "The Accounting Review",
]

UTD24_TITLES = [
    "The Accounting Review",
    "Journal of Accounting and Economics",
    "Journal of Accounting Research",
    "Journal of Finance",
    "Journal of Financial Economics",
    "The Review of Financial Studies",
    "Information Systems Research",
    "INFORMS Journal on Computing",
    "MIS Quarterly",
    "Journal of Consumer Research",
    "Journal of Marketing",
    "Journal of Marketing Research",
    "Marketing Science",
    "Management Science",
    "Operations Research",
    "Journal of Operations Management",
    "Manufacturing & Service Operations Management",
    "Production and Operations Management",
    "Academy of Management Journal",
    "Academy of Management Review",
    "Administrative Science Quarterly",
    "Organization Science",
    "Journal of International Business Studies",
    "Strategic Management Journal",
]

HCI_SJR_Q1_TITLES = [
    "ACM Transactions on Computer-Human Interaction",
    "International Journal of Human-Computer Studies",
    "International Journal of Human-Computer Interaction",
    "Human-Computer Interaction",
    "Computers in Human Behavior",
    "ACM Transactions on Human-Robot Interaction",
    "ACM Transactions on Privacy and Security",
    "IEEE Transactions on Human-Machine Systems",
    "IEEE Transactions on Visualization and Computer Graphics",
]

PREPRINT_PLATFORMS = [
    "SSRN",
    "NBER",
]

AJG_OBHRM_SEED = [
    ("1941-6067", "ETHICS-CSR-MAN", "Academy of Management Annals", "4*"),
    ("1948-0989", "ETHICS-CSR-MAN", "Academy of Management Journal", "4*"),
    ("1930-3807", "ETHICS-CSR-MAN", "Academy of Management Review", "4*"),
    ("1930-3815", "ETHICS-CSR-MAN", "Administrative Science Quarterly", "4*"),
    ("1557-1211", "ETHICS-CSR-MAN", "Journal of Management", "4*"),
    ("1748-8583", "HRM&EMP", "Human Resource Management Journal (UK)", "4*"),
    ("1944-9585", "MDEV&EDU", "Academy of Management Learning and Education", "4*"),
    ("1526-5455", "ORG STUD", "Organization Science", "4*"),
    ("1939-1854", "PSYCH (WOP-OB)", "Journal of Applied Psychology", "4*"),
    ("1744-6570", "PSYCH (WOP-OB)", "Personnel Psychology", "4*"),
    ("1097-0266", "STRAT", "Strategic Management Journal", "4*"),
    ("1558-9080", "ETHICS-CSR-MAN", "Academy of Management Perspectives", "4"),
    ("1467-8551", "ETHICS-CSR-MAN", "British Journal of Management", "4"),
    ("1467-6486", "ETHICS-CSR-MAN", "Journal of Management Studies", "4"),
    ("1467-8543", "HRM&EMP", "British Journal of Industrial Relations", "4"),
    ("1099-050X", "HRM&EMP", "Human Resource Management (USA)", "4"),
    ("1468-232X", "HRM&EMP", "Industrial Relations", "4"),
    ("1469-8722", "HRM&EMP", "Work, Employment and Society", "4"),
    ("1741-282X", "ORG STUD", "Human Relations", "4"),
    ("1873-3409", "ORG STUD", "Leadership Quarterly", "4"),
    ("1741-3044", "ORG STUD", "Organization Studies", "4"),
    ("1552-7425", "ORG STUD", "Organizational Research Methods", "4"),
    ("2044-8325", "PSYCH (WOP-OB)", "Journal of Occupational and Organizational Psychology", "4"),
    ("1939-1307", "PSYCH (WOP-OB)", "Journal of Occupational Health Psychology", "4"),
    ("1099-1379", "PSYCH (WOP-OB)", "Journal of Organizational Behavior", "4"),
    ("1095-9084", "PSYCH (WOP-OB)", "Journal of Vocational Behavior", "4"),
    ("1095-9920", "PSYCH (WOP-OB)", "Organizational Behavior and Human Decision Processes", "4"),
    ("1464-5335", "PSYCH (WOP-OB)", "Work and Stress", "4"),
]

OBHRM_FOR_CODES = {"3505", "3507"}
OBHRM_AJG_FIELDS = {"HRM&EMP", "ORG STUD", "PSYCH (WOP-OB)", "MDEV&EDU"}
TITLE_KEYWORDS = [
    "academy of management",
    "administrative science",
    "applied psychology",
    "employment",
    "human resource",
    "human relations",
    "industrial relations",
    "leadership",
    "organization",
    "organisational",
    "organizational",
    "personnel",
    "work",
]
MANUAL_INCLUDE_TITLES = {
    "academy of management annals",
    "academy of management discoveries",
    "academy of management journal",
    "academy of management learning and education",
    "academy of management perspectives",
    "academy of management review",
    "administrative science quarterly",
    "annual review of organizational psychology and organizational behavior",
    "applied psychology: an international review",
    "british journal of industrial relations",
    "british journal of management",
    "european journal of work and organizational psychology",
    "group & organization management",
    "human relations",
    "human resource management",
    "human resource management (us)",
    "human resource management journal (uk)",
    "human resource management review",
    "ilr review",
    "ilr review (industrial and labor relations review)",
    "industrial relations",
    "industrial relations: a journal of economy and society",
    "international journal of human resource management",
    "international journal of management reviews",
    "journal of applied psychology",
    "journal of management",
    "journal of management studies",
    "journal of occupational and organizational psychology",
    "journal of occupational health psychology",
    "journal of organizational behavior",
    "journal of vocational behavior",
    "leadership quarterly",
    "organization science",
    "organization studies",
    "organizational behavior and human decision processes",
    "organizational research methods",
    "personnel psychology",
    "work and stress",
    "work, employment and society",
}
MANUAL_EXCLUDE_KEYWORDS = [
    "accounting",
    "finance",
    "marketing",
    "operations",
    "supply chain",
    "tourism",
    "hospitality",
    "sport management",
    "construction",
    "retail",
]


@dataclass
class JournalRecord:
    title: str
    normalized_title: str
    issn: str = ""
    eissn: str = ""
    publisher: str = ""
    abdc_rating: str = ""
    abdc_for: str = ""
    ajg2024: str = ""
    ajg_field: str = ""
    in_ft50: bool = False
    in_utd24: bool = False
    in_hci_sjr_q1: bool = False
    is_preprint_platform: bool = False
    sources: set[str] = field(default_factory=set)


def normalize_title(title: str) -> str:
    value = str(title or "").lower()
    value = value.replace("&", "and")
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\bthe\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_key(title: str) -> str:
    normalized = normalize_title(title)
    aliases = {
        "human resource management usa": "human resource management",
        "human resource management us": "human resource management",
        "human resource management journal uk": "human resource management journal",
        "industrial relations a journal of economy and society": "industrial relations",
        "mis quarterly management information systems": "mis quarterly",
        "m s om manufacturing service operations management": "manufacturing service operations management",
        "manufacturing and service operations management": "manufacturing service operations management",
        "review of financial studies": "review of financial studies",
        "sloan management review": "mit sloan management review",
    }
    return aliases.get(normalized, normalized)


def clean_issn(value: object) -> str:
    text = str(value or "").upper().strip()
    if text in {"", "NAN", "NONE"}:
        return ""
    text = re.sub(r"[^0-9X]", "", text)
    if len(text) != 8:
        return ""
    return f"{text[:4]}-{text[4:]}"


def add_or_update(records: dict[str, JournalRecord], title: str, **updates: object) -> None:
    key = title_key(title)
    if not key:
        return
    record = records.get(key)
    if record is None:
        record = JournalRecord(title=str(title).strip(), normalized_title=key)
        records[key] = record

    for field_name in ["issn", "eissn", "publisher", "abdc_rating", "abdc_for", "ajg2024", "ajg_field"]:
        value = str(updates.get(field_name, "") or "").strip()
        if value and not getattr(record, field_name):
            setattr(record, field_name, value)

    if updates.get("in_ft50"):
        record.in_ft50 = True
    if updates.get("in_utd24"):
        record.in_utd24 = True
    if updates.get("in_hci_sjr_q1"):
        record.in_hci_sjr_q1 = True
    if updates.get("is_preprint_platform"):
        record.is_preprint_platform = True

    source = updates.get("source")
    if source:
        record.sources.add(str(source))


def load_abdc(records: dict[str, JournalRecord], path: Path) -> tuple[int, int]:
    df = pd.read_excel(path, sheet_name="2025 JQL", header=7)
    df["rating_clean"] = df["2025 rating"].astype(str).str.strip()
    selected = df[df["rating_clean"].isin(["A", "A*"])].copy()
    for _, row in selected.iterrows():
        add_or_update(
            records,
            row["Journal Title"],
            issn=clean_issn(row.get("ISSN")),
            eissn=clean_issn(row.get("ISSNOnline")),
            publisher=str(row.get("Publisher", "") or "").strip(),
            abdc_rating=row["rating_clean"],
            abdc_for=str(row.get("FoR", "") or "").strip(),
            source=f"ABDC_{row['rating_clean']}",
        )
    return len(df), len(selected)


def load_seed_lists(records: dict[str, JournalRecord]) -> None:
    for title in FT50_TITLES:
        add_or_update(records, title, in_ft50=True, source="FT50_seed")
    for title in UTD24_TITLES:
        add_or_update(records, title, in_utd24=True, source="UTD24_seed")
    for title in HCI_SJR_Q1_TITLES:
        add_or_update(records, title, in_hci_sjr_q1=True, source="HCI_SJR_Q1")
    for title in PREPRINT_PLATFORMS:
        add_or_update(records, title, is_preprint_platform=True, source="PREPRINT_PLATFORM")


def load_ajg_from_web(records: dict[str, JournalRecord]) -> int:
    import urllib.request

    request = urllib.request.Request(
        AJG_SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0 OBHRM literature monitor"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    tables = pd.read_html(StringIO(html))
    if not tables:
        return 0
    df = max(tables, key=len)
    lower_cols = {str(col).strip().lower(): col for col in df.columns}
    required = ["issn", "field", "title", "publisher", "ajg2024"]
    if not all(col in lower_cols for col in required):
        return 0

    count = 0
    for _, row in df.iterrows():
        rating = str(row[lower_cols["ajg2024"]] or "").strip()
        if rating not in {"4", "4*"}:
            continue
        title = str(row[lower_cols["title"]] or "").strip()
        if not title or title.lower() == "nan":
            continue
        add_or_update(
            records,
            title,
            issn=clean_issn(row[lower_cols["issn"]]),
            publisher=str(row[lower_cols["publisher"]] or "").strip(),
            ajg2024=rating,
            ajg_field=str(row[lower_cols["field"]] or "").strip(),
            source=f"AJG2024_{rating}",
        )
        count += 1
    return count


def load_ajg_seed(records: dict[str, JournalRecord]) -> int:
    for issn, field_name, title, rating in AJG_OBHRM_SEED:
        add_or_update(
            records,
            title,
            issn=clean_issn(issn),
            ajg2024=rating,
            ajg_field=field_name,
            source=f"AJG2024_{rating}_seed",
        )
    return len(AJG_OBHRM_SEED)


def candidate_reason(record: JournalRecord) -> tuple[bool, str, str]:
    title_norm = normalize_title(record.title)
    reasons: list[str] = []
    status = "needs_review"
    strong_signal = False

    if title_norm in MANUAL_INCLUDE_TITLES or record.normalized_title in MANUAL_INCLUDE_TITLES:
        reasons.append("manual core OBHRM title")
        strong_signal = True

    for code in OBHRM_FOR_CODES:
        if code and code in str(record.abdc_for):
            reasons.append(f"ABDC FoR {code}")

    if record.ajg_field in OBHRM_AJG_FIELDS:
        reasons.append(f"AJG field {record.ajg_field}")
        strong_signal = True

    for keyword in TITLE_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, title_norm):
            reasons.append(f"title keyword '{keyword}'")
            strong_signal = True
            break

    if (record.in_ft50 or record.in_utd24) and any(
        marker in title_norm
        for marker in [
            "academy of management",
            "administrative science",
            "organization science",
            "strategic management",
            "journal of international business studies",
        ]
    ):
        reasons.append("FT50/UTD management-general journal")
        strong_signal = True

    if record.in_hci_sjr_q1:
        reasons.append("HCI selected journal with SJR Q1")
        strong_signal = True

    if record.is_preprint_platform:
        reasons.append("approved preprint platform")
        strong_signal = True

    if not reasons:
        return False, "", "excluded_by_scope"

    if strong_signal:
        status = "include_candidate"

    if any(keyword in title_norm for keyword in MANUAL_EXCLUDE_KEYWORDS) and title_norm not in MANUAL_INCLUDE_TITLES:
        status = "needs_review"
        reasons.append("broad-management/noise keyword needs human check")

    return True, "; ".join(dict.fromkeys(reasons)), status


def source_lists(record: JournalRecord) -> str:
    values = []
    if record.in_ft50:
        values.append("FT50")
    if record.in_utd24:
        values.append("UTD24")
    if record.ajg2024:
        values.append(f"AJG2024_{record.ajg2024}")
    if record.abdc_rating:
        values.append(f"ABDC_{record.abdc_rating}")
    if record.in_hci_sjr_q1:
        values.append("HCI_SJR_Q1")
    if record.is_preprint_platform:
        values.append("PREPRINT_PLATFORM")
    return ";".join(values)


def write_csv(records: Iterable[JournalRecord], output: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in sorted(records, key=lambda item: item.title.lower()):
        candidate, reason, status = candidate_reason(record)
        rows.append(
            {
                "journal_title": record.title,
                "normalized_title": record.normalized_title,
                "issn": record.issn,
                "eissn": record.eissn,
                "publisher": record.publisher,
                "abdc_rating": record.abdc_rating,
                "abdc_for": record.abdc_for,
                "ajg2024": record.ajg2024,
                "ajg_field": record.ajg_field,
                "in_ft50": str(record.in_ft50),
                "in_utd24": str(record.in_utd24),
                "in_hci_sjr_q1": str(record.in_hci_sjr_q1),
                "is_preprint_platform": str(record.is_preprint_platform),
                "source_lists": source_lists(record),
                "obhrm_candidate": str(candidate),
                "inclusion_reason": reason,
                "review_status": status,
            }
        )

    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def markdown_table(rows: list[dict[str, str]], limit: int | None = None) -> str:
    selected = rows if limit is None else rows[:limit]
    lines = [
        "| # | Journal | Sources | ABDC | AJG | FoR/Field | Review | Reason |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for index, row in enumerate(selected, 1):
        field = row["abdc_for"] or row["ajg_field"]
        lines.append(
            f"| {index} | {row['journal_title']} | {row['source_lists']} | "
            f"{row['abdc_rating']} | {row['ajg2024']} | {field} | "
            f"{row['review_status']} | {row['inclusion_reason']} |"
        )
    return "\n".join(lines)


def write_review(rows: list[dict[str, str]], output: Path, stats: dict[str, object]) -> None:
    candidates = [row for row in rows if row["obhrm_candidate"] == "True"]
    include_candidates = [row for row in candidates if row["review_status"] == "include_candidate"]
    needs_review = [row for row in candidates if row["review_status"] == "needs_review"]

    content = f"""# OBHRM Journal Whitelist Review

Generated: {datetime.now().isoformat(timespec="seconds")}

## Summary

- Total top-list journals collected: {len(rows)}
- OBHRM candidate journals: {len(candidates)}
- Include candidates: {len(include_candidates)}
- Needs human review: {len(needs_review)}
- ABDC rows read: {stats['abdc_rows_read']}
- ABDC A/A* rows kept: {stats['abdc_rows_kept']}
- AJG 2024 rows added: {stats['ajg_rows_added']} ({stats['ajg_mode']})

## Sources

- FT50 seed list, source URL: {FT50_SOURCE_URL}
- UTD24 seed list, source URL: {UTD24_SOURCE_URL}
- AJG/ABS 2024, source URL: {AJG_SOURCE_URL}
- {ABDC_SOURCE_NOTE}
- HCI selected journals with SJR Q1, source URL: {HCI_SOURCE_URL}
- SSRN preprint platform, source URL: {SSRN_SOURCE_URL}
- NBER working papers/preprint platform, source URL: {NBER_SOURCE_URL}

## Review Instructions

Please review the candidate journals below before we run article scanning. Mark any journal that should be removed from the OBHRM scope, and point out any missing OBHRM journal you expect to see.

The script intentionally errs on the side of inclusion for management-general journals. Rows marked `needs_review` are plausible but more likely to include noise.

## Include Candidates

{markdown_table(include_candidates)}

## Needs Human Review

{markdown_table(needs_review) if needs_review else "No rows."}
"""
    output.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build OBHRM top-journal whitelist.")
    parser.add_argument("--abdc-file", type=Path, default=DEFAULT_ABDC)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-ajg-web", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.abdc_file.exists():
        raise FileNotFoundError(f"ABDC workbook not found: {args.abdc_file}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records: dict[str, JournalRecord] = {}

    abdc_rows_read, abdc_rows_kept = load_abdc(records, args.abdc_file)
    load_seed_lists(records)

    ajg_mode = "web"
    try:
        ajg_rows_added = 0 if args.skip_ajg_web else load_ajg_from_web(records)
        if ajg_rows_added == 0:
            ajg_mode = "seed"
            ajg_rows_added = load_ajg_seed(records)
    except Exception as exc:  # noqa: BLE001 - keep whitelist build resilient.
        ajg_mode = f"seed after web error: {exc.__class__.__name__}"
        ajg_rows_added = load_ajg_seed(records)

    rows = write_csv(records.values(), args.output_dir / "journals.csv")
    write_review(
        rows,
        args.output_dir / "journals_review.md",
        {
            "abdc_rows_read": abdc_rows_read,
            "abdc_rows_kept": abdc_rows_kept,
            "ajg_rows_added": ajg_rows_added,
            "ajg_mode": ajg_mode,
        },
    )

    candidates = sum(row["obhrm_candidate"] == "True" for row in rows)
    print(f"Wrote {args.output_dir / 'journals.csv'} ({len(rows)} rows)")
    print(f"Wrote {args.output_dir / 'journals_review.md'} ({candidates} OBHRM candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
