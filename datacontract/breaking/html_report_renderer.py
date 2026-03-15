"""
html_report_renderer — HTML renderer for ODCS data contract diffs
----------------------------------------------------------------
Produces a self-contained HTML report from a report_data diff dict,
including a Change Summary section and a Change Details table with
depth-based indentation.

ContractDiffReport.build_report_data() produces the report_data dict.

Usage:
    from report_renderer import ContractDiffReport
    from html_report_renderer import HtmlContractDiffRenderer
    from diff import ContractDiff

    contracts_diff = ContractDiff().generate("v1.yaml", "v2.yaml")
    report_data = ContractDiffReport().build_report_data(
        contracts_diff, source_label="v1.yaml", target_label="v2.yaml",
    )
    html = HtmlContractDiffRenderer(report_data=report_data).render()
"""

from __future__ import annotations

import html as _html
from typing import Any

from datacontract.breaking.helpers import LIST_CONTAINERS


def _e(s: Any) -> str:
    """HTML-escape a value."""
    return _html.escape(str(s))


def _format_value(val: Any, max_len: int = None) -> str:
    if val is None:
        return ""
    if isinstance(val, dict):
        keys = list(val.keys())
        summary = f"{{ {', '.join(keys[:4])}{'...' if len(keys) > 4 else ''} }}"
        return f'<span class="obj">{_e(summary)}</span>'
    s = str(val)
    # Remove truncation - let HTML handle wrapping naturally
    return _e(s)


def _pill(change_type: str) -> str:
    """Render a change-type pill. Accepts 'added', 'removed', or 'changed'."""
    label = {"added": "Added", "removed": "Removed", "changed": "Changed"}.get(change_type, change_type.capitalize())
    css = change_type if change_type in ("added", "removed", "changed") else "changed"
    return f'<span class="pill {css}">{label}</span>'


def _path_td(key: str, depth: int, is_list_item: bool) -> str:
    """Build a <td> for the path column with depth-based indentation."""
    pad = f"padding-left:calc(14px + {depth * 2}ch)"
    label = f"- {_e(key)}" if is_list_item else _e(key)
    return f'<td class="path" style="{pad}"><span class="key">{label}</span></td>'


def _render_detail_rows(changes: list) -> list[str]:
    """Build all <tr> rows for the detail table.
    Ancestor header rows are inferred from path at render time — not stored in dict.
    """
    explicit = {c["path"] for c in changes}
    ancestors: list[str] = []
    for c in changes:
        segs = c["path"].split(".")
        for i in range(1, len(segs)):
            anc = ".".join(segs[:i])
            if anc not in explicit:
                explicit.add(anc)
                ancestors.append(anc)

    all_entries = sorted(changes + [{"path": a, "_ancestor": True} for a in ancestors], key=lambda x: x["path"])

    rows = []
    for c in all_entries:
        segs = c["path"].split(".")
        key = segs[-1]
        depth = len(segs) - 1
        is_list_item = len(segs) > 1 and segs[-2] in LIST_CONTAINERS
        td = _path_td(key, depth, is_list_item)

        if c.get("_ancestor"):
            rows.append(f"<tr>{td}<td></td><td></td><td></td></tr>")
            continue

        change_type = c["changeType"].lower()
        pill = _pill(change_type)
        old_v = c.get("old_value")
        new_v = c.get("new_value")

        if old_v is None and new_v is None:
            rows.append(f"<tr>{td}<td>{pill}</td><td></td><td></td></tr>")
        else:
            old_html = _format_value(old_v) if old_v is not None else ""
            new_html = _format_value(new_v) if new_v is not None else ""
            rows.append(f'<tr>{td}<td>{pill}</td><td class="new">{new_html}</td><td class="old">{old_html}</td></tr>')

    return rows


# ---------------------------------------------------------------------------
# Main renderer class
# ---------------------------------------------------------------------------


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #f6f8fa;
  --surface:   #ffffff;
  --border:    #d0d7de;
  --text:      #24292f;
  --muted:     #6e7781;
  --error:     #cf222e;
  --error-bg:  #fff0ee;
  --warning:   #9a6700;
  --warning-bg:#fff8c5;
  --info:      #0969da;
  --info-bg:   #ddf4ff;
  --success:   #1a7f37;
  --success-bg:#dafbe1;
  --mono:      'IBM Plex Mono', monospace;
  --sans:      'IBM Plex Sans', sans-serif;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.6;
  padding: 40px 24px;
  min-height: 100vh;
}

.container { max-width: 1040px; margin: 0 auto; }

