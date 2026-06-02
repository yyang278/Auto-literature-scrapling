"""Run an OBHRM top-journal article scan and generate Markdown/CSV reports."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from html import unescape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[3]
WHITELIST_CSV = REPO_ROOT / "data" / "whitelist" / "journals.csv"
MONITOR_CONFIG = REPO_ROOT / "config" / "monitor.yaml"
MONITOR_EXAMPLE = REPO_ROOT / "config" / "monitor.example.yaml"
OUTPUT_ROOT = REPO_ROOT / "outputs"
LOG_ROOT = REPO_ROOT / "logs"

CROSSREF_API = "https://api.crossref.org/v1"
OPENALEX_API = "https://api.openalex.org"

EXCLUDED_JOURNAL_TITLES = {"operations research"}

JOURNAL_LISTS: dict[str, dict[str, Any]] = {
    "all-whitelist": {
        "label": "All approved OBHRM/HCI/preprint whitelist sources",
        "tokens": set(),
    },
    "abs-4-and-4-star": {
        "label": "ABS/AJG 2024 4 and 4* sources within the whitelist",
        "tokens": {"AJG2024_4", "AJG2024_4*"},
    },
    "abs-4-star": {
        "label": "ABS/AJG 2024 4* sources within the whitelist",
        "tokens": {"AJG2024_4*"},
    },
    "ft50": {
        "label": "FT50 sources within the whitelist",
        "tokens": {"FT50"},
    },
    "utd24": {
        "label": "UTD24 sources within the whitelist",
        "tokens": {"UTD24"},
    },
}


@dataclass
class Journal:
    title: str
    issns: list[str]
    source_lists: str


@dataclass
class OpenAlexSource:
    id: str
    display_name: str
    resolution_method: str


@dataclass
class Article:
    title: str = ""
    journal: str = ""
    doi: str = ""
    publication_date: str = ""
    publication_date_source: str = ""
    publisher: str = ""
    publisher_url: str = ""
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    author_affiliations: list[tuple[str, str]] = field(default_factory=list)
    matched_concepts: list[str] = field(default_factory=list)
    matched_fields: list[str] = field(default_factory=list)
    source: str = ""
    crossref_url: str = ""
    openalex_url: str = ""
    abstract_status: str = "missing"

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else ""

def normalize_title(title: str) -> str:
    value = str(title or "").lower()
    value = value.replace("&", "and")
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\bthe\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip().lstrip("\ufeff"), value.strip().strip('"').strip("'"))


def simple_yaml_config(path: Path) -> dict[str, Any]:
    """Load the small monitor YAML shape without requiring PyYAML."""
    text = path.read_text(encoding="utf-8")
    config: dict[str, Any] = {
        "timezone": "Asia/Tokyo",
        "outputs": {
            "root": "outputs",
            "report_name": "obhrm_daily_report.md",
            "csv_name": "obhrm_daily_records.csv",
        },
        "push": {"lark_enabled": False},
        "keyword_groups": {
            "active": {"name": "active", "match_mode": "any", "concepts": []}
        },
    }
    active = config["keyword_groups"]["active"]
    section: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0 and stripped.endswith(":"):
            section = [stripped[:-1]]
            continue
        if indent == 2 and stripped.endswith(":"):
            section = [section[0], stripped[:-1]] if section else [stripped[:-1]]
            continue
        if stripped.startswith("- ") and section[-2:] == ["active", "concepts"]:
            active["concepts"].append(stripped[2:].strip().strip('"'))
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            value = value.strip().strip('"')
            if key == "timezone":
                config["timezone"] = value
            elif key == "name" and "active" in section:
                active["name"] = value
            elif key == "match_mode" and "active" in section:
                active["match_mode"] = value
            elif key in {"lark_enabled"}:
                config["push"][key] = value.lower() == "true"
            elif key in {"root", "report_name", "csv_name"} and "outputs" in section:
                config["outputs"][key] = value
    return config


def load_config() -> dict[str, Any]:
    path = MONITOR_CONFIG if MONITOR_CONFIG.exists() else MONITOR_EXAMPLE
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass
    return simple_yaml_config(path)


def parse_keywords(
    config: dict[str, Any],
    cli_keywords: str | None,
    cli_keyword_lines: list[str] | None = None,
    cli_match_mode: str | None = None,
) -> tuple[str, str, list[str]]:
    active = config.get("keyword_groups", {}).get("active", {})
    name = str(active.get("name", "active"))
    mode = str(active.get("match_mode", "any")).lower()
    concepts = active.get("concepts", [])
    if cli_match_mode:
        mode = cli_match_mode.lower()
    if cli_keywords:
        name = "cli-keywords"
        concepts = re.split(r"[;\n]", cli_keywords)
    if cli_keyword_lines:
        name = "cli-keywords"
        concepts = cli_keyword_lines
    cleaned = [str(item).strip() for item in concepts if str(item).strip()]
    if not cleaned:
        raise ValueError("No keywords configured. Add concepts to config/monitor.yaml or pass --keyword/--keywords.")
    if len(cleaned) > 5:
        raise ValueError("At most 5 keyword concepts are supported for the GitHub Actions workflow.")
    if mode not in {"any", "all"}:
        raise ValueError("match_mode must be either 'any' or 'all'.")
    return name, mode, cleaned


def parse_local_datetime(value: str, timezone: str) -> datetime:
    if "T" not in value and " " not in value:
        value = f"{value}T00:00"
    normalized = value.replace(" ", "T")
    return datetime.fromisoformat(normalized).replace(tzinfo=ZoneInfo(timezone))


def validate_window(start: datetime, end: datetime) -> None:
    if end <= start:
        raise ValueError(
            "Invalid time window: end must be later than start. "
            f"Got start={start.isoformat()} and end={end.isoformat()}."
        )


def default_window(timezone: str) -> tuple[datetime, datetime]:
    now = datetime.now(ZoneInfo(timezone))
    end = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < end:
        end -= timedelta(days=1)
    start = end - timedelta(days=1)
    return start, end


def trial_window(timezone: str) -> tuple[datetime, datetime]:
    return (
        parse_local_datetime("2026-05-25T08:00", timezone),
        parse_local_datetime("2026-05-26T08:00", timezone),
    )


def previous_week_window(timezone: str, reference: datetime | None = None) -> tuple[datetime, datetime]:
    now = reference or datetime.now(ZoneInfo(timezone))
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    this_monday = today_midnight - timedelta(days=today_midnight.weekday())
    previous_monday = this_monday - timedelta(days=7)
    return previous_monday, this_monday


def journal_list_options() -> str:
    return ", ".join(JOURNAL_LISTS)


def journal_matches_list(source_lists: str, journal_list: str) -> bool:
    if journal_list not in JOURNAL_LISTS:
        raise ValueError(f"Unknown journal list {journal_list!r}. Available: {journal_list_options()}")
    tokens = JOURNAL_LISTS[journal_list]["tokens"]
    if not tokens:
        return True
    source_tokens = {part.strip() for part in str(source_lists or "").split(";") if part.strip()}
    return bool(source_tokens & tokens)


def journal_is_excluded(title: str, journal_list: str) -> bool:
    return normalize_title(title) in EXCLUDED_JOURNAL_TITLES


def load_journals(path: Path, journal_list: str = "all-whitelist") -> list[Journal]:
    journals: list[Journal] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("obhrm_candidate") != "True":
                continue
            if journal_is_excluded(row.get("journal_title", ""), journal_list):
                continue
            if not journal_matches_list(row.get("source_lists", ""), journal_list):
                continue
            issns = []
            for field_name in ["issn", "eissn"]:
                value = (row.get(field_name) or "").strip()
                if value and value not in issns:
                    issns.append(value)
            journals.append(
                Journal(
                    title=row.get("journal_title", "").strip(),
                    issns=issns,
                    source_lists=row.get("source_lists", "").strip(),
                )
            )
    return journals


def http_json(url: str, params: dict[str, str] | None = None, timeout: int = 40) -> dict[str, Any]:
    full_url = url
    if params:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        full_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "OBHRM-literature-monitor/0.1 (mailto optional)",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_url(url: str, params: dict[str, str]) -> str:
    return f"{url}?{urllib.parse.urlencode(params)}"


def date_parts_to_date(value: Any) -> str:
    try:
        parts = value["date-parts"][0]
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day).isoformat()
    except Exception:
        return ""


def clean_abstract(text: str) -> str:
    text = re.sub(r"</?jats:[^>]+>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def add_unique(values: list[str], value: str) -> None:
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if value and value not in values:
        values.append(value)


def format_author_affiliations(pairs: list[tuple[str, str]]) -> str:
    rows = []
    for author, affiliation in pairs:
        author_value = re.sub(r"\s+", " ", str(author or "")).strip() or "not available"
        affiliation_value = re.sub(r"\s+", " ", str(affiliation or "")).strip() or "not available"
        rows.append(f"{author_value} :: {affiliation_value}")
    return " ~~ ".join(rows)


def crossref_authors(item: dict[str, Any]) -> tuple[list[str], list[str], list[tuple[str, str]]]:
    authors: list[str] = []
    affiliations: list[str] = []
    author_affiliations: list[tuple[str, str]] = []
    for author in item.get("author", []) or []:
        name = " ".join(
            part
            for part in [
                author.get("given", ""),
                author.get("family", ""),
            ]
            if part
        ).strip()
        if name:
            authors.append(name)
        author_affs: list[str] = []
        for aff in author.get("affiliation", []) or []:
            aff_name = aff.get("name")
            if aff_name:
                add_unique(author_affs, aff_name)
                add_unique(affiliations, aff_name)
        if name:
            author_affiliations.append((name, csv_value(author_affs) if author_affs else "not available"))
    return authors, affiliations, author_affiliations


def crossref_enrich_by_doi(article: Article) -> None:
    if not article.doi:
        return
    url = f"{CROSSREF_API}/works/{urllib.parse.quote(article.doi)}"
    try:
        data = http_json(url)
    except Exception:
        return
    item = data.get("message") or {}
    if not article.abstract and item.get("abstract"):
        article.abstract = clean_abstract(str(item.get("abstract", "") or ""))
        if article.abstract:
            article.abstract_status = "available"
    if not article.publisher_url:
        article.publisher_url = str(item.get("URL", "") or "")
    if not article.publisher:
        article.publisher = str(item.get("publisher", "") or "")
    for subject in item.get("subject", []) or []:
        value = str(subject)
        if value and value not in article.keywords:
            article.keywords.append(value)
    if not article.authors or not article.affiliations or not article.author_affiliations:
        authors, affiliations, author_affiliations = crossref_authors(item)
        article.authors = article.authors or authors
        for affiliation in affiliations:
            if affiliation not in article.affiliations:
                article.affiliations.append(affiliation)
        if not article.author_affiliations:
            article.author_affiliations = author_affiliations
    article.crossref_url = url


def article_from_crossref(item: dict[str, Any], journal_hint: str, source_url: str) -> Article:
    title = " ".join(item.get("title") or []).strip()
    container = " ".join(item.get("container-title") or []).strip() or journal_hint
    doi = str(item.get("DOI", "") or "").lower().strip()
    abstract = clean_abstract(str(item.get("abstract", "") or ""))
    authors, affiliations, author_affiliations = crossref_authors(item)
    publication_date = ""
    publication_source = ""
    for key in ["published-online", "published-print", "published", "issued", "created"]:
        publication_date = date_parts_to_date(item.get(key))
        if publication_date:
            publication_source = key
            break
    subjects = [str(value) for value in item.get("subject", []) or []]
    url = str(item.get("URL", "") or "")
    return Article(
        title=title,
        journal=container,
        doi=doi,
        publication_date=publication_date,
        publication_date_source=publication_source,
        publisher=str(item.get("publisher", "") or ""),
        publisher_url=url,
        abstract=abstract,
        keywords=subjects,
        authors=authors,
        affiliations=affiliations,
        author_affiliations=author_affiliations,
        source="Crossref",
        crossref_url=source_url,
        abstract_status="available" if abstract else "missing",
    )


def reconstruct_openalex_abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, word_positions in index.items():
        for position in word_positions:
            positions.append((position, word))
    return " ".join(word for _, word in sorted(positions)).strip()


def openalex_authors_and_affiliations(data: dict[str, Any]) -> tuple[list[str], list[str], list[tuple[str, str]]]:
    authors: list[str] = []
    affiliations: set[str] = set()
    author_affiliations: list[tuple[str, str]] = []
    for authorship in data.get("authorships", []) or []:
        author_name = (authorship.get("author") or {}).get("display_name")
        if author_name:
            authors.append(author_name)
        author_affs: list[str] = []
        for inst in authorship.get("institutions", []) or []:
            name = inst.get("display_name")
            if name:
                affiliations.add(name)
                add_unique(author_affs, name)
        for raw in authorship.get("raw_affiliation_strings", []) or []:
            if raw:
                affiliations.add(raw)
                add_unique(author_affs, raw)
        if author_name:
            author_affiliations.append(
                (author_name, csv_value(author_affs) if author_affs else "not available")
            )
    return authors, sorted(affiliations), author_affiliations


def openalex_keywords(data: dict[str, Any]) -> list[str]:
    values: list[str] = []
    primary_topic = data.get("primary_topic") or {}
    if primary_topic.get("display_name"):
        values.append(primary_topic["display_name"])
    for topic in data.get("topics", []) or []:
        name = topic.get("display_name")
        if name and name not in values:
            values.append(name)
    for concept in data.get("concepts", []) or []:
        name = concept.get("display_name")
        if name and name not in values:
            values.append(name)
    return values


def openalex_source(data: dict[str, Any]) -> tuple[str, list[str], str]:
    locations = []
    if data.get("primary_location"):
        locations.append(data["primary_location"])
    locations.extend(data.get("locations", []) or [])
    for location in locations:
        source = (location or {}).get("source") or {}
        if not source:
            continue
        name = source.get("display_name") or ""
        issns = []
        if source.get("issn_l"):
            issns.append(source["issn_l"])
        for issn in source.get("issn", []) or []:
            if issn not in issns:
                issns.append(issn)
        host = source.get("host_organization_name") or ""
        return name, issns, host
    return "", [], ""


def article_from_openalex(data: dict[str, Any]) -> Article:
    source_name, _, host = openalex_source(data)
    authors, affiliations, author_affiliations = openalex_authors_and_affiliations(data)
    abstract = reconstruct_openalex_abstract(data.get("abstract_inverted_index"))
    doi_url = data.get("doi", "") or ""
    doi = doi_url.replace("https://doi.org/", "").lower().strip()
    url = ""
    primary_location = data.get("primary_location") or {}
    if primary_location:
        url = primary_location.get("landing_page_url") or primary_location.get("pdf_url") or ""
    return Article(
        title=data.get("display_name", "") or "",
        journal=source_name,
        doi=doi,
        publication_date=data.get("publication_date", "") or "",
        publication_date_source="openalex_publication_date",
        publisher=host,
        publisher_url=url or doi_url,
        abstract=abstract,
        keywords=openalex_keywords(data),
        authors=authors,
        affiliations=affiliations,
        author_affiliations=author_affiliations,
        source="OpenAlex",
        openalex_url=data.get("id", "") or "",
        abstract_status="available" if abstract else "missing",
    )


def enrich_from_openalex(article: Article) -> None:
    if not article.doi:
        return
    doi_url = f"https://doi.org/{article.doi}"
    encoded = urllib.parse.quote(doi_url, safe="")
    url = f"{OPENALEX_API}/works/{encoded}"
    try:
        data = http_json(url)
    except urllib.error.HTTPError:
        return
    except Exception:
        return

    article.openalex_url = data.get("id", "") or ""
    article.publisher_url = article.publisher_url or data.get("doi", "") or data.get("id", "") or ""
    article.publication_date = article.publication_date or data.get("publication_date", "") or ""
    article.publication_date_source = article.publication_date_source or "openalex_publication_date"
    if not article.abstract:
        article.abstract = reconstruct_openalex_abstract(data.get("abstract_inverted_index"))
        if article.abstract:
            article.abstract_status = "available"

    concepts = []
    primary_topic = data.get("primary_topic") or {}
    if primary_topic.get("display_name"):
        concepts.append(primary_topic["display_name"])
    for concept in data.get("concepts", []) or []:
        name = concept.get("display_name")
        if name and name not in concepts:
            concepts.append(name)
    for keyword in concepts:
        if keyword not in article.keywords:
            article.keywords.append(keyword)

    authors, affiliations, author_affiliations = openalex_authors_and_affiliations(data)
    if not article.authors:
        article.authors = authors

    merged_affiliations = set(article.affiliations)
    merged_affiliations.update(affiliations)
    article.affiliations = sorted(merged_affiliations)

    if not article.author_affiliations:
        article.author_affiliations = author_affiliations


def journal_index(journals: list[Journal]) -> tuple[set[str], set[str]]:
    issns: set[str] = set()
    titles: set[str] = set()
    for journal in journals:
        normalized = normalize_title(journal.title)
        titles.add(normalized)
        if normalized == "ssrn":
            titles.update(
                {
                    "ssrn electronic journal",
                    "social science research network",
                }
            )
        if normalized == "nber":
            titles.update(
                {
                    "nber working paper",
                    "nber working papers",
                    "national bureau of economic research",
                }
            )
        for issn in journal.issns:
            issns.add(issn)
    return issns, titles


def is_whitelisted_openalex_work(
    data: dict[str, Any],
    whitelist_issns: set[str],
    whitelist_titles: set[str],
) -> bool:
    source_name, source_issns, _ = openalex_source(data)
    if any(issn in whitelist_issns for issn in source_issns):
        return True
    return normalize_title(source_name) in whitelist_titles


def openalex_short_id(value: str) -> str:
    return str(value or "").rstrip("/").rsplit("/", 1)[-1]


def resolve_openalex_source(journal: Journal, log: list[str]) -> OpenAlexSource | None:
    mailto = os.environ.get("OBHRM_OPENALEX_MAILTO") or os.environ.get("OBHRM_CONTACT_EMAIL", "")
    for issn in journal.issns:
        params = {"filter": f"issn:{issn}", "per-page": "5"}
        if mailto:
            params["mailto"] = mailto
        try:
            data = http_json(f"{OPENALEX_API}/sources", params)
        except Exception as exc:  # noqa: BLE001
            log.append(f"WARN OpenAlex source lookup failed {journal.title} issn={issn}: {exc}")
            continue
        results = data.get("results", []) or []
        for source in results:
            source_issns = source.get("issn") or []
            if issn in source_issns or issn == source.get("issn_l"):
                return OpenAlexSource(
                    id=openalex_short_id(source.get("id", "")),
                    display_name=source.get("display_name", "") or journal.title,
                    resolution_method=f"issn:{issn}",
                )
        if results:
            source = results[0]
            return OpenAlexSource(
                id=openalex_short_id(source.get("id", "")),
                display_name=source.get("display_name", "") or journal.title,
                resolution_method=f"issn-first:{issn}",
            )

    params = {"search": journal.title, "per-page": "5"}
    if mailto:
        params["mailto"] = mailto
    try:
        data = http_json(f"{OPENALEX_API}/sources", params)
    except Exception as exc:  # noqa: BLE001
        log.append(f"WARN OpenAlex source title lookup failed {journal.title}: {exc}")
        return None
    target = normalize_title(journal.title)
    for source in data.get("results", []) or []:
        display_name = source.get("display_name", "") or ""
        if normalize_title(display_name) == target:
            return OpenAlexSource(
                id=openalex_short_id(source.get("id", "")),
                display_name=display_name,
                resolution_method="title-exact",
            )
    log.append(f"WARN OpenAlex source unresolved: {journal.title}")
    return None


def concept_pattern(concept: str) -> re.Pattern[str]:
    escaped = re.escape(concept.strip())
    escaped = re.sub(r"\\\s+", r"\\s+", escaped)
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", flags=re.IGNORECASE)


def keyword_matches(article: Article, concepts: list[str], match_mode: str = "any") -> bool:
    fields = {
        "title": article.title,
        "abstract": article.abstract,
        "keywords": "; ".join(article.keywords),
    }
    matched_concepts: list[str] = []
    matched_fields: list[str] = []
    for concept in concepts:
        pattern = concept_pattern(concept)
        for field_name, field_value in fields.items():
            if pattern.search(field_value or ""):
                matched_concepts.append(concept)
                matched_fields.append(field_name)
                break
    article.matched_concepts = list(dict.fromkeys(matched_concepts))
    article.matched_fields = list(dict.fromkeys(matched_fields))
    if match_mode == "all":
        return len(article.matched_concepts) == len(list(dict.fromkeys(concepts)))
    return bool(article.matched_concepts)


def query_crossref_journal(
    journal: Journal,
    start: datetime,
    end: datetime,
    rows: int,
    log: list[str],
) -> list[Article]:
    articles: list[Article] = []
    if not journal.issns:
        log.append(f"SKIP no ISSN: {journal.title}")
        return articles

    mailto = os.environ.get("OBHRM_CROSSREF_MAILTO") or os.environ.get("OBHRM_CONTACT_EMAIL", "")
    start_date = start.date().isoformat()
    end_date = end.date().isoformat()
    for issn in journal.issns:
        for date_filter in ["online-pub-date", "pub-date"]:
            filters = [
                f"from-{date_filter}:{start_date}",
                f"until-{date_filter}:{end_date}",
                "type:journal-article",
            ]
            params = {
                "filter": ",".join(filters),
                "rows": str(rows),
                "sort": "published",
                "order": "desc",
            }
            if mailto:
                params["mailto"] = mailto
            url = f"{CROSSREF_API}/journals/{urllib.parse.quote(issn)}/works"
            try:
                data = http_json(url, params)
            except Exception as exc:  # noqa: BLE001
                log.append(f"WARN Crossref failed {journal.title} {issn} {date_filter}: {exc}")
                continue
            items = (data.get("message") or {}).get("items", []) or []
            log.append(f"Crossref {journal.title} {issn} {date_filter}: {len(items)} items")
            for item in items:
                articles.append(article_from_crossref(item, journal.title, url))
            if items:
                break
        time.sleep(0.15)
    return articles


def dedupe_articles(articles: list[Article]) -> list[Article]:
    seen: set[str] = set()
    deduped: list[Article] = []
    for article in articles:
        key = article.doi or f"{article.title.lower()}::{article.journal.lower()}"
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(article)
    return deduped


def scan_articles(
    journals: list[Journal],
    concepts: list[str],
    match_mode: str,
    start: datetime,
    end: datetime,
    rows_per_journal: int,
    limit_journals: int | None,
    log: list[str],
) -> list[Article]:
    selected_journals = journals[:limit_journals] if limit_journals else journals
    all_articles: list[Article] = []
    for index, journal in enumerate(selected_journals, 1):
        log.append(f"JOURNAL {index}/{len(selected_journals)} {journal.title}")
        all_articles.extend(query_crossref_journal(journal, start, end, rows_per_journal, log))

    deduped = dedupe_articles(all_articles)
    matched: list[Article] = []
    for article in deduped:
        enrich_from_openalex(article)
        if keyword_matches(article, concepts, match_mode):
            matched.append(article)
        time.sleep(0.05)
    return sorted(matched, key=lambda item: (item.publication_date or "", item.journal, item.title))


def query_openalex_keyword(
    concept: str,
    start: datetime,
    end: datetime,
    per_page: int,
    max_pages: int,
    log: list[str],
) -> list[dict[str, Any]]:
    start_date = start.date().isoformat()
    end_date = end.date().isoformat()
    filters = [
        f"from_publication_date:{start_date}",
        f"to_publication_date:{end_date}",
        "type:article",
        f"title_and_abstract.search:{concept}",
    ]
    params = {
        "filter": ",".join(filters),
        "per-page": str(per_page),
        "sort": "publication_date:desc",
    }
    mailto = os.environ.get("OBHRM_OPENALEX_MAILTO") or os.environ.get("OBHRM_CONTACT_EMAIL", "")
    if mailto:
        params["mailto"] = mailto

    results: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        params["page"] = str(page)
        try:
            data = http_json(f"{OPENALEX_API}/works", params)
        except Exception as exc:  # noqa: BLE001
            log.append(f"WARN OpenAlex failed concept={concept!r} page={page}: {exc}")
            break
        page_results = data.get("results", []) or []
        log.append(f"OpenAlex concept={concept!r} page={page}: {len(page_results)} items")
        results.extend(page_results)
        if len(page_results) < per_page:
            break
        time.sleep(0.2)
    return results


def query_openalex_source_keyword(
    journal: Journal,
    source: OpenAlexSource,
    concept: str,
    start: datetime,
    end: datetime,
    per_page: int,
    max_pages: int,
    source_index: int,
    source_count: int,
    log: list[str],
    trace_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    start_date = start.date().isoformat()
    end_date = end.date().isoformat()
    filters = [
        f"from_publication_date:{start_date}",
        f"to_publication_date:{end_date}",
        "type:article",
        f"locations.source.id:{source.id}",
        f"title_and_abstract.search:{concept}",
    ]
    params = {
        "filter": ",".join(filters),
        "per-page": str(per_page),
        "sort": "publication_date:desc",
        "cursor": "*",
    }
    mailto = os.environ.get("OBHRM_OPENALEX_MAILTO") or os.environ.get("OBHRM_CONTACT_EMAIL", "")
    if mailto:
        params["mailto"] = mailto

    results: list[dict[str, Any]] = []
    total_count = 0
    pages_fetched = 0
    status = "complete"
    last_url = request_url(f"{OPENALEX_API}/works", params)
    for page in range(1, max_pages + 1):
        last_url = request_url(f"{OPENALEX_API}/works", params)
        try:
            data = http_json(f"{OPENALEX_API}/works", params)
        except Exception as exc:  # noqa: BLE001
            status = f"failed: {exc}"
            log.append(
                f"WARN OpenAlex source-first failed source={journal.title!r} "
                f"concept={concept!r} page={page}: {exc}"
            )
            break
        meta = data.get("meta") or {}
        if page == 1:
            total_count = int(meta.get("count") or 0)
        page_results = data.get("results", []) or []
        pages_fetched = page
        results.extend(page_results)
        log.append(
            f"OpenAlex source-first {source_index}/{source_count} source={journal.title!r} "
            f"source_id={source.id} concept={concept!r} page={page}: "
            f"{len(page_results)} items total={total_count}"
        )
        next_cursor = meta.get("next_cursor")
        if not page_results or not next_cursor:
            break
        params["cursor"] = next_cursor
        time.sleep(0.2)

    if total_count > len(results) and status == "complete":
        status = f"incomplete: fetched {len(results)} of {total_count}; increase --max-pages"
        log.append(
            f"WARN OpenAlex source-first incomplete source={journal.title!r} "
            f"concept={concept!r}: fetched {len(results)} of {total_count}"
        )

    trace_rows.append(
        {
            "source_index": source_index,
            "source_count": source_count,
            "journal": journal.title,
            "issns": "; ".join(journal.issns),
            "openalex_source_id": source.id,
            "openalex_source_name": source.display_name,
            "source_resolution": source.resolution_method,
            "concept": concept,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "api_total_count": total_count,
            "fetched_count": len(results),
            "pages_fetched": pages_fetched,
            "per_page": per_page,
            "max_pages": max_pages,
            "status": status,
            "query_url": last_url,
        }
    )
    return results


def scan_articles_keyword_first(
    journals: list[Journal],
    concepts: list[str],
    match_mode: str,
    start: datetime,
    end: datetime,
    per_keyword: int,
    max_pages: int,
    log: list[str],
) -> list[Article]:
    whitelist_issns, whitelist_titles = journal_index(journals)
    raw_works: list[dict[str, Any]] = []
    for concept in concepts:
        raw_works.extend(
            query_openalex_keyword(
                concept=concept,
                start=start,
                end=end,
                per_page=per_keyword,
                max_pages=max_pages,
                log=log,
            )
        )

    articles: list[Article] = []
    skipped = 0
    for work in raw_works:
        if not is_whitelisted_openalex_work(work, whitelist_issns, whitelist_titles):
            skipped += 1
            continue
        article = article_from_openalex(work)
        crossref_enrich_by_doi(article)
        if keyword_matches(article, concepts, match_mode):
            articles.append(article)
        time.sleep(0.05)
    log.append(f"OpenAlex whitelist-filter skipped: {skipped}")
    return sorted(dedupe_articles(articles), key=lambda item: (item.publication_date or "", item.journal, item.title))


def scan_articles_source_first(
    journals: list[Journal],
    concepts: list[str],
    match_mode: str,
    start: datetime,
    end: datetime,
    per_keyword: int,
    max_pages: int,
    limit_journals: int | None,
    log: list[str],
    trace_rows: list[dict[str, Any]],
) -> list[Article]:
    selected_journals = journals[:limit_journals] if limit_journals else journals
    raw_works: list[dict[str, Any]] = []
    for index, journal in enumerate(selected_journals, 1):
        log.append(f"SOURCE-FIRST JOURNAL {index}/{len(selected_journals)} {journal.title}")
        source = resolve_openalex_source(journal, log)
        if not source:
            trace_rows.append(
                {
                    "source_index": index,
                    "source_count": len(selected_journals),
                    "journal": journal.title,
                    "issns": "; ".join(journal.issns),
                    "openalex_source_id": "",
                    "openalex_source_name": "",
                    "source_resolution": "unresolved",
                    "concept": "",
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "api_total_count": 0,
                    "fetched_count": 0,
                    "pages_fetched": 0,
                    "per_page": per_keyword,
                    "max_pages": max_pages,
                    "status": "unresolved-source",
                    "query_url": "",
                }
            )
            continue
        for concept in concepts:
            raw_works.extend(
                query_openalex_source_keyword(
                    journal=journal,
                    source=source,
                    concept=concept,
                    start=start,
                    end=end,
                    per_page=per_keyword,
                    max_pages=max_pages,
                    source_index=index,
                    source_count=len(selected_journals),
                    log=log,
                    trace_rows=trace_rows,
                )
            )

    articles: list[Article] = []
    for work in raw_works:
        article = article_from_openalex(work)
        crossref_enrich_by_doi(article)
        if keyword_matches(article, concepts, match_mode):
            articles.append(article)
        time.sleep(0.05)
    return sorted(dedupe_articles(articles), key=lambda item: (item.publication_date or "", item.journal, item.title))


def safe_label(label: str | None) -> str:
    if not label:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-")
    return cleaned[:80]


def output_dir_for(end: datetime, label: str | None = None) -> tuple[Path, Path]:
    folder = end.date().isoformat()
    suffix = safe_label(label)
    if suffix:
        folder = f"{folder}_{suffix}"
    output_dir = OUTPUT_ROOT / folder
    log_dir = LOG_ROOT / folder
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, log_dir


def csv_value(values: list[str]) -> str:
    return "; ".join(value for value in values if value)


def write_csv_report(articles: list[Article], path: Path) -> None:
    fieldnames = [
        "title",
        "journal",
        "publication_date",
        "doi_url",
        "authors",
        "affiliations",
        "abstract_status",
        "abstract",
        "keywords",
        "matched_concepts",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for article in articles:
            affiliation_value = (
                format_author_affiliations(article.author_affiliations)
                if article.author_affiliations
                else csv_value(article.affiliations)
            )
            writer.writerow(
                {
                    "title": article.title,
                    "journal": article.journal,
                    "publication_date": article.publication_date,
                    "doi_url": article.doi_url,
                    "abstract_status": article.abstract_status,
                    "abstract": article.abstract,
                    "keywords": csv_value(article.keywords),
                    "authors": csv_value(article.authors),
                    "affiliations": affiliation_value,
                    "matched_concepts": csv_value(article.matched_concepts),
                }
            )


def write_trace_report(trace_rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "source_index",
        "source_count",
        "journal",
        "issns",
        "openalex_source_id",
        "openalex_source_name",
        "source_resolution",
        "concept",
        "window_start",
        "window_end",
        "api_total_count",
        "fetched_count",
        "pages_fetched",
        "per_page",
        "max_pages",
        "status",
        "query_url",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in trace_rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def article_markdown(article: Article, index: int) -> str:
    abstract = article.abstract if article.abstract else "_No public abstract found._"
    abstract_status_icon = "Available" if article.abstract_status != "missing" else "Missing"
    affiliation_value = (
        format_author_affiliations(article.author_affiliations)
        if article.author_affiliations
        else csv_value(article.affiliations)
    )
    return f"""### {index}. {article.title}

