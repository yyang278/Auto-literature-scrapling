"""Render an OBHRM Markdown report into a standalone HTML file."""

from __future__ import annotations

import argparse
import html
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
  max-width: 78ch;
  margin: 0;
  color: #263244;
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
}
"""


def repair_mojibake(text: str) -> str:
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


def render_fields(fields: list[tuple[str, str]]) -> str:
    chunks = []
    rows = []

    def flush_rows() -> None:
        nonlocal rows
        if rows:
            chunks.append('<table class="field-table">' + "\n".join(rows) + "</table>")
            rows = []

    for name, value in fields:
        if name == "Abstract status":
            status = value.strip().lower()
            badge_class = "missing" if status == "missing" else "available"
            value_html = f'<span class="badge {badge_class}">{html.escape(value)}</span>'
        elif name == "Abstract":
            flush_rows()
            chunks.append(
                '<div class="abstract-block">'
                f'<span class="abstract-label">{html.escape(name)}</span>'
                f'<p class="abstract-text">{inline_markdown(value)}</p>'
                "</div>"
            )
            continue
        else:
            value_html = inline_markdown(value)
        rows.append(
            "<tr>"
            f'<td class="field-name">{html.escape(name)}</td>'
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
            body.append(f'<section class="section"><h2>{html.escape(line[3:].strip())}</h2>')
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
