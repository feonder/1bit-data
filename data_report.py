"""Generate HTML reports of network usage (daily/monthly/yearly + app drill-down)."""
import sys
import os
import re
import tempfile
import subprocess
import json
import html
import hashlib
from datetime import date, timedelta

import data_tracker as dt
import i18n
from i18n import t


MULTI_PART_TLDS = {
    "co.uk", "ac.uk", "gov.uk", "org.uk", "net.uk",
    "com.tr", "net.tr", "org.tr", "edu.tr", "gov.tr",
    "co.jp", "ne.jp", "ac.jp", "or.jp",
    "com.au", "net.au", "org.au", "edu.au",
    "com.br", "net.br", "org.br",
    "co.kr", "ne.kr", "or.kr",
    "co.za", "co.nz",
}

ISP_SUFFIX_RE = re.compile(
    r"[,\s]+(Inc\.?|LLC|Ltd\.?|Limited|Corporation|Corp\.?|GmbH|S\.A\.?|B\.V\.?|S\.r\.l\.?|AG|"
    r"Pty Ltd|Co\.,? Ltd\.?|Co\.?|A\.?S\.?)\.?\s*$",
    re.IGNORECASE,
)


def _registrable_domain(hostname):
    if not hostname:
        return ""
    parts = hostname.lower().rstrip(".").split(".")
    if len(parts) < 2:
        return hostname
    last_two = ".".join(parts[-2:])
    if last_two in MULTI_PART_TLDS and len(parts) >= 3:
        return ".".join(parts[-3:])
    return last_two


def _clean_isp(isp):
    if not isp:
        return ""
    cleaned = ISP_SUFFIX_RE.sub("", isp).strip(" ,.")
    return cleaned or isp


def _service_for_ip(ip, meta):
    """Derive a service identifier from DNS + GeoIP metadata."""
    m = meta.get(ip, {}) if meta else {}
    hostname = m.get("hostname")
    if hostname:
        dom = _registrable_domain(hostname)
        if dom:
            return dom
    isp = m.get("isp")
    if isp:
        return _clean_isp(isp)
    if ip.startswith("local") or ip in ("unknown", "ipv6_or_other"):
        return "Yerel / Bilinmiyor"
    return ip


def fmt_bytes(n):
    if n is None:
        n = 0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"


def _date_range(period):
    today = date.today()
    if period == "daily":
        return today.isoformat(), today.isoformat(), t("report.period.today")
    if period == "monthly":
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat(), t("report.period.month", m=start.strftime("%B %Y"))
    if period == "yearly":
        start = today.replace(month=1, day=1)
        return start.isoformat(), today.isoformat(), t("report.period.year", y=today.year)
    if period == "last30":
        start = today - timedelta(days=29)
        return start.isoformat(), today.isoformat(), t("report.period.last30")
    raise ValueError(f"Unknown period: {period}")


def _slug(s):
    h = hashlib.md5(s.encode("utf-8")).hexdigest()[:8]
    return h


_tbl_counter = [0]


def _next_table_id():
    _tbl_counter[0] += 1
    return f"tbl_{_tbl_counter[0]}"


def _see_more_button(table_id, hidden_count):
    more_lbl = t("btn.show_more", n=hidden_count)
    less_lbl = t("btn.show_less")
    return (
        f'<button class="see-more" data-target="#{table_id}" '
        f'data-more-label="{html.escape(more_lbl)}" data-less-label="{html.escape(less_lbl)}">'
        f'{html.escape(more_lbl)}</button>'
    )


# ---------- Shared CSS / JS helpers ----------

