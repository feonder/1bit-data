"""Export traffic data to CSV / JSON for any period."""
import csv
import json
import os
import subprocess
from datetime import datetime, date, timedelta

import data_tracker as dt


COLUMNS = ["timestamp", "datetime", "date", "app", "remote",
           "bytes_in", "bytes_out", "network"]


def _date_range(period):
    today = date.today()
    if period == "today":
        return today.isoformat(), today.isoformat()
    if period == "month":
        return today.replace(day=1).isoformat(), today.isoformat()
    if period == "year":
        return today.replace(month=1, day=1).isoformat(), today.isoformat()
    if period == "last30":
        return (today - timedelta(days=29)).isoformat(), today.isoformat()
    if period == "all":
        return "0000-00-00", "9999-99-99"
    raise ValueError(f"Unknown period: {period}")


def _fetch_rows(start, end):
    return dt._query(
        "SELECT timestamp, date, app, remote, bytes_in, bytes_out, network "
        "FROM traffic WHERE date BETWEEN ? AND ? ORDER BY timestamp",
        (start, end)
    )


def export(period, fmt):
    """Export traffic for period to Desktop. Returns path."""
    dt.init_db()
    start, end = _date_range(period)
    rows = _fetch_rows(start, end)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    period_label = period.replace("_", "-")
    fname = f"1bit_data_{period_label}_{ts}.{fmt}"
    path = os.path.expanduser(f"~/Desktop/{fname}")

    if fmt == "csv":
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            for r in rows:
                ts_unix, d, app, remote, b_in, b_out, network = r
                dt_iso = datetime.fromtimestamp(ts_unix).isoformat(timespec="seconds")
                w.writerow([ts_unix, dt_iso, d, app, remote, b_in, b_out, network])
    elif fmt == "json":
        records = []
        for r in rows:
            ts_unix, d, app, remote, b_in, b_out, network = r
            records.append({
                "timestamp": ts_unix,
                "datetime": datetime.fromtimestamp(ts_unix).isoformat(timespec="seconds"),
                "date": d,
                "app": app,
                "remote": remote,
                "bytes_in": b_in,
                "bytes_out": b_out,
                "network": network,
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "period": period,
                "start": start,
                "end": end,
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "row_count": len(records),
                "rows": records,
            }, f, indent=2, ensure_ascii=False)
    else:
        raise ValueError(f"Unknown format: {fmt}")

    subprocess.run(["open", "-R", path])
    return path, len(rows)


if __name__ == "__main__":
    import sys
    period = sys.argv[1] if len(sys.argv) > 1 else "today"
    fmt = sys.argv[2] if len(sys.argv) > 2 else "csv"
    p, n = export(period, fmt)
    print(f"Exported {n} rows -> {p}")