| Field | Value |
|---|---|
| Journal | {article.journal or "not available"} |
| Publication date | {article.publication_date or "unknown"} |
| DOI URL | {article.doi_url or "missing"} |
| Authors | {csv_value(article.authors) or "not available"} |
| Affiliations | {affiliation_value or "not available"} |
| Abstract status | {abstract_status_icon} |
| Abstract | {abstract} |
| Keywords | {csv_value(article.keywords) or "not available"} |
| Matched concepts | {csv_value(article.matched_concepts)} |

"""


def write_markdown_report(
    articles: list[Article],
    path: Path,
    keyword_name: str,
    match_mode: str,
    concepts: list[str],
    start: datetime,
    end: datetime,
    journal_count: int,
) -> None:
    missing = [article for article in articles if article.abstract_status == "missing"]
    available = [article for article in articles if article.abstract_status != "missing"]
    with_abstract_count = len(available)
    body = [
        "# OBHRM Weekly Literature Report",
        "",
        f"**Window:** {start.isoformat()} to {end.isoformat()}  ",
        f"**Concepts:** {csv_value(concepts)}  ",
        f"**Target journal/platform whitelist size:** {journal_count}  ",
        f"**Matched articles:** {len(articles)}  ",
        f"**Missing abstracts:** {len(missing)}",
        "",
        "## At a Glance",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Matched articles | {len(articles)} |",
        f"| Articles with abstracts | {with_abstract_count} |",
        f"| Missing abstracts | {len(missing)} |",
        f"| Target sources | {journal_count} |",
        "",
        "> Publication metadata often has date-level rather than hour-level precision. "
        "This report uses the requested Tokyo-time window and public metadata API date filters.",
        "",
        "> Full-text boundary: this report provides DOI and publisher links only. "
        "Readers must manually use their own authorized university account for full-text access. "
        "The monitor does not log in, bypass access controls, or download PDFs.",
        "",
        "## Articles With Abstracts",
        "",
    ]
    body.extend(article_markdown(article, index) for index, article in enumerate(available, 1))
    body.extend(["", "## Missing Abstract", ""])
    if missing:
        body.extend(article_markdown(article, index) for index, article in enumerate(missing, 1))
    else:
        body.append("No matched articles with missing abstracts.")
    path.write_text("\n".join(body), encoding="utf-8")


def lark_signature(secret: str, timestamp: str) -> str:
    payload = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(payload, b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def send_lark(text: str) -> None:
    webhook = os.environ.get("OBHRM_LARK_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("OBHRM_LARK_WEBHOOK_URL is not set")
    payload: dict[str, Any] = {"msg_type": "text", "content": {"text": text}}
    secret = os.environ.get("OBHRM_LARK_WEBHOOK_SECRET")
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = lark_signature(secret, timestamp)
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def format_lark_summary(
    journal_counts: Counter[str],
    concepts: list[str],
    start: datetime,
    end: datetime,
    public_report_url: str = "",
    public_index_url: str = "",
) -> str:
    lines = [
        "OBHRM Weekly Literature Report",
        f"Concepts: {csv_value(concepts)}",
        f"Window: {start.isoformat()} to {end.isoformat()}",
        "",
        "Journal counts:",
    ]
    if journal_counts:
        for journal, count in sorted(journal_counts.items(), key=lambda item: (-item[1], item[0].lower())):
            lines.append(f"- {journal}: {count}")
    else:
        lines.append("- No matched articles")
    if public_report_url or public_index_url:
        lines.append("")
    if public_report_url:
        lines.extend(["Full report:", public_report_url])
    if public_index_url:
        lines.extend(["Report index:", public_index_url])
    return "\n".join(lines)


def build_lark_summary(
    articles: list[Article],
    concepts: list[str],
    start: datetime,
    end: datetime,
    public_report_url: str = "",
    public_index_url: str = "",
) -> str:
    journal_counts = Counter(article.journal or "Unknown journal" for article in articles)
    return format_lark_summary(journal_counts, concepts, start, end, public_report_url, public_index_url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OBHRM literature monitor scan.")
    parser.add_argument("--keyword", action="append", default=[], help="One keyword concept. Repeat up to 5 times.")
    parser.add_argument("--keywords", help="Legacy semicolon-separated keyword concepts.")
    parser.add_argument("--match-mode", choices=["any", "all"], help="Keyword matching logic.")
    parser.add_argument(
        "--timezone",
        choices=["Asia/Tokyo", "America/Chicago", "Asia/Shanghai"],
        help="Timezone used to interpret --start and --end.",
    )
    parser.add_argument("--start", help="Local start datetime, e.g. 2026-05-25T08:00.")
    parser.add_argument("--end", help="Local end datetime, e.g. 2026-05-26T08:00.")
    parser.add_argument("--trial", action="store_true", help="Use the approved trial window.")
    parser.add_argument("--previous-week", action="store_true", help="Use previous Monday 00:00 to current Monday 00:00.")
    parser.add_argument("--rows-per-journal", type=int, default=20)
    parser.add_argument("--limit-journals", type=int, help="Debug limit for the number of journals.")
    parser.add_argument("--output-label", help="Optional suffix for output/log folders.")
    parser.add_argument(
        "--strategy",
        choices=["openalex-source", "openalex-keyword", "crossref-journal"],
        default="openalex-source",
    )
    parser.add_argument("--per-keyword", type=int, default=200)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--push-lark", action="store_true")
    parser.add_argument("--public-report-url", help="Public URL for the full hosted HTML report.")
    parser.add_argument("--public-index-url", help="Public URL for the hosted report index page.")
    parser.add_argument(
        "--journal-list",
        choices=list(JOURNAL_LISTS),
        default="all-whitelist",
        help="Named source subset to scan.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    config = load_config()
    timezone = args.timezone or str(config.get("timezone", "Asia/Tokyo"))
    keyword_name, match_mode, concepts = parse_keywords(config, args.keywords, args.keyword, args.match_mode)

    if args.trial:
        start, end = trial_window(timezone)
    elif args.previous_week:
        start, end = previous_week_window(timezone)
    elif args.start and args.end:
        start = parse_local_datetime(args.start, timezone)
        end = parse_local_datetime(args.end, timezone)
    else:
        start, end = default_window(timezone)
    validate_window(start, end)

    journals = load_journals(WHITELIST_CSV, args.journal_list)
    output_dir, log_dir = output_dir_for(end, args.output_label)
    report_path = output_dir / "obhrm_daily_report.md"
    csv_path = output_dir / "obhrm_daily_records.csv"
    trace_path = output_dir / "obhrm_scan_trace.csv"
    log_path = log_dir / "run.log"
    trace_rows: list[dict[str, Any]] = []
    log: list[str] = [
        f"Start: {datetime.now().isoformat(timespec='seconds')}",
        f"Window: {start.isoformat()} to {end.isoformat()}",
        f"Timezone: {timezone}",
        f"Keywords: {concepts}",
        f"Match mode: {match_mode}",
        f"Journal list: {args.journal_list} ({JOURNAL_LISTS[args.journal_list]['label']})",
        f"Journals: {len(journals)}",
        f"Strategy: {args.strategy}",
    ]

    if args.strategy == "crossref-journal":
        articles = scan_articles(
            journals=journals,
            concepts=concepts,
            match_mode=match_mode,
            start=start,
            end=end,
            rows_per_journal=args.rows_per_journal,
            limit_journals=args.limit_journals,
            log=log,
        )
    elif args.strategy == "openalex-source":
        articles = scan_articles_source_first(
            journals=journals,
            concepts=concepts,
            match_mode=match_mode,
            start=start,
            end=end,
            per_keyword=args.per_keyword,
            max_pages=args.max_pages,
            limit_journals=args.limit_journals,
            log=log,
            trace_rows=trace_rows,
        )
    else:
        selected_journals = journals[: args.limit_journals] if args.limit_journals else journals
        articles = scan_articles_keyword_first(
            journals=selected_journals,
            concepts=concepts,
            match_mode=match_mode,
            start=start,
            end=end,
            per_keyword=args.per_keyword,
            max_pages=args.max_pages,
            log=log,
        )
    write_csv_report(articles, csv_path)
    write_trace_report(trace_rows, trace_path)
    write_markdown_report(
        articles=articles,
        path=report_path,
        keyword_name=keyword_name,
        match_mode=match_mode,
        concepts=concepts,
        start=start,
        end=end,
        journal_count=len(journals),
    )

    log.append(f"Matched articles: {len(articles)}")
    log.append(f"Report: {report_path}")
    log.append(f"CSV: {csv_path}")
    log.append(f"Trace: {trace_path}")

    if args.push_lark:
        try:
            send_lark(
                build_lark_summary(
                    articles,
                    concepts,
                    start,
                    end,
                    public_report_url=args.public_report_url or "",
                    public_index_url=args.public_index_url or "",
                )
            )
            log.append("Lark push: OK")
        except Exception as exc:  # noqa: BLE001
            log.append(f"Lark push: FAILED {exc}")

    log_path.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {log_path}")
    print(f"Matched articles: {len(articles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