CSS = """
  * { box-sizing: border-box; }
  body {
    font-family: "JetBrains Mono", "SF Mono", Menlo, Monaco, monospace;
    background: #0a0e0a;
    color: #00ff66;
    margin: 0;
    padding: 24px;
    font-size: 13px;
    line-height: 1.5;
  }
  body::after {
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
      0deg, transparent 0, transparent 2px,
      rgba(0,0,0,0.18) 2px, rgba(0,0,0,0.18) 3px
    );
    z-index: 1;
  }
  .wrap { max-width: 1200px; margin: 0 auto; position: relative; z-index: 2; }
  h1 {
    font-size: 18px;
    margin: 0 0 4px;
    color: #00ff66;
    font-weight: normal;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  h1::before { content: "> "; color: #00ff66; }
  .subtitle {
    color: #5a8a5a;
    margin-bottom: 24px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .back {
    display: inline-block;
    color: #ffaa00;
    text-decoration: none;
    font-size: 12px;
    margin-bottom: 16px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .back:hover { color: #ffd066; text-decoration: underline; }
  .summary {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  .stat {
    background: transparent;
    padding: 14px 16px;
    border: 1px solid #1a5a1a;
    border-radius: 0;
  }
  .stat .label {
    font-size: 10px;
    color: #5a8a5a;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .stat .value { font-size: 20px; font-weight: normal; color: #ffaa00; }
  .stat .sub { font-size: 10px; color: #5a8a5a; margin-top: 4px; text-transform: uppercase; }
  .card {
    background: transparent;
    border: 1px solid #1a5a1a;
    border-radius: 0;
    padding: 16px 20px 20px;
    margin-bottom: 16px;
    box-shadow: none;
  }
  .card h2 {
    margin: 0 0 14px;
    font-size: 12px;
    color: #00ff66;
    font-weight: normal;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 1px dashed #1a5a1a;
    padding-bottom: 8px;
  }
  .card h2::before { content: "[ "; color: #5a8a5a; }
  .card h2::after { content: " ]"; color: #5a8a5a; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; font-family: inherit; }
  th, td {
    text-align: left;
    padding: 6px 8px;
    border-bottom: 1px dashed #1a3a1a;
  }
  th {
    color: #5a8a5a;
    font-weight: normal;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #1a5a1a;
  }
  td { color: #00cc55; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; color: #ffaa00; }
  .bar {
    display: inline-block;
    height: 4px;
    background: #00ff66;
    border-radius: 0;
    vertical-align: middle;
    margin-right: 8px;
  }
  .chart-wrap { position: relative; height: 280px; }
  .chart-wrap.tall { height: 320px; }
  .empty {
    color: #5a8a5a;
    text-align: center;
    padding: 40px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 11px;
  }
  a.app-link { color: #ffaa00; text-decoration: none; }
  a.app-link:hover { color: #ffd066; text-decoration: underline; }
  .cc { color: #ffaa00; font-size: 10px; margin-right: 6px; letter-spacing: 0.05em; }
  .geo { color: #5a8a5a; font-size: 10px; margin-left: 6px; text-transform: uppercase; }
  .host { color: #00ff66; }
  .ip { color: #5a8a5a; font-family: inherit; font-size: 10px; margin-left: 6px; }
  code { font-family: inherit; color: #00cc55; }

  /* Heatmap */
  .heatmap-wrap { overflow-x: auto; padding-bottom: 8px; }
  .heatmap {
    display: grid;
    grid-template-columns: 80px repeat(24, 1fr);
    gap: 1px;
    min-width: 700px;
  }
  .hm-header, .hm-rowlabel {
    font-size: 9px;
    color: #5a8a5a;
    text-align: center;
    padding: 2px;
    text-transform: uppercase;
  }
  .hm-rowlabel { text-align: right; padding-right: 8px; }
  .hm-cell {
    aspect-ratio: 1.2;
    background: #0f1a0f;
    border-radius: 0;
    cursor: default;
    min-height: 14px;
  }
  .hm-legend {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    font-size: 10px;
    color: #5a8a5a;
    text-transform: uppercase;
  }
  .hm-legend .swatch {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 0;
  }

  /* Collapsible tables */
  table.collapsible tr.hidden-extra { display: none; }
  table.collapsible.expanded tr.hidden-extra { display: table-row; }
  .see-more {
    display: block;
    width: 100%;
    background: transparent;
    border: 1px dashed #1a5a1a;
    color: #ffaa00;
    font-family: inherit;
    font-size: 11px;
    padding: 8px 16px;
    margin-top: 10px;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    transition: all 0.15s;
  }
  .see-more:hover {
    background: rgba(0, 255, 102, 0.06);
    border-color: #00ff66;
    color: #00ff66;
  }
  .see-more:active { transform: translateY(1px); }

  /* Scrollbar (Webkit) */
  ::-webkit-scrollbar { width: 10px; height: 10px; }
  ::-webkit-scrollbar-track { background: #0a0e0a; }
  ::-webkit-scrollbar-thumb { background: #1a5a1a; border-radius: 0; }
  ::-webkit-scrollbar-thumb:hover { background: #00ff66; }

  @media (max-width: 800px) {
    .summary { grid-template-columns: 1fr; }
    .grid2 { grid-template-columns: 1fr; }
  }
"""

