"""Data quota config + check + notification state tracking."""
import json
import os
from datetime import date, timedelta

import data_tracker as dt

QUOTAS_FILE = os.path.expanduser("~/.data_monitor_quotas.json")
STATE_FILE = os.path.expanduser("~/.data_monitor_quotas_state.json")

DEFAULT_QUOTAS = {
    "_help": [
        "Daily / monthly total limits (bytes). null = limitsiz.",
        "apps: { 'App Name': { 'period': 'daily'|'weekly'|'monthly', 'limit': bytes } }",
        "networks: { 'Network Name': { 'period': 'daily'|'monthly', 'limit': bytes } }",
        "1 GB = 1073741824 bytes, 1 MB = 1048576 bytes",
    ],
    "daily_total": None,
    "monthly_total": None,
    "apps": {},
    "networks": {},
}


def load_quotas():
    if os.path.exists(QUOTAS_FILE):
        try:
            with open(QUOTAS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    save_quotas(DEFAULT_QUOTAS)
    return DEFAULT_QUOTAS


def save_quotas(data):
    with open(QUOTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _period_bounds(period):
    today = date.today()
    if period == "daily":
        return today.isoformat(), today.isoformat(), today.isoformat()
    if period == "weekly":
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), today.isoformat(), f"W{today.isocalendar()[1]:02d}-{today.year}"
    if period == "monthly":
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat(), today.strftime("%Y-%m")
    return None, None, None


def _usage_total(start, end):
    t_in, t_out = dt.total_range(start, end)
    return (t_in or 0) + (t_out or 0)


def _usage_app(app, start, end):
    rows = dt._query(
        "SELECT SUM(bytes_in), SUM(bytes_out) FROM traffic "
        "WHERE app = ? AND date BETWEEN ? AND ?",
        (app, start, end)
    )
    if not rows or rows[0][0] is None:
        return 0
    return (rows[0][0] or 0) + (rows[0][1] or 0)


def _usage_network(network, start, end):
    rows = dt._query(
        "SELECT SUM(bytes_in), SUM(bytes_out) FROM traffic "
        "WHERE network = ? AND date BETWEEN ? AND ?",
        (network, start, end)
    )
    if not rows or rows[0][0] is None:
        return 0
    return (rows[0][0] or 0) + (rows[0][1] or 0)


def check_quotas():
    """Return list of (key, label, used, limit, pct, exceeded_bool, was_new_breach_bool)."""
    quotas = load_quotas()
    state = _load_state()
    results = []
    today = date.today().isoformat()

    def record(key_base, label, period, used, limit):
        if not limit:
            return
        start, end, period_id = _period_bounds(period)
        full_key = f"{period_id}:{key_base}"
        pct = int(round(used / limit * 100)) if limit else 0
        exceeded = used >= limit
        was_fired = state.get(full_key) is True
        is_new_breach = exceeded and not was_fired
        if exceeded:
            state[full_key] = True
        results.append({
            "key": full_key,
            "label": label,
            "period": period,
            "used": used,
            "limit": limit,
            "pct": pct,
            "exceeded": exceeded,
            "new_breach": is_new_breach,
        })

    # Daily total
    if quotas.get("daily_total"):
        s, e, _ = _period_bounds("daily")
        record("total", "Toplam (Günlük)", "daily", _usage_total(s, e), quotas["daily_total"])

    # Monthly total
    if quotas.get("monthly_total"):
        s, e, _ = _period_bounds("monthly")
        record("total", "Toplam (Aylık)", "monthly", _usage_total(s, e), quotas["monthly_total"])

    # Per-app
    for app, cfg in (quotas.get("apps") or {}).items():
        period = cfg.get("period", "daily")
        limit = cfg.get("limit")
        if not limit:
            continue
        s, e, _ = _period_bounds(period)
        if s is None:
            continue
        record(f"app:{app}", app, period, _usage_app(app, s, e), limit)

    # Per-network
    for net, cfg in (quotas.get("networks") or {}).items():
        period = cfg.get("period", "daily")
        limit = cfg.get("limit")
        if not limit:
            continue
        s, e, _ = _period_bounds(period)
        if s is None:
            continue
        record(f"net:{net}", net, period, _usage_network(net, s, e), limit)

    # Prune stale state (older than 60 days)
    cutoff_date = (date.today() - timedelta(days=60)).isoformat()
    state = {k: v for k, v in state.items() if k.split(":", 1)[0] >= cutoff_date or k.startswith("W")}
    _save_state(state)

    return results


def any_exceeded():
    return any(r["exceeded"] for r in check_quotas())


if __name__ == "__main__":
    for r in check_quotas():
        print(r)