/* Header */
.header {
  display: flex; align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding-bottom: 24px; margin-bottom: 32px; gap: 16px;
}
.header-left h1 { font-size: 20px; font-weight: 600; letter-spacing: -0.3px; }
.header-left .subtitle { font-size: 12px; color: var(--muted); margin-top: 4px; font-family: var(--mono); }
.badges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 2px; }
.badge {
  font-size: 11px; font-family: var(--mono);
  padding: 3px 10px; border-radius: 20px; font-weight: 500; border: 1px solid;
}
.badge.error   { color: var(--error);   background: var(--error-bg);   border-color: #ffcecb; }
.badge.warning { color: var(--warning); background: var(--warning-bg); border-color: #d4a72c; }
.badge.info    { color: var(--info);    background: var(--info-bg);    border-color: #80ccff; }
.badge.success { color: var(--success); background: var(--success-bg); border-color: #aceebb; }

/* Section */
.section { margin-bottom: 32px; }
.section-title {
  font-size: 13px; font-weight: 600; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--text); margin-bottom: 12px;
}

/* Diff table */
.diff-table {
  width: 100%; border-collapse: collapse;
  font-family: var(--mono); font-size: 12px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; overflow: hidden;
}
.diff-table th {
  text-align: left; padding: 8px 14px;
  font-size: 10px; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: #444c56;
  background: #e6eaf0; border-bottom: 2px solid #c8d0da;
}
.diff-table td { padding: 6px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }
.diff-table tr:last-child td { border-bottom: none; }
/* Ultra-compact field and change columns, reduced padding for new/old */
.diff-table th:nth-child(1),
.diff-table td:nth-child(1) {
  width: 25%; /* field column - very compact */
}
.diff-table th:nth-child(2),
.diff-table td:nth-child(2) {
  width: 5%; /* change column - ultra minimal */
}
.diff-table th:nth-child(3),
.diff-table th:nth-child(4),
.diff-table td:nth-child(3),
.diff-table td:nth-child(4) {
  width: 35%; /* new and old columns - maximum space */
  padding-left: 8px;
  padding-right: 8px;
}
.diff-table .key  { color: var(--text); }
.diff-table .old  { color: var(--error); text-decoration: line-through; opacity: 0.8; }
.diff-table .new  { color: var(--success); }
/* monospace indent: each level = 2ch, dash+space = 2ch so children align exactly */
  .diff-table .path  { font-family: inherit; }

/* Pills */
.pill {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10px; font-weight: 500; padding: 2px 8px;
  border-radius: 12px; border: 1px solid; white-space: nowrap;
}
.pill.added   { color: var(--success); background: var(--success-bg); border-color: #aceebb; }
.pill.removed { color: var(--error);   background: var(--error-bg);   border-color: #ffcecb; }
.pill.changed { color: var(--warning); background: var(--warning-bg); border-color: #d4a72c; }

"""


class HtmlContractDiffRenderer:
    """
    Renders a self-contained HTML diff report from a report_data diff dict.

    Produces a header (title, source → target, generated timestamp), a
    Change Summary section with badge counts, and a Change Details table
    with depth-based indentation and colour-coded change-type pills.

    Args:
        report_data: dict returned by ContractDiffReport.build_report_data()
    """

    def __init__(self, report_data: dict):
        self.report_data = report_data

    # ---- header ----

    def _render_header(self, report_data: dict) -> str:
        h = report_data["header"]
        return f"""
        <div class="header">
          <div class="header-left">
            <h1>{_e(h["title"])}</h1>
            <div class="subtitle">{_e(h["subtitle"])}</div>
            {f'<div class="subtitle" style="margin-top:4px;">Generated: {_e(h["generated_at"])}</div>' if h.get("generated_at") else ""}
          </div>
        </div>"""

    # ---- high-level summary section ----

    def _render_summary_section(self, report_data: dict) -> str:
        counts = report_data["summary"]["counts"]
        changes = report_data["summary"]["changes"]

        badges = []
        if counts["removed"]:
            badges.append(f'<span class="badge error">{counts["removed"]} Removed</span>')
        if counts["changed"]:
            badges.append(f'<span class="badge warning">{counts["changed"]} Changed</span>')
        if counts["added"]:
            badges.append(f'<span class="badge success">{counts["added"]} Added</span>')
        badges_html = f'<div class="badges" style="margin:16px 0;">{"".join(badges)}</div>'

        rows = []
        for ch in changes:
            pill = _pill(ch["changeType"].lower())
            rows.append(f'<tr><td class="path">{_e(ch["path"])}</td><td>{pill}</td></tr>')

        total = counts["added"] + counts["removed"] + counts["changed"]
        return f"""
        <div class="section">
          <div class="section-title">Change Summary &nbsp;·&nbsp; {total} change(s)</div>
          {badges_html}
          <table class="diff-table">
            <thead><tr><th>field</th><th>change</th></tr></thead>
            <tbody>{"".join(rows)}</tbody>
          </table>
        </div>"""

    # ---- diff table ----

    def _render_diff_table(self, report_data: dict) -> str:
        changes = report_data["detail"]["changes"]
        rows = _render_detail_rows(changes)

        return f"""
        <div class="section">
          <div class="section-title">Change Details</div>
          <table class="diff-table">
            <thead>
              <tr><th>field</th><th>change</th><th>new</th><th>old</th></tr>
            </thead>
            <tbody>{"".join(rows)}</tbody>
          </table>
        </div>"""

    # ---- main render ----

    def render(self) -> str:
        report_data = self.report_data
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ODCS Diff — {_e(report_data["source_label"])} → {_e(report_data["target_label"])}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">
  {self._render_header(report_data)}
  {self._render_summary_section(report_data)}
  {self._render_diff_table(report_data)}
</div>
</body>
</html>"""