CHART_JS = """
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.see-more');
  if (!btn) return;
  const sel = btn.dataset.target;
  const table = document.querySelector(sel);
  if (!table) return;
  const isExpanded = table.classList.toggle('expanded');
  btn.textContent = isExpanded ? btn.dataset.lessLabel : btn.dataset.moreLabel;
});

Chart.defaults.color = '#5a8a5a';
Chart.defaults.borderColor = '#1a5a1a';
Chart.defaults.font.family = '"JetBrains Mono", "SF Mono", Menlo, Monaco, monospace';
Chart.defaults.font.size = 10;

const TERM_PALETTE = [
  '#00ff66','#ffaa00','#39d0d8','#ff79c6','#00cc55',
  '#cc8800','#2da0a8','#cc6699','#008833','#664400'
];

function fmtBytes(n) {
  const units = ['B','KB','MB','GB','TB'];
  let i = 0;
  while (n >= 1024 && i < units.length-1) { n /= 1024; i++; }
  return n.toFixed(2) + ' ' + units[i];
}
function makeDoughnut(elId, labels, totals) {
  if (!labels.length) return;
  new Chart(document.getElementById(elId), {
    type: 'doughnut',
    data: { labels: labels, datasets: [{ data: totals,
      backgroundColor: TERM_PALETTE, borderColor: '#0a0e0a', borderWidth: 2 }]},
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'right',
        labels: { color: '#00cc55', font: { size: 10, family: Chart.defaults.font.family } } },
        tooltip: { callbacks: { label: (c) => c.label + ': ' + fmtBytes(c.parsed) } } } }
  });
}
function makeTrend(elId, labels, down, up) {
  if (!labels.length) return;
  new Chart(document.getElementById(elId), {
    type: 'line',
    data: { labels: labels, datasets: [
      { label: window.__lblDl || 'DOWNLOAD', data: down, borderColor: '#00ff66',
        backgroundColor: 'rgba(0,255,102,0.12)', fill: true, tension: 0.2,
        pointRadius: 2, pointBackgroundColor: '#00ff66' },
      { label: window.__lblUl || 'UPLOAD', data: up, borderColor: '#ffaa00',
        backgroundColor: 'rgba(255,170,0,0.10)', fill: true, tension: 0.2,
        pointRadius: 2, pointBackgroundColor: '#ffaa00' }
    ]},
    options: { responsive: true, maintainAspectRatio: false,
      scales: {
        y: { ticks: { callback: (v) => fmtBytes(v), color: '#5a8a5a' },
             grid: { color: '#1a3a1a' } },
        x: { ticks: { color: '#5a8a5a' }, grid: { color: '#1a3a1a' } }
      },
      plugins: {
        legend: { labels: { color: '#00cc55' } },
        tooltip: { callbacks: {
          label: (c) => c.dataset.label + ': ' + fmtBytes(c.parsed.y)
        } } } }
  });
}
function makeHourBar(elId, totals) {
  new Chart(document.getElementById(elId), {
    type: 'bar',
    data: { labels: [...Array(24).keys()].map(h => String(h).padStart(2,'0')),
      datasets: [{ data: totals, backgroundColor: '#00ff66', borderRadius: 0 }] },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (c) => fmtBytes(c.parsed.y) } } },
      scales: {
        y: { ticks: { callback: (v) => fmtBytes(v), color: '#5a8a5a' },
             grid: { color: '#1a3a1a' } },
        x: { ticks: { color: '#5a8a5a' }, grid: { color: '#0a0e0a' } }
      } }
  });
}
"""


