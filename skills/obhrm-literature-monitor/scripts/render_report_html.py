"""Render an OBHRM Markdown report into a standalone HTML file."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


DEFAULT_REPORT = (
    Path(__file__).resolve().parents[3]
    / "outputs"
    / "2026-05-25_ai-llm-week-2026-05-18-to-2026-05-24-designed-198"
    / "obhrm_daily_report.md"
)


STYLE = """
:root {
  color-scheme: light;
  --ink: #172033;
  --muted: #647084;
  --line: #d9e0ea;
  --soft: #f7f9fc;
  --panel: #ffffff;
  --accent: #1f5fbf;
  --accent-strong: #123b77;
  --accent-soft: #eaf2ff;
  --warn: #b42318;
  --warn-soft: #fff1f0;
  --ok: #067647;
  --ok-soft: #ecfdf3;
  --shadow: 0 18px 44px rgba(24, 33, 47, 0.10);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans",
    "Microsoft YaHei", Arial, sans-serif;
  color: var(--ink);
  background:
    linear-gradient(180deg, #f4f7fb 0%, #eef3f8 260px, #f7f9fc 100%);
  line-height: 1.55;
}
main {
  width: min(1120px, calc(100% - 40px));
  margin: 34px auto 56px;
}
.hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #ffffff 0%, #f7fbff 100%);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 30px 34px;
  box-shadow: var(--shadow);
}
.hero::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 6px;
  background: linear-gradient(180deg, var(--accent), #6a9af6);
}
h1 {
  margin: 0 0 18px;
  color: var(--accent-strong);
  font-size: 34px;
  line-height: 1.16;
  letter-spacing: 0;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
}
.meta-item {
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
}
.meta-label {
  display: block;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.section {
  margin-top: 30px;
}
h2 {
  margin: 0 0 16px;
  color: var(--accent-strong);
  font-size: 23px;
  line-height: 1.25;
}
h3 {
  margin: 0;
  color: #111827;
  font-size: 19px;
  line-height: 1.35;
}
.article {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0;
  margin: 18px 0;
  overflow: hidden;
  box-shadow: 0 8px 22px rgba(24, 33, 47, 0.06);
}
.article-header {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 14px;
  align-items: start;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--line);
  background: #fbfcfe;
}
.article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.article-content {
  padding: 18px 24px 22px;
}
.note {
  border-left: 4px solid var(--accent);
  background: var(--accent-soft);
  padding: 12px 14px;
  margin: 12px 0;
  border-radius: 6px;
  color: #243b63;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 4px 14px rgba(24, 33, 47, 0.04);
}
.stat-label {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.stat-value {
  display: block;
  margin-top: 4px;
  color: var(--accent-strong);
  font-size: 26px;
  font-weight: 800;
}
.summary-table {
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 4px 14px rgba(24, 33, 47, 0.04);
}
.summary-table th,
.summary-table td {
  padding: 12px 14px;
}
.summary-table th {
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.empty-note {
  color: var(--muted);
  background: var(--panel);
  border: 1px dashed var(--line);
  border-radius: 10px;
  padding: 14px 16px;
}
.keyword-nav {
  margin-top: 30px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: 0 8px 22px rgba(24, 33, 47, 0.06);
}
.keyword-nav h2 {
  font-size: 20px;
  margin-bottom: 8px;
}
.keyword-nav-intro {
  color: var(--muted);
  margin: 0 0 14px;
}
.keyword-nav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.keyword-nav-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel);
  padding: 12px 14px;
}
.keyword-nav-title {
  color: var(--accent-strong);
  display: block;
  font-weight: 900;
  margin-bottom: 8px;
}
.keyword-nav-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.keyword-nav-links a {
  border: 1px solid #b7cdfb;
  border-radius: 999px;
  background: #f7faff;
  color: var(--accent-strong);
  font-size: 12px;
  font-weight: 800;
  padding: 4px 9px;
}
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--panel);
}
th, td {
  border-bottom: 1px solid var(--line);
  padding: 10px 0;
  vertical-align: top;
}
th {
  background: #f1f4f9;
  color: #344054;
  text-align: left;
}
tr:last-child td { border-bottom: 0; }
.field-name {
  width: 170px;
  color: var(--muted);
  font-weight: 700;
  white-space: nowrap;
  padding-right: 18px;
}
.field-value {
  color: #263244;
}
.abstract-block {
  margin: 12px 0;
  padding: 14px 16px;
  background: #fbfdff;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.abstract-label {
  color: var(--muted);
  display: block;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  margin-bottom: 7px;
  text-transform: uppercase;
}
.abstract-text {
  margin: 0;
  color: #263244;
  hyphens: auto;
  text-align: justify;
  text-wrap: pretty;
}
.affiliation-table {
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
}
.affiliation-table th,
.affiliation-table td {
  padding: 10px 12px;
}
.affiliation-table th {
  background: #f5f8fc;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.affiliation-author {
  width: 24%;
  color: #263244;
  font-weight: 800;
}
.affiliation-value {
  color: #263244;
  text-align: left;
}
.badge {
  display: inline-block;
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 12px;
  font-weight: 700;
}
.badge.available { color: var(--ok); background: var(--ok-soft); }
.badge.missing { color: var(--warn); background: var(--warn-soft); }
.badge.journal {
  color: var(--accent-strong);
  background: var(--accent-soft);
}
.badge.date {
  color: #475467;
  background: #f2f4f7;
}
.doi-link {
  display: inline-flex;
  align-items: center;
  border: 1px solid #b7cdfb;
  border-radius: 999px;
  background: #f7faff;
  padding: 5px 10px;
  font-weight: 700;
}
a {
  color: var(--accent);
  text-decoration: none;
  overflow-wrap: anywhere;
}
a:hover { text-decoration: underline; }
.trend-section {
  margin-top: 30px;
}
.trend-intro {
  color: var(--muted);
  margin: -8px 0 18px;
}
.combined-trend {
  position: relative;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 18px;
  box-shadow: 0 8px 22px rgba(24, 33, 47, 0.06);
}
.combined-trend-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.chart-mode-toggle {
  display: inline-flex;
  gap: 4px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px;
  background: #f8fafc;
}
.chart-mode-button {
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  padding: 6px 10px;
}
.chart-mode-button.active {
  background: var(--panel);
  color: var(--accent-strong);
  box-shadow: 0 2px 7px rgba(24, 33, 47, 0.10);
}
.combined-svg[hidden] {
  display: none;
}
.trend-hover-zone {
  fill: transparent;
  pointer-events: all;
}
.trend-hover-line {
  display: none;
  stroke: #94a3b8;
  stroke-dasharray: 4 4;
  stroke-width: 1.4;
}
.trend-tooltip {
  display: none;
  position: absolute;
  z-index: 5;
  max-width: min(460px, calc(100% - 40px));
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.98);
  color: var(--ink);
  box-shadow: 0 16px 42px rgba(24, 33, 47, 0.16);
  font-size: 13px;
}
.trend-tooltip-title {
  color: var(--accent-strong);
  font-size: 15px;
  font-weight: 900;
  margin-bottom: 6px;
}
.trend-tooltip-row {
  border-top: 1px solid #edf1f6;
  padding-top: 7px;
  margin-top: 7px;
}
.trend-tooltip-keyword {
  font-weight: 900;
}
.trend-tooltip-meta {
  color: var(--muted);
}
.trend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}
.trend-card {
  display: block;
  min-height: 236px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  color: inherit;
  box-shadow: 0 8px 22px rgba(24, 33, 47, 0.06);
}
.trend-card:hover {
  border-color: #b7cdfb;
  box-shadow: 0 14px 30px rgba(24, 33, 47, 0.10);
  text-decoration: none;
}
.trend-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  min-height: 54px;
}
.trend-title {
  margin: 0;
  font-size: 18px;
  line-height: 1.22;
  color: var(--trend-color, var(--accent));
}
.trend-count {
  display: block;
  color: var(--muted);
  font-size: 14px;
  font-weight: 800;
  margin-top: 3px;
}
.trend-open {
  color: var(--trend-color, var(--accent));
  font-size: 24px;
  line-height: 1;
  font-weight: 800;
}
.trend-svg {
  width: 100%;
  height: auto;
  margin-top: 10px;
}
.trend-axis {
  fill: #9aa5b5;
  font-size: 11px;
}
.trend-footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-size: 14px;
  margin-top: 8px;
}
.trend-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-top: 10px;
}
.trend-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 13px;
}
.trend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--trend-color, var(--accent));
}
.trend-modal {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 20;
  align-items: center;
  justify-content: center;
  padding: 28px;
  background: rgba(15, 23, 42, 0.48);
}
.trend-modal:target {
  display: flex;
}
.trend-modal-card {
  width: min(1040px, 100%);
  max-height: min(760px, calc(100vh - 56px));
  overflow: auto;
  background: var(--panel);
  border-radius: 14px;
  border: 1px solid var(--line);
  padding: 22px 24px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.25);
}
.trend-modal-top {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 10px;
}
.trend-close {
  flex: 0 0 auto;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 5px 10px;
  color: var(--muted);
  font-weight: 800;
}
@media (max-width: 720px) {
  main { width: min(100% - 20px, 1120px); margin-top: 16px; }
  .hero { padding: 22px 20px; }
  h1 { font-size: 26px; }
  .article-header {
    grid-template-columns: 1fr;
    padding: 18px;
  }
  .article-meta {
    justify-content: flex-start;
  }
  .article-content { padding: 16px 18px 18px; }
  tr, td { display: block; width: 100%; }
  td { border-bottom: 0; padding: 4px 0; }
  tr {
    border-bottom: 1px solid var(--line);
    padding: 8px 0;
  }
  .field-name { white-space: normal; }
  .affiliation-table,
  .affiliation-table thead,
  .affiliation-table tbody,
  .affiliation-table tr,
  .affiliation-table th,
  .affiliation-table td {
    display: block;
    width: 100%;
  }
  .affiliation-table th { display: none; }
  .affiliation-author {
    padding-bottom: 0;
  }
  .affiliation-value {
    padding-top: 2px;
  }
  .trend-modal { padding: 12px; }
  .trend-modal-card { padding: 18px; }
  .combined-trend-header {
    display: block;
  }
  .chart-mode-toggle {
    margin-top: 10px;
  }
}
"""


CHART_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef476f"]

REPORT_SCRIPT = """
<script>
(() => {
  const escapeHtml = (value) => String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

  const formatTopWork = (work) => {
    if (!work || !work.title) return "No top-cited candidate metadata available.";
    const parts = [];
    if (work.journal) parts.push(escapeHtml(work.journal));
    if (work.publication_date) parts.push(escapeHtml(work.publication_date));
    parts.push(`${Number(work.cited_by_count || 0)} citations`);
    const link = work.doi_url || work.openalex_url;
    const title = link
      ? `<a href="${escapeHtml(link)}" target="_blank" rel="noopener">${escapeHtml(work.title)}</a>`
      : escapeHtml(work.title);
    return `${title}<br><span class="trend-tooltip-meta">${parts.join(" · ")}</span>`;
  };

  document.querySelectorAll(".combined-trend").forEach((chart) => {
    const dataNode = chart.querySelector(".trend-data");
    const tooltip = chart.querySelector(".trend-tooltip");
    if (!dataNode || !tooltip) return;
    let data;
    try {
      data = JSON.parse(dataNode.textContent || "{}");
    } catch {
      return;
    }

    const showMode = (mode) => {
      chart.querySelectorAll(".combined-svg").forEach((svg) => {
        if (svg.dataset.mode === mode) {
          svg.removeAttribute("hidden");
        } else {
          svg.setAttribute("hidden", "");
        }
      });
      chart.querySelectorAll(".chart-mode-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.chartMode === mode);
      });
    };

    chart.querySelectorAll(".chart-mode-button").forEach((button) => {
      button.addEventListener("click", () => showMode(button.dataset.chartMode || "indexed"));
    });

    const showTooltip = (event, year, svg) => {
      const yearIndex = data.years.indexOf(Number(year));
      if (yearIndex < 0) return;
      const rows = data.series.map((series) => {
        const top = (series.top_by_year || {})[String(year)] || {};
        const count = Number((series.counts || [])[yearIndex] || 0);
        return `<div class="trend-tooltip-row">
          <span class="trend-tooltip-keyword" style="color:${escapeHtml(series.color)}">${escapeHtml(series.concept)}</span>:
          <strong>${count}</strong> candidate appearances
          <div>${formatTopWork(top)}</div>
        </div>`;
      }).join("");
      tooltip.innerHTML = `<div class="trend-tooltip-title">${escapeHtml(year)}</div>${rows}`;
      tooltip.style.display = "block";
      const chartRect = chart.getBoundingClientRect();
      const tooltipWidth = Math.min(460, chartRect.width - 40);
      const left = Math.min(
        Math.max(event.clientX - chartRect.left + 14, 12),
        chartRect.width - tooltipWidth - 12
      );
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${Math.max(event.clientY - chartRect.top - 12, 70)}px`;
      const line = svg.querySelector(".trend-hover-line");
      const zone = event.currentTarget;
      if (line && zone) {
        const x = Number(zone.getAttribute("x")) + Number(zone.getAttribute("width")) / 2;
        line.setAttribute("x1", x);
        line.setAttribute("x2", x);
        line.style.display = "block";
      }
    };

    chart.querySelectorAll(".trend-hover-zone").forEach((zone) => {
      zone.addEventListener("mousemove", (event) => {
        const svg = zone.closest("svg");
        showTooltip(event, zone.dataset.year, svg);
      });
      zone.addEventListener("mouseenter", (event) => {
        const svg = zone.closest("svg");
        showTooltip(event, zone.dataset.year, svg);
      });
    });

    chart.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
      chart.querySelectorAll(".trend-hover-line").forEach((line) => {
        line.style.display = "none";
      });
    });

    showMode("indexed");
  });
})();
</script>
"""


def repair_mojibake(text: str) -> str:
    replacements = {
        "鈥揳": "–a",
        "鈥搊": "–o",
        "鈥搃": "–i",
        "鈥?": "’",
        "鈥檚": "’s",
        "鈥檛": "’t",
        "艂": "ł",
        "â€“": "–",
        "â€™": "’",
        "â€œ": "“",
        "â€\u009d": "”",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    suspicious = ("\u00c2", "\u00c3", "\u00e2", "\u9225", "\ufffd")
    if not any(token in text for token in suspicious):
        return text

    def score(value: str) -> int:
        return sum(value.count(token) for token in suspicious)

    best = text
    best_score = score(text)
    for encoding in ("latin1", "cp1252", "gbk"):
        try:
            candidate = text.encode(encoding).decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
        candidate_score = score(candidate)
        if candidate_score < best_score:
            best = candidate
            best_score = candidate_score
    return best


def inline_markdown(text: str) -> str:
    text = repair_mojibake(text)
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"(https://doi\.org/[^\s|<]+)",
        r'<a class="doi-link" href="\1" target="_blank" rel="noopener">\1</a>',
        escaped,
    )
    return escaped


def slugify_fragment(text: str) -> str:
    text = repair_mojibake(text).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "section"


def render_keyword_nav(markdown: str) -> str:
    articles: dict[str, str] = {}
    missing: dict[str, str] = {}
    for line in markdown.splitlines():
        if line.startswith("## Articles With Abstracts - "):
            concept = line.removeprefix("## Articles With Abstracts - ").strip()
            articles[concept] = slugify_fragment(line[3:].strip())
        elif line.startswith("## Missing Abstract - "):
            concept = line.removeprefix("## Missing Abstract - ").strip()
            missing[concept] = slugify_fragment(line[3:].strip())
    concepts = sorted(set(articles) | set(missing), key=str.casefold)
    if len(concepts) <= 1:
        return ""
    cards = []
    for concept in concepts:
        links = []
        if concept in articles:
            links.append(f'<a href="#{articles[concept]}">Articles with abstracts</a>')
        if concept in missing:
            links.append(f'<a href="#{missing[concept]}">Missing abstracts</a>')
        cards.append(
            '<div class="keyword-nav-card">'
            f'<span class="keyword-nav-title">{html.escape(repair_mojibake(concept))}</span>'
            '<div class="keyword-nav-links">'
            + "\n".join(links)
            + "</div></div>"
        )
    return (
        '<nav class="keyword-nav" aria-label="Keyword result shortcuts">'
        "<h2>Jump to Keyword Results</h2>"
        '<p class="keyword-nav-intro">Use these shortcuts to move directly to each keyword-specific article list.</p>'
        '<div class="keyword-nav-grid">'
        + "\n".join(cards)
        + "</div></nav>"
    )


def render_author_affiliations(value: str) -> str:
    rows = []
    for raw_row in re.split(r"\s+(?:~~|\|\|)\s+", value):
        if " :: " in raw_row:
            author, affiliation = raw_row.split(" :: ", 1)
        else:
            author, affiliation = "not available", raw_row
        rows.append(
            "<tr>"
            f'<td class="affiliation-author">{inline_markdown(author)}</td>'
            f'<td class="affiliation-value">{inline_markdown(affiliation)}</td>'
            "</tr>"
        )
    if not rows:
        return inline_markdown(value)
    return (
        '<table class="affiliation-table">'
        "<thead><tr><th>Author</th><th>Affiliation</th></tr></thead>"
        "<tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def parse_field_table(lines: list[str], start_index: int) -> tuple[list[tuple[str, str]], int]:
    fields: list[tuple[str, str]] = []
    index = start_index + 2
    while index < len(lines):
        line = lines[index]
        if not line.startswith("| "):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2:
            fields.append((cells[0], cells[1]))
        index += 1
    return fields, index


def render_generic_table(table_lines: list[str]) -> str:
    rows = []
    for index, line in enumerate(table_lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if index == 1 and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        tag = "th" if index == 0 else "td"
        rows.append(
            "<tr>"
            + "".join(f"<{tag}>{inline_markdown(cell)}</{tag}>" for cell in cells)
            + "</tr>"
        )
    return '<table class="summary-table">' + "\n".join(rows) + "</table>"


def render_fields(fields: list[tuple[str, str]]) -> str:
    chunks = []
    rows = []

    def flush_rows() -> None:
        nonlocal rows
        if rows:
            chunks.append('<table class="field-table">' + "\n".join(rows) + "</table>")
            rows = []

    for name, value in fields:
        if name == "Authors":
            continue
        display_name = "Author & affiliation" if name == "Affiliations" else name
        if name == "Abstract status":
            status = value.strip().lower()
            badge_class = "missing" if status == "missing" else "available"
            value_html = f'<span class="badge {badge_class}">{html.escape(value)}</span>'
        elif name == "Abstract":
            flush_rows()
            chunks.append(
                '<div class="abstract-block">'
                f'<span class="abstract-label">{html.escape(display_name)}</span>'
                f'<p class="abstract-text" lang="en">{inline_markdown(value)}</p>'
                "</div>"
            )
            continue
        elif name == "Affiliations" and " :: " in value:
            value_html = render_author_affiliations(value)
        else:
            value_html = inline_markdown(value)
        rows.append(
            "<tr>"
            f'<td class="field-name">{html.escape(display_name)}</td>'
            f'<td class="field-value">{value_html}</td>'
            "</tr>"
        )
    flush_rows()
    return "\n".join(chunks)


def article_badges(fields: list[tuple[str, str]]) -> str:
    values = {name: value for name, value in fields}
    badges = []
    journal = values.get("Journal", "")
    date = values.get("Publication date", "")
    status = values.get("Abstract status", "")
    if journal:
        badges.append(f'<span class="badge journal">{inline_markdown(journal)}</span>')
    if date:
        badges.append(f'<span class="badge date">{inline_markdown(date)}</span>')
    if status:
        status_class = "missing" if status.strip().lower() == "missing" else "available"
        badges.append(f'<span class="badge {status_class}">{html.escape(status)}</span>')
    return '<div class="article-meta">' + "\n".join(badges) + "</div>"


def load_keyword_trends(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    series = data.get("series")
    if not isinstance(series, list) or not series:
        return None
    usable = [
        item
        for item in series
        if isinstance(item, dict)
        and item.get("concept")
        and isinstance(item.get("points"), list)
        and item.get("points")
    ]
    if not usable:
        return None
    data["series"] = usable
    return data


def trend_years(data: dict) -> list[int]:
    years = [year for year in data.get("years", []) if isinstance(year, int)]
    if years:
        return list(range(min(years), max(years) + 1))
    collected = []
    for item in data.get("series", []):
        for point in item.get("points", []):
            year = point.get("year")
            if isinstance(year, int):
                collected.append(year)
    return list(range(min(collected), max(collected) + 1)) if collected else []


def points_for_series(item: dict, years: list[int]) -> list[int]:
    by_year = {
        int(point["year"]): int(point.get("count", 0))
        for point in item.get("points", [])
        if isinstance(point, dict) and isinstance(point.get("year"), int)
    }
    return [by_year.get(year, 0) for year in years]


def top_work_by_year(item: dict) -> dict[int, dict]:
    values = {}
    for point in item.get("points", []):
        if isinstance(point, dict) and isinstance(point.get("year"), int):
            values[int(point["year"])] = point.get("top_cited_work") or {}
    return values


def normalized_points(counts: list[int]) -> list[float]:
    peak = max(counts, default=0)
    if peak <= 0:
        return [0 for _ in counts]
    return [(count / peak) * 100 for count in counts]


def chart_coordinates(
    counts: list[int] | list[float],
    years: list[int],
    width: int,
    height: int,
    padding: int,
    max_y: int,
) -> list[tuple[float, float]]:
    if not years:
        return []
    span = max(len(years) - 1, 1)
    usable_width = width - padding * 2
    usable_height = height - padding * 2
    coordinates = []
    for index, count in enumerate(counts):
        x = padding + (usable_width * index / span)
        y = height - padding - (usable_height * count / max(max_y, 1))
        coordinates.append((x, y))
    return coordinates


def points_attr(coordinates: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in coordinates)


def render_single_chart(
    item: dict,
    years: list[int],
    color: str,
    width: int = 320,
    height: int = 130,
    padding: int = 24,
) -> str:
    counts = points_for_series(item, years)
    max_y = max(max(counts, default=0), 1)
    coordinates = chart_coordinates(counts, years, width, height, padding, max_y)
    if not coordinates:
        return ""
    baseline = height - padding
    area_points = [(coordinates[0][0], baseline), *coordinates, (coordinates[-1][0], baseline)]
    start_year = years[0]
    end_year = years[-1]
    peak_count = max(counts, default=0)
    peak_index = counts.index(peak_count) if counts else 0
    peak_x, peak_y = coordinates[peak_index]
    return f"""
<svg class="trend-svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(str(item.get('concept', 'Keyword trend')))} yearly trend">
  <line x1="{padding}" y1="{baseline}" x2="{width - padding}" y2="{baseline}" stroke="#d9e0ea" stroke-width="1"/>
  <text class="trend-axis" x="{padding}" y="{height - 6}">{start_year}</text>
  <text class="trend-axis" x="{width - padding}" y="{height - 6}" text-anchor="end">{end_year}</text>
  <text class="trend-axis" x="{padding}" y="{padding - 8}">{max_y}</text>
  <polygon points="{points_attr(area_points)}" fill="{color}" opacity="0.13"/>
  <polyline points="{points_attr(coordinates)}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{peak_x:.1f}" cy="{peak_y:.1f}" r="4" fill="{color}" stroke="#fff" stroke-width="2"/>
</svg>
"""


def render_combined_chart(
    data: dict,
    years: list[int],
    title: str = "Combined Keyword Trajectories",
    show_legend: bool = True,
    extra_class: str = "",
) -> str:
    series = data.get("series", [])
    width = 900
    height = 290
    padding = 44
    raw_counts_by_series = [points_for_series(item, years) for item in series]

    def chart_svg(mode: str, max_y: int, counts_by_series: list[list[int] | list[float]]) -> str:
        baseline = height - padding
        chart_lines = [
            f'<line x1="{padding}" y1="{baseline}" x2="{width - padding}" y2="{baseline}" stroke="#d9e0ea" stroke-width="1"/>',
            f'<text class="trend-axis" x="{padding}" y="{height - 14}">{years[0]}</text>',
            f'<text class="trend-axis" x="{width - padding}" y="{height - 14}" text-anchor="end">{years[-1]}</text>',
            f'<text class="trend-axis" x="{padding}" y="{padding - 14}">{max_y}</text>',
        ]
        for index, item in enumerate(series):
            color = CHART_COLORS[index % len(CHART_COLORS)]
            coordinates = chart_coordinates(counts_by_series[index], years, width, height, padding, max_y)
            if not coordinates:
                continue
            chart_lines.append(
                f'<polyline points="{points_attr(coordinates)}" fill="none" stroke="{color}" '
                'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
            )
        hover_coordinates = chart_coordinates([0 for _ in years], years, width, height, padding, max_y)
        if hover_coordinates:
            chart_lines.append(
                f'<line class="trend-hover-line" x1="{hover_coordinates[0][0]:.1f}" y1="{padding}" '
                f'x2="{hover_coordinates[0][0]:.1f}" y2="{baseline}"/>'
            )
            zone_width = max((width - padding * 2) / max(len(years), 1), 8)
            for year, (x, _) in zip(years, hover_coordinates):
                chart_lines.append(
                    f'<rect class="trend-hover-zone" data-year="{year}" '
                    f'x="{x - zone_width / 2:.1f}" y="{padding}" '
                    f'width="{zone_width:.1f}" height="{baseline - padding}"/>'
                )
        return (
            f'<svg class="trend-svg combined-svg" data-mode="{mode}" '
            f'viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="Combined keyword yearly trend, {mode} mode">'
            + "\n".join(chart_lines)
            + "</svg>"
        )

    raw_max_y = max([max(counts, default=0) for counts in raw_counts_by_series] or [1])
    indexed_counts_by_series = [normalized_points(counts) for counts in raw_counts_by_series]
    legend = []
    for index, item in enumerate(series):
        color = CHART_COLORS[index % len(CHART_COLORS)]
        legend.append(
            '<span class="trend-legend-item">'
            f'<span class="trend-swatch" style="--trend-color:{color}"></span>'
            f"{html.escape(str(item.get('concept', 'Keyword')))}"
            "</span>"
        )
    payload = {
        "years": years,
        "series": [
            {
                "concept": str(item.get("concept", "Keyword")),
                "color": CHART_COLORS[index % len(CHART_COLORS)],
                "counts": raw_counts_by_series[index],
                "top_by_year": top_work_by_year(item),
            }
            for index, item in enumerate(series)
        ],
    }
    payload_json = (
        json.dumps(payload, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    return (
        f'<div class="combined-trend {html.escape(extra_class)}">'
        '<div class="combined-trend-header">'
        f"<h3>{html.escape(title)}</h3>"
        '<div class="chart-mode-toggle" role="group" aria-label="Chart scale mode">'
        '<button class="chart-mode-button active" type="button" data-chart-mode="indexed">% of keyword peak</button>'
        '<button class="chart-mode-button" type="button" data-chart-mode="raw">Raw counts</button>'
        "</div></div>"
        + chart_svg("indexed", 100, indexed_counts_by_series)
        + chart_svg("raw", raw_max_y, raw_counts_by_series).replace('class="trend-svg combined-svg"', 'class="trend-svg combined-svg" hidden')
        + (('<div class="trend-legend">' + "\n".join(legend) + "</div>") if show_legend else "")
        + '<div class="trend-tooltip" role="status"></div>'
        + f'<script type="application/json" class="trend-data">{payload_json}</script>'
        + "</div>"
    )


def render_keyword_trends(path: Path) -> str:
    data = load_keyword_trends(path)
    if not data:
        return ""
    years = trend_years(data)
    if not years:
        return ""
    series = data.get("series", [])
    if len(series) == 1:
        concept = str(series[0].get("concept", "Keyword"))
        return (
            '<section class="trend-section">'
            "<h2>Keyword Trajectory</h2>"
            '<p class="trend-intro">This chart shows yearly candidate appearances for the selected keyword within the selected source lists and time window. Hover along the year axis to inspect raw yearly counts and top-cited candidate metadata.</p>'
            + render_combined_chart(data, years, title=f"{concept} Keyword Trajectory", show_legend=False)
            + "</section>"
        )
    cards = []
    modals = []
    for index, item in enumerate(series):
        color = CHART_COLORS[index % len(CHART_COLORS)]
        concept = str(item.get("concept", "Keyword"))
        total = int(item.get("total", 0) or 0)
        peak_year = item.get("peak_year") or "n/a"
        peak_count = int(item.get("peak_count", 0) or 0)
        chart = render_single_chart(item, years, color)
        single_data = {**data, "series": [item]}
        large_chart = render_combined_chart(
            single_data,
            years,
            title=f"{concept} Interactive Trajectory",
            show_legend=False,
            extra_class="modal-trend-chart",
        )
        cards.append(
            f'<a class="trend-card" href="#trend-{index}" style="--trend-color:{color}">'
            '<div class="trend-card-header">'
            "<div>"
            f'<h3 class="trend-title">{html.escape(concept)}</h3>'
            f'<span class="trend-count">{total} candidate appearances</span>'
            "</div>"
            '<span class="trend-open" title="Open enlarged chart" aria-hidden="true">&#x26F6;</span>'
            "</div>"
            + chart
            + '<div class="trend-footer">'
            f"<span>Peak: {html.escape(str(peak_year))}</span>"
            f"<span>{peak_count} papers</span>"
            "</div></a>"
        )
        modals.append(
            f'<div id="trend-{index}" class="trend-modal">'
            '<div class="trend-modal-card">'
            '<div class="trend-modal-top">'
            "<div>"
            f'<h2 style="color:{color}; margin-bottom:4px;">{html.escape(concept)}</h2>'
            f'<p class="trend-intro">{total} candidate appearances; peak {html.escape(str(peak_year))}: {peak_count} papers.</p>'
            "</div>"
            '<a class="trend-close" href="#">Close</a>'
            "</div>"
            + large_chart
            + "</div></div>"
        )
    return (
        '<section class="trend-section">'
        "<h2>Keyword Trajectories</h2>"
        '<p class="trend-intro">Each chart shows yearly candidate appearances for one keyword within the selected source lists and time window. Click a card to enlarge it.</p>'
        + render_combined_chart(data, years)
        + '<div class="trend-grid">'
        + "\n".join(cards)
        + "</div>"
        + "\n".join(modals)
        + "</section>"
    )


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    body: list[str] = []
    hero_meta: list[str] = []
    index = 0
    in_hero = False

    while index < len(lines):
        line = lines[index]
        if line.startswith("# "):
            body.append('<section class="hero">')
            in_hero = True
            body.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
            index += 1
            continue
        if in_hero and line.startswith("**") and ":**" in line:
            label, value = line.split(":**", 1)
            label = label.strip("*")
            value = value.strip().rstrip("  ")
            hero_meta.append(
                '<div class="meta-item">'
                f'<span class="meta-label">{html.escape(label)}</span>'
                f"<strong>{inline_markdown(value)}</strong>"
                "</div>"
            )
            index += 1
            continue
        if in_hero and line.startswith("## "):
            if hero_meta:
                body.append('<div class="meta-grid">' + "\n".join(hero_meta) + "</div>")
            body.append("</section>")
            in_hero = False
            continue
        if line.startswith("## "):
            heading = line[3:].strip()
            body.append(
                f'<section class="section" id="{slugify_fragment(heading)}">'
                f"<h2>{html.escape(heading)}</h2>"
            )
            index += 1
            continue
        if line.startswith("### "):
            title = line[4:].strip()
            table_index = index + 1
            while table_index < len(lines) and not lines[table_index].strip():
                table_index += 1
            if table_index < len(lines) and lines[table_index].startswith("| Field |"):
                fields, index = parse_field_table(lines, table_index)
                body.append('<article class="article">')
                body.append('<div class="article-header">')
                body.append(f"<h3>{html.escape(repair_mojibake(title))}</h3>")
                body.append(article_badges(fields))
                body.append("</div>")
                body.append('<div class="article-content">')
                body.append(render_fields(fields))
                body.append("</div>")
                body.append("</article>")
                continue
            body.append('<article class="article">')
            body.append('<div class="article-header">')
            body.append(f"<h3>{html.escape(repair_mojibake(title))}</h3>")
            body.append("</div>")
            index += 1
            continue
        if line.startswith("> "):
            body.append(f'<p class="note">{inline_markdown(line[2:].strip())}</p>')
            index += 1
            continue
        if line.startswith("| Metric |"):
            table_lines = [line]
            index += 1
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            rows = []
            for row in table_lines[2:]:
                cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
                if len(cells) >= 2:
                    rows.append(
                        '<div class="stat-card">'
                        f'<span class="stat-label">{html.escape(cells[0])}</span>'
                        f'<span class="stat-value">{html.escape(cells[1])}</span>'
                        "</div>"
                    )
            body.append('<div class="stats-grid">')
            body.append("\n".join(rows))
            body.append("</div>")
            continue
        if line.startswith("| "):
            table_lines = [line]
            index += 1
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            body.append(render_generic_table(table_lines))
            continue
        if line.strip():
            paragraph_class = "empty-note" if line.startswith("No matched articles") else ""
            class_attr = f' class="{paragraph_class}"' if paragraph_class else ""
            body.append(f"<p{class_attr}>{inline_markdown(line.strip())}</p>")
        index += 1

    if in_hero:
        if hero_meta:
            body.append('<div class="meta-grid">' + "\n".join(hero_meta) + "</div>")
        body.append("</section>")

    return "\n".join(body)


def render(markdown_path: Path, output_path: Path) -> None:
    title = "OBHRM Weekly Literature Report"
    content = markdown_path.read_text(encoding="utf-8")
    html_body = markdown_to_html(content)
    trend_html = render_keyword_trends(markdown_path.with_name("obhrm_keyword_trends.json"))
    keyword_nav_html = render_keyword_nav(content)
    if trend_html:
        html_body = html_body.replace(
            "</section>",
            "</section>\n" + trend_html + keyword_nav_html,
            1,
        )
    elif keyword_nav_html:
        html_body = html_body.replace("</section>", "</section>\n" + keyword_nav_html, 1)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{STYLE}</style>
</head>
<body>
  <main>
{html_body}
  </main>
{REPORT_SCRIPT}
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render report Markdown as HTML.")
    parser.add_argument("--input", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.input.with_suffix(".html")
    render(args.input, output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
