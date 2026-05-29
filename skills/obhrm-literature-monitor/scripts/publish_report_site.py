"""Publish a rendered HTML literature report into the Netlify static site."""

from __future__ import annotations

import argparse
import html
import re
from datetime import datetime
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
  display: block;
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


def report_entries(site_dir: Path) -> list[tuple[str, str, str]]:
    reports_dir = site_dir / "reports"
    entries: list[tuple[str, str, str]] = []
    for index_path in sorted(reports_dir.glob("*/index.html"), reverse=True):
        text = index_path.read_text(encoding="utf-8")
        rel = index_path.parent.relative_to(site_dir).as_posix() + "/"
        title = extract_title(text)
        window = extract_window(text)
        entries.append((rel, title, window))
    return entries


def render_site_index(site_dir: Path) -> None:
    entries = report_entries(site_dir)
    if entries:
        cards = "\n".join(
            '<a class="report-card" href="{href}">'
            '<span class="report-title">{title}</span>'
            '<span class="report-meta">{meta}</span>'
            "</a>".format(
                href=html.escape(href),
                title=html.escape(title),
                meta=html.escape(meta or "Open report"),
            )
            for href, title, meta in entries
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


def publish_report(input_path: Path, site_dir: Path, slug: str | None) -> Path:
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
    render_site_index(site_dir)
    return target_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish an HTML report to the Netlify site directory.")
    parser.add_argument("--input", type=Path, required=True, help="Rendered HTML report to publish.")
    parser.add_argument("--site-dir", type=Path, default=DEFAULT_SITE_DIR)
    parser.add_argument("--slug", help="Optional public URL slug under site/reports/.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = publish_report(args.input, args.site_dir, args.slug)
    print(f"Published {target}")
    print(f"Site index: {args.site_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