def _render_remotes_table(remotes, meta, visible=10):
    if not remotes:
        return f'<div class="empty">{t("misc.no_data")}</div>'
    max_total = max(r[1] for r in remotes) if remotes else 1
    rows = []
    for i, (remote, total, b_in, b_out) in enumerate(remotes):
        pct = (total / max_total * 100) if max_total else 0
        m = meta.get(remote, {})
        hostname = m.get("hostname")
        cc = (m.get("country_code") or "").upper()
        country = m.get("country") or ""
        city = m.get("city") or ""
        cc_tag = f'<span class="cc">[{html.escape(cc)}]</span> ' if cc else ""
        geo_str = ""
        if country or city:
            geo_str = f' <span class="geo">{html.escape((city + ", " if city else "") + country)}</span>'
        if hostname:
            name_html = (f'{cc_tag}<span class="host">{html.escape(hostname)}</span>'
                         f'<span class="ip">{html.escape(remote)}</span>{geo_str}')
        else:
            name_html = f'{cc_tag}<code>{html.escape(remote)}</code>{geo_str}'
        cls = ' class="hidden-extra"' if i >= visible else ""
        rows.append(f"""
            <tr{cls}>
              <td><span class="bar" style="width:{pct*0.6:.0f}px"></span>{name_html}</td>
              <td class="num">{fmt_bytes(total)}</td>
              <td class="num" style="color:#39d0d8">↓ {fmt_bytes(b_in)}</td>
              <td class="num" style="color:#ff79c6">↑ {fmt_bytes(b_out)}</td>
            </tr>
        """)
    tbl_id = _next_table_id()
    table_html = f"""
        <table id="{tbl_id}" class="collapsible">
          <thead><tr><th>{t("table.target")}</th><th class="num">{t("table.total")}</th>
          <th class="num">{t("table.fetched")}</th><th class="num">{t("table.sent")}</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
    """
    hidden = max(0, len(remotes) - visible)
    if hidden > 0:
        table_html += _see_more_button(tbl_id, hidden)
    return table_html


def _render_services_table(services, visible=10, hard_limit=100):
    if not services:
        return f'<div class="empty">{t("misc.no_data")}</div>'
    top = services[:hard_limit]
    max_total = max(s[1] for s in top) if top else 1
    rows = []
    for i, (svc, total, b_in, b_out) in enumerate(top):
        pct = (total / max_total * 100) if max_total else 0
        cls = ' class="hidden-extra"' if i >= visible else ""
        rows.append(f"""
            <tr{cls}>
              <td><span class="bar" style="width:{pct*0.6:.0f}px"></span>{html.escape(svc)}</td>
              <td class="num">{fmt_bytes(total)}</td>
              <td class="num" style="color:#39d0d8">↓ {fmt_bytes(b_in)}</td>
              <td class="num" style="color:#ff79c6">↑ {fmt_bytes(b_out)}</td>
            </tr>
        """)
    tbl_id = _next_table_id()
    table_html = f"""
        <table id="{tbl_id}" class="collapsible">
          <thead><tr><th>{t("table.service")}</th><th class="num">{t("table.total")}</th>
          <th class="num">{t("table.download")}</th><th class="num">{t("table.upload")}</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
    """
    hidden = max(0, len(top) - visible)
    if hidden > 0:
        table_html += _see_more_button(tbl_id, hidden)
    return table_html


