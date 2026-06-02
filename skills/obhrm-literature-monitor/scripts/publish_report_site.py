"""Publish a rendered HTML literature report into the Netlify static site."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SITE_DIR = REPO_ROOT / "site"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


SITE_STYLE = """
:root {
  color-scheme: light;
  --ink: #172033;
  --muted: #647084;
  --line: #d9e0ea;
  --panel: #ffffff;
  --accent: #1f5fbf;
  --accent-strong: #123b77;
  --soft: #f7f9fc;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans",
    "Microsoft YaHei", Arial, sans-serif;
  color: var(--ink);
  background: linear-gradient(180deg, #f4f7fb 0%, #eef3f8 280px, #f7f9fc 100%);
  line-height: 1.55;
}
main {
  width: min(980px, calc(100% - 40px));
  margin: 42px auto 60px;
}
.hero {
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 30px 34px;
  box-shadow: 0 18px 44px rgba(24, 33, 47, 0.10);
}
h1 {
  margin: 0 0 10px;
  color: var(--accent-strong);
  font-size: 34px;
  line-height: 1.16;
}
.subtitle {
  margin: 0;
  color: var(--muted);
  max-width: 70ch;
}
.report-list {
  display: grid;
  gap: 14px;
  margin-top: 24px;
}
.report-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  text-decoration: none;
  color: inherit;
  box-shadow: 0 8px 22px rgba(24, 33, 47, 0.06);
}
.report-card:hover {
  border-color: #b7cdfb;
  transform: translateY(-1px);
}
.report-title {
  display: block;
  color: var(--accent);
  font-size: 19px;
  font-weight: 800;
}
.report-meta {
  display: block;
  color: var(--muted);
  margin-top: 5px;
  overflow-wrap: anywhere;
}
.report-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  min-width: 180px;
}
.tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 10px;
  background: #f2f6fd;
  color: var(--accent-strong);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
  white-space: nowrap;
}
.tag.time {
  background: #f5f7fa;
  color: #475467;
}
.tag.legacy {
  background: #fff7ed;
  color: #9a4b00;
}
.empty {
  margin-top: 24px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  color: var(--muted);
}
@media (max-width: 720px) {
  main { width: min(100% - 20px, 980px); margin-top: 18px; }
  .hero { padding: 22px 20px; }
  h1 { font-size: 27px; }
  .report-card {
    grid-template-columns: 1fr;
  }
  .report-tags {
    justify-content: flex-start;
    min-width: 0;
  }
}
"""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-._")
    return slug or "report"


def extract_title(html_text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return "OBHRM Weekly Literature Report"
    return html.unescape(re.sub(r"\s+", " ", match.group(1)).strip())


def sanitize_public_html(html_text: str) -> str:
    html_text = re.sub(
        r"Electronic address:\s*" + EMAIL_RE.pattern,
        "Electronic address: [email removed]",
        html_text,
        flags=re.IGNORECASE,
    )
    return EMAIL_RE.sub("[email removed]", html_text)


def extract_window(html_text: str) -> str:
    match = re.search(
        r'<span class="meta-label">Window</span><strong>(.*?)</strong>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", match.group(1)).strip())


def read_metadata(report_dir: Path) -> dict[str, str]:
    metadata_path = report_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if value is not None}


def format_run_time(value: str) -> str:
    if not value:
        return ""
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        return parsed.strftime("%Y-%m-%d %H:%M")
    utc_time = parsed.astimezone(timezone.utc)
    return utc_time.strftime("%Y-%m-%d %H:%M UTC")


def report_entries(site_dir: Path) -> list[dict[str, str]]:
    reports_dir = site_dir / "reports"
    entries: list[dict[str, str]] = []
    for index_path in sorted(reports_dir.glob("*/index.html"), reverse=True):
        text = index_path.read_text(encoding="utf-8")
        rel = index_path.parent.relative_to(site_dir).as_posix() + "/"
        title = extract_title(text)
        window = extract_window(text)
        metadata = read_metadata(index_path.parent)
        entries.append(
            {
                "href": rel,
                "title": title,
                "window": window,
                "run_actor": metadata.get("run_actor", ""),
                "run_started_at": metadata.get("run_started_at", ""),
            }
        )
    return entries


def render_report_tags(entry: dict[str, str]) -> str:
    actor = entry.get("run_actor", "").strip()
    run_time = format_run_time(entry.get("run_started_at", "").strip())
    tags: list[str] = []
    if actor:
        tags.append(f'<span class="tag">by {html.escape(actor)}</span>')
    if run_time:
        tags.append(f'<span class="tag time">run {html.escape(run_time)}</span>')
    if not tags:
        tags.append('<span class="tag legacy">legacy report</span>')
    return '<span class="report-tags">' + "".join(tags) + "</span>"


def render_site_index(site_dir: Path) -> None:
    entries = report_entries(site_dir)
    if entries:
        cards = "\n".join(
            '<a class="report-card" href="{href}">'
            '<span class="report-main">'
            '<span class="report-title">{title}</span>'
            '<span class="report-meta">{meta}</span>'
            "</span>"
            "{tags}"
            "</a>".format(
                href=html.escape(entry["href"]),
                title=html.escape(entry["title"]),
                meta=html.escape(entry["window"] or "Open report"),
                tags=render_report_tags(entry),
            )
            for entry in entries
        )
    else:
        cards = '<div class="empty">No reports have been published yet.</div>'

    generated = datetime.now().isoformat(timespec="seconds")
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OBHRM Literature Reports</title>
  <style>{SITE_STYLE}</style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>OBHRM Literature Reports</h1>
      <p class="subtitle">Weekly literature reports generated from the OBHRM/HCI/preprint target-source monitor. Generated index: {html.escape(generated)}</p>
    </section>
    <section class="report-list">
      {cards}
    </section>
  </main>
</body>
</html>
"""
    (site_dir / "index.html").write_text(document, encoding="utf-8")


def default_run_actor() -> str:
    return (
        os.environ.get("GITHUB_TRIGGERING_ACTOR")
        or os.environ.get("GITHUB_ACTOR")
        or os.environ.get("USERNAME")
        or os.environ.get("USER")
        or ""
    )


def default_run_started_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def publish_report(
    input_path: Path,
    site_dir: Path,
    slug: str | None,
    run_actor: str | None = None,
    run_started_at: str | None = None,
) -> Path:
    input_path = input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"HTML report not found: {input_path}")
    if input_path.suffix.lower() != ".html":
        raise ValueError(f"Expected an .html report, got: {input_path}")

    report_slug = slugify(slug or input_path.parent.name)
    target_dir = site_dir / "reports" / report_slug
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "index.html"
    target_path.write_text(sanitize_public_html(input_path.read_text(encoding="utf-8")), encoding="utf-8")
    metadata = {
        "run_actor": (run_actor or default_run_actor()).strip(),
        "run_started_at": (run_started_at or default_run_started_at()).strip(),
    }
    (target_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    render_site_index(site_dir)
    return target_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish an HTML report to the Netlify site directory.")
    parser.add_argument("--input", type=Path, required=True, help="Rendered HTML report to publish.")
    parser.add_argument("--site-dir", type=Path, default=DEFAULT_SITE_DIR)
    parser.add_argument("--slug", help="Optional public URL slug under site/reports/.")
    parser.add_argument("--run-actor", help="GitHub account/user that triggered this report.")
    parser.add_argument("--run-started-at", help="ISO timestamp for when this report run started.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = publish_report(args.input, args.site_dir, args.slug, args.run_actor, args.run_started_at)
    print(f"Published {target}")
    print(f"Site index: {args.site_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