def _render_networks_table(networks):
    if not networks:
        return f'<div class="empty">{t("misc.no_network_data")}</div>'
    max_total = max(n[1] for n in networks) if networks else 1
    rows = []
    for net, total, b_in, b_out in networks:
        pct = (total / max_total * 100) if max_total else 0
        label = net or t("misc.untracked")
        rows.append(f"""
            <tr>
              <td><span class="bar" style="width:{pct*0.6:.0f}px"></span>{html.escape(label)}</td>
              <td class="num">{fmt_bytes(total)}</td>
              <td class="num" style="color:#39d0d8">↓ {fmt_bytes(b_in)}</td>
              <td class="num" style="color:#ff79c6">↑ {fmt_bytes(b_out)}</td>
            </tr>
        """)
    return f"""
        <table>
          <thead><tr><th>{t("table.network")}</th><th class="num">{t("table.total")}</th>
          <th class="num">{t("table.download")}</th><th class="num">{t("table.upload")}</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_apps_table(apps, app_links=None, visible=10):
    if not apps:
        return f'<div class="empty">{t("misc.no_data")}</div>'
    max_total = max(a[1] for a in apps) if apps else 1
    rows = []
    for i, (app, total, b_in, b_out) in enumerate(apps):
        pct = (total / max_total * 100) if max_total else 0
        if app_links and app in app_links:
            name_html = f'<a class="app-link" href="{html.escape(app_links[app])}">{html.escape(app)}</a>'
        else:
            name_html = html.escape(app)
        cls = ' class="hidden-extra"' if i >= visible else ""
        rows.append(f"""
            <tr{cls}>
              <td><span class="bar" style="width:{pct*0.6:.0f}px"></span>{name_html}</td>
              <td class="num">{fmt_bytes(total)}</td>
              <td class="num" style="color:#39d0d8">↓ {fmt_bytes(b_in)}</td>
              <td class="num" style="color:#ff79c6">↑ {fmt_bytes(b_out)}</td>
            </tr>
        """)
    tbl_id = _next_table_id()
    table_html = f"""
        <table id="{tbl_id}" class="collapsible">
          <thead><tr><th>{t("table.app")}</th><th class="num">{t("table.total")}</th>
          <th class="num">{t("table.download")}</th><th class="num">{t("table.upload")}</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
    """
    hidden = max(0, len(apps) - visible)
    if hidden > 0:
        table_html += _see_more_button(tbl_id, hidden)
    return table_html


def _render_heatmap(hourly_rows, max_days=45):
    """hourly_rows: [(date, hour, b_in, b_out)]. Render last N days × 24 hours."""
    if not hourly_rows:
        return f'<div class="empty">{t("misc.no_data")}</div>'

    # Aggregate by (date, hour)
    grid = {}
    dates = set()
    for d, h, b_in, b_out in hourly_rows:
        grid[(d, h)] = (b_in or 0) + (b_out or 0)
        dates.add(d)

    # Sort dates desc, take last N
    sorted_dates = sorted(dates, reverse=True)[:max_days]
    sorted_dates.reverse()  # show oldest at top

    max_val = max(grid.values()) if grid else 1

    def color(val):
        if val <= 0:
            return "#0f1a0f"
        intensity = min(1.0, (val / max_val) ** 0.5)
        return f"rgba(0, 255, 102, {0.18 + intensity * 0.82:.2f})"

    cells = ['<div class="hm-rowlabel"></div>']
    for h in range(24):
        cells.append(f'<div class="hm-header">{h:02d}</div>')

    for d in sorted_dates:
        cells.append(f'<div class="hm-rowlabel">{html.escape(d[5:])}</div>')
        for h in range(24):
            v = grid.get((d, h), 0)
            label = f"{d} {h:02d}:00 — {fmt_bytes(v)}"
            cells.append(
                f'<div class="hm-cell" style="background:{color(v)}" title="{html.escape(label)}"></div>'
            )

    legend = (
        f'<div class="hm-legend">{html.escape(t("misc.low"))} '
        '<span class="swatch" style="background:rgba(0,255,102,0.18)"></span>'
        '<span class="swatch" style="background:rgba(0,255,102,0.4)"></span>'
        '<span class="swatch" style="background:rgba(0,255,102,0.7)"></span>'
        f'<span class="swatch" style="background:rgba(0,255,102,1)"></span> {html.escape(t("misc.high"))}</div>'
    )

    return f'<div class="heatmap-wrap"><div class="heatmap">{"".join(cells)}</div></div>{legend}'


def _trend_section(daily, canvas_id="trendChart"):
    if not daily or len(daily) < 2:
        return ""
    return f"""
    <div class="card">
      <h2>{html.escape(t("section.daily_trend"))}</h2>
      <div class="chart-wrap"><canvas id="{canvas_id}"></canvas></div>
    </div>
    """


def _hour_section(hour_totals, canvas_id="hourBar"):
    """24-hour bar chart of usage by hour-of-day."""
    if not hour_totals:
        return ""
    totals = [0] * 24
    for h, b_in, b_out in hour_totals:
        if h is not None and 0 <= h < 24:
            totals[h] = (b_in or 0) + (b_out or 0)
    if sum(totals) == 0:
        return ""
    return f"""
    <div class="card">
      <h2>{html.escape(t("section.hour_usage"))}</h2>
      <div class="chart-wrap"><canvas id="{canvas_id}"></canvas></div>
      <script>window.__hourTotals_{canvas_id} = {json.dumps(totals)};</script>
    </div>
    """


# ---------- Main report ----------

def _write_html(path, body, scripts=""):
    lang = i18n.get_lang()
    doc = f"""<!DOCTYPE html>
<html lang="{lang}"><head>
<meta charset="utf-8">
<title>{html.escape(t("report.title"))}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>{CSS}</style>
</head>
<body>{body}
<script>{CHART_JS}
{scripts}</script>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)


def _make_app_subpage(out_dir, app, start, end, app_link_back=None):
    """Generate per-app drill-down page. Returns filename.
    If app_link_back is None, page is standalone (no back link)."""
    total_in, total_out = dt.app_total(app, start, end)
    total = (total_in or 0) + (total_out or 0)
    remotes = dt.app_top_remotes(app, start, end, limit=50)
    daily = dt.app_daily_trend(app, start, end)
    hourly = dt.app_hourly_buckets(app, start, end)

    remote_ips = [r[0] for r in remotes]
    meta = dt.get_remote_meta(remote_ips)

    # hour-of-day aggregate
    hour_totals = [0] * 24
    for _, h, b_in, b_out in hourly:
        if h is not None and 0 <= h < 24:
            hour_totals[h] += (b_in or 0) + (b_out or 0)

    fname = f"app_{_slug(app)}.html"

    back_html = ""
    if app_link_back:
        back_html = (f'<a class="back" href="{html.escape(app_link_back)}">'
                     f'{html.escape(t("report.back"))}</a>')
    body = f"""
<div class="wrap">
  {back_html}
  <h1>{html.escape(app)}</h1>
  <div class="subtitle">{start} -&gt; {end}</div>

  <div class="summary">
    <div class="stat"><div class="label">{html.escape(t("stat.total"))}</div>
      <div class="value">{fmt_bytes(total)}</div></div>
    <div class="stat"><div class="label">{html.escape(t("stat.downloaded"))}</div>
      <div class="value">↓ {fmt_bytes(total_in or 0)}</div></div>
    <div class="stat"><div class="label">{html.escape(t("stat.uploaded"))}</div>
      <div class="value">↑ {fmt_bytes(total_out or 0)}</div></div>
  </div>

  {_trend_section(daily, "appTrend")}

  <div class="card">
    <h2>{html.escape(t("section.hour_usage"))}</h2>
    <div class="chart-wrap"><canvas id="appHourBar"></canvas></div>
  </div>

  <div class="card">
    <h2>{html.escape(t("section.heatmap"))}</h2>
    {_render_heatmap(hourly)}
  </div>

  <div class="card">
    <h2>{html.escape(t("section.app_targets", app=app))}</h2>
    {_render_remotes_table(remotes, meta)}
  </div>
</div>
"""
    scripts = f"""
window.__lblDl = {json.dumps(t("chart.download"))};
window.__lblUl = {json.dumps(t("chart.upload"))};
makeTrend('appTrend', {json.dumps([d[0] for d in daily])},
  {json.dumps([d[1] for d in daily])}, {json.dumps([d[2] for d in daily])});
makeHourBar('appHourBar', {json.dumps(hour_totals)});
"""
    path = os.path.join(out_dir, fname)
    _write_html(path, body, scripts)
    return fname


def generate(period):
    dt.init_db()
    start, end, title = _date_range(period)

    total_in, total_out = dt.total_range(start, end)
    total = (total_in or 0) + (total_out or 0)

    apps_top10 = dt.top_apps_range(start, end, limit=10)
    apps_all = dt.top_apps_range(start, end, limit=50)
    remotes = dt.top_remotes_range(start, end, limit=40)
    daily = dt.daily_totals_range(start, end)
    hourly = dt.hourly_buckets_range(start, end)
    hour_totals_rows = dt.hour_of_day_totals(start, end)

    remote_ips = [r[0] for r in remotes]
    meta = dt.get_remote_meta(remote_ips)

    # Aggregate by service across ALL remotes in range (not just top 40)
    all_remotes = dt.top_remotes_range(start, end, limit=10000)
    all_remote_ips = [r[0] for r in all_remotes]
    all_meta = dt.get_remote_meta(all_remote_ips)
    service_agg = {}
    for ip, total, b_in, b_out in all_remotes:
        svc = _service_for_ip(ip, all_meta)
        bucket = service_agg.setdefault(svc, [0, 0, 0])
        bucket[0] += total
        bucket[1] += b_in or 0
        bucket[2] += b_out or 0
    services = sorted(
        ([svc, vals[0], vals[1], vals[2]] for svc, vals in service_agg.items()),
        key=lambda x: -x[1],
    )

    networks = dt.top_networks_range(start, end, limit=20)

    out_dir = tempfile.mkdtemp(prefix=f"data_report_{period}_")
    main_path = os.path.join(out_dir, "index.html")

    # Generate sub-pages for top 20 apps
    app_links = {}
    for app, _, _, _ in apps_all[:20]:
        fname = _make_app_subpage(out_dir, app, start, end, "index.html")
        app_links[app] = fname

    # hour-of-day for main page
    hour_totals = [0] * 24
    for h, b_in, b_out in hour_totals_rows:
        if h is not None and 0 <= h < 24:
            hour_totals[h] = (b_in or 0) + (b_out or 0)

    body = f"""
<div class="wrap">
  <h1>{html.escape(t("report.title"))}</h1>
  <div class="subtitle">{html.escape(title)} . {start} -&gt; {end}</div>

  <div class="summary">
    <div class="stat"><div class="label">{html.escape(t("stat.total_data"))}</div>
      <div class="value">{fmt_bytes(total)}</div>
      <div class="sub">{html.escape(t("stat.sub.dl_ul"))}</div></div>
    <div class="stat"><div class="label">{html.escape(t("stat.downloaded"))}</div>
      <div class="value">↓ {fmt_bytes(total_in or 0)}</div></div>
    <div class="stat"><div class="label">{html.escape(t("stat.uploaded"))}</div>
      <div class="value">↑ {fmt_bytes(total_out or 0)}</div></div>
  </div>

  {_trend_section(daily)}

  <div class="card">
    <h2>{html.escape(t("section.hour_usage_total"))}</h2>
    <div class="chart-wrap"><canvas id="hourBar"></canvas></div>
  </div>

  <div class="card">
    <h2>{html.escape(t("section.heatmap"))}</h2>
    {_render_heatmap(hourly)}
  </div>

  <div class="grid2">
    <div class="card">
      <h2>{html.escape(t("section.top_apps"))}</h2>
      <div class="chart-wrap"><canvas id="appsChart"></canvas></div>
    </div>
    <div class="card">
      <h2>{html.escape(t("section.app_details"))} <span style="font-size:10px;color:#5a8a5a;font-weight:normal">{t("section.click_for_details")}</span></h2>
      {_render_apps_table(apps_all, app_links)}
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>{html.escape(t("section.service_distribution"))}</h2>
      <div class="chart-wrap"><canvas id="svcChart"></canvas></div>
    </div>
    <div class="card">
      <h2>{html.escape(t("section.service_details"))}</h2>
      {_render_services_table(services)}
    </div>
  </div>

  <div class="card">
    <h2>{html.escape(t("section.network_usage"))}</h2>
    {_render_networks_table(networks)}
  </div>

  <div class="card">
    <h2>{html.escape(t("section.destinations"))}</h2>
    {_render_remotes_table(remotes, meta)}
  </div>
</div>
"""

    top_services = services[:10]
    scripts = f"""
window.__lblDl = {json.dumps(t("chart.download"))};
window.__lblUl = {json.dumps(t("chart.upload"))};
makeDoughnut('appsChart',
  {json.dumps([a[0] for a in apps_top10])},
  {json.dumps([a[1] for a in apps_top10])});
makeDoughnut('svcChart',
  {json.dumps([s[0] for s in top_services])},
  {json.dumps([s[1] for s in top_services])});
makeTrend('trendChart',
  {json.dumps([d[0] for d in daily])},
  {json.dumps([d[1] for d in daily])},
  {json.dumps([d[2] for d in daily])});
makeHourBar('hourBar', {json.dumps(hour_totals)});
"""

    _write_html(main_path, body, scripts)
    return main_path


def open_report(period):
    path = generate(period)
    subprocess.run(["open", path])
    return path


def open_app_report(app_name, period="daily"):
    """Generate and open a standalone app drill-down report."""
    dt.init_db()
    start, end, _ = _date_range(period)
    out_dir = tempfile.mkdtemp(prefix="data_app_")
    fname = _make_app_subpage(out_dir, app_name, start, end, app_link_back=None)
    path = os.path.join(out_dir, fname)
    subprocess.run(["open", path])
    return path


if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "daily"
    path = open_report(period)
    print(f"Opened: {path}")
