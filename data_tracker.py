"""Network usage tracker: nettop sampling + DNS/GeoIP enrichment + queries."""
import sqlite3
import subprocess
import os
import re
import time
import socket
import json
import urllib.request
from datetime import datetime, date, timedelta

DB_PATH = os.path.expanduser("~/.data_monitor.db")
NETWORK_NAMES_FILE = os.path.expanduser("~/.data_monitor_networks.json")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
VERSION_RE = re.compile(r"^\d+(?:\.\d+){1,3}$")

# In-memory previous snapshot: {(app, pid, remote): (bytes_in, bytes_out)}
_last_snapshot = {}

# Cache for prettified process names: (raw_name, pid) -> resolved
_name_cache = {}

# Cache for current network (avoid repeated subprocess calls)
_network_cache = {"ts": 0, "value": ""}


def _prettify_from_path(raw_name, path):
    """Map a versioned-name + binary path to a friendly label."""
    low = path.lower()
    if "claude/versions" in low or ".local/share/claude" in low:
        return f"Claude Code ({raw_name})"
    m = re.search(r"/Applications/([^/]+)\.app/", path)
    if m:
        return f"{m.group(1)} ({raw_name})"
    base = path.rsplit("/", 1)[-1]
    if base and base != raw_name and not VERSION_RE.fullmatch(base):
        return f"{base} ({raw_name})"
    return f"Versiyon {raw_name}"


def _get_binary_path(pid):
    """Return absolute binary path for a PID via psutil (proc_pidpath)."""
    try:
        import psutil
        return psutil.Process(int(pid)).exe()
    except Exception:
        return None


def _load_network_aliases():
    """Load user-defined network aliases from ~/.data_monitor_networks.json."""
    if os.path.exists(NETWORK_NAMES_FILE):
        try:
            with open(NETWORK_NAMES_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_current_network():
    """Return network identifier (sname + gateway, or 'Bağlı Değil')."""
    now = time.time()
    if now - _network_cache["ts"] < 30 and _network_cache["value"]:
        return _network_cache["value"]

    gateway = ""
    interface = ""
    try:
        r = subprocess.run(["route", "-n", "get", "default"],
                           capture_output=True, text=True, timeout=2)
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("gateway:"):
                gateway = line.split(":", 1)[1].strip()
            elif line.startswith("interface:"):
                interface = line.split(":", 1)[1].strip()
    except Exception:
        pass

    if not gateway:
        result = "Bağlı Değil"
    else:
        sname = ""
        if interface:
            try:
                r = subprocess.run(["ipconfig", "getsummary", interface],
                                   capture_output=True, text=True, timeout=2)
                for line in r.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("sname ="):
                        sname = line.split("=", 1)[1].strip()
                        break
            except Exception:
                pass

        key = gateway
        aliases = _load_network_aliases()
        if key in aliases:
            result = aliases[key]
        elif sname:
            result = f"{sname} ({gateway})"
        else:
            result = gateway

    _network_cache["ts"] = now
    _network_cache["value"] = result
    return result


def _resolve_app_name(raw_name, pid):
    """If raw_name looks cryptic (e.g. version number), resolve via lsof + ps."""
    if not raw_name:
        return raw_name
    key = (raw_name, pid)
    if key in _name_cache:
        return _name_cache[key]

    resolved = raw_name
    if VERSION_RE.fullmatch(raw_name) and pid and pid.isdigit():
        path = _get_binary_path(pid)
        if path:
            resolved = _prettify_from_path(raw_name, path)
        else:
            resolved = f"Versiyon {raw_name}"

    _name_cache[key] = resolved
    return resolved


def migrate_versioned_names():
    """Rename historical rows that have cryptic versioned app names."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT DISTINCT app FROM traffic")
    distinct = [r[0] for r in cur.fetchall()]
    rename_map = {}

    claude_dir = os.path.expanduser("~/.local/share/claude/versions")
    claude_versions = set()
    if os.path.isdir(claude_dir):
        claude_versions = set(os.listdir(claude_dir))

    for name in distinct:
        if not VERSION_RE.fullmatch(name):
            continue
        if name in claude_versions:
            rename_map[name] = f"Claude Code ({name})"
        else:
            rename_map[name] = f"Versiyon {name}"

    for old, new in rename_map.items():
        conn.execute("UPDATE traffic SET app = ? WHERE app = ?", (new, old))
    conn.commit()
    conn.close()
    return rename_map


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traffic (
            timestamp INTEGER NOT NULL,
            date TEXT NOT NULL,
            app TEXT NOT NULL,
            remote TEXT NOT NULL,
            bytes_in INTEGER NOT NULL,
            bytes_out INTEGER NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON traffic(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_app ON traffic(app)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_remote ON traffic(remote)")
    # Add network column if missing (older DBs)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(traffic)").fetchall()]
    if "network" not in cols:
        conn.execute("ALTER TABLE traffic ADD COLUMN network TEXT NOT NULL DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_network ON traffic(network)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dns_cache (
            ip TEXT PRIMARY KEY,
            hostname TEXT,
            resolved_at INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS geo_cache (
            ip TEXT PRIMARY KEY,
            country TEXT,
            country_code TEXT,
            city TEXT,
            isp TEXT,
            resolved_at INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS speed_tests (
            timestamp INTEGER PRIMARY KEY,
            dl_bps REAL,
            ul_bps REAL,
            base_rtt_ms REAL,
            responsiveness_rpm REAL,
            network TEXT
        )
    """)
    conn.commit()
    conn.close()


def _classify_remote(remote_raw):
    if not remote_raw or "*" in remote_raw:
        return "unknown"
    m = IPV4_RE.search(remote_raw)
    if not m:
        return "ipv6_or_other"
    ip = m.group(0)
    parts = ip.split(".")
    try:
        a, b = int(parts[0]), int(parts[1])
        if a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168) or a == 127:
            return f"local ({ip})"
    except (ValueError, IndexError):
        pass
    return ip


def _is_public_ip(ip):
    if not ip or "." not in ip:
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    if a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168):
        return False
    if a == 127 or a == 0 or a >= 224:
        return False
    return True


def _run_nettop():
    try:
        result = subprocess.run(
            ["nettop", "-L", "1", "-x", "-J", "bytes_in,bytes_out", "-n",
             "-t", "wifi", "-t", "wired"],
            capture_output=True, text=True, timeout=15
        )
    except Exception:
        return []

    rows = []
    current_app = None
    current_pid = None
    for line in result.stdout.splitlines():
        parts = line.split(",")
        if len(parts) < 3:
            continue
        first = parts[0].strip()
        if not first or first == "bytes_in":
            continue
        try:
            b_in = int(parts[1])
            b_out = int(parts[2])
        except ValueError:
            continue

        if first.startswith(("tcp", "udp", "quic")):
            if current_app is None:
                continue
            try:
                conn_str = first.split(" ", 1)[1]
                remote_raw = conn_str.split("<->")[1]
            except (IndexError, ValueError):
                remote_raw = ""
            remote = _classify_remote(remote_raw)
            rows.append((current_app, current_pid, remote, b_in, b_out))
        else:
            if "." in first:
                name, _, pid = first.rpartition(".")
                if pid.isdigit():
                    current_app = _resolve_app_name(name, pid)
                    current_pid = pid
                    continue
            current_app = first
            current_pid = ""
    return rows


def sample_and_store():
    global _last_snapshot
    rows = _run_nettop()
    if not rows:
        return 0

    now = int(time.time())
    today = date.today().isoformat()

    snapshot = {}
    for app, pid, remote, b_in, b_out in rows:
        key = (app, pid, remote)
        prev_in, prev_out = snapshot.get(key, (0, 0))
        snapshot[key] = (prev_in + b_in, prev_out + b_out)

    deltas = {}
    for key, (cur_in, cur_out) in snapshot.items():
        prev = _last_snapshot.get(key)
        if prev is None:
            d_in, d_out = cur_in, cur_out
        else:
            d_in = max(0, cur_in - prev[0])
            d_out = max(0, cur_out - prev[1])
        if d_in == 0 and d_out == 0:
            continue
        app, _, remote = key
        agg_key = (app, remote)
        cur = deltas.get(agg_key, [0, 0])
        cur[0] += d_in
        cur[1] += d_out
        deltas[agg_key] = cur

    _last_snapshot = snapshot

    if not deltas:
        return 0

    network = get_current_network()
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        "INSERT INTO traffic (timestamp, date, app, remote, bytes_in, bytes_out, network) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(now, today, app, remote, d[0], d[1], network) for (app, remote), d in deltas.items()]
    )
    conn.commit()
    conn.close()
    return len(deltas)


# ---------- DNS / GeoIP enrichment ----------

def _get_unresolved_dns_ips(limit=50):
    return _query("""
        SELECT DISTINCT t.remote FROM traffic t
        LEFT JOIN dns_cache d ON d.ip = t.remote
        WHERE d.ip IS NULL
          AND t.remote NOT IN ('unknown', 'ipv6_or_other')
          AND t.remote NOT LIKE 'local%'
        LIMIT ?
    """, (limit,))


def resolve_dns_batch(limit=50):
    ips = [r[0] for r in _get_unresolved_dns_ips(limit)]
    if not ips:
        return 0
    socket.setdefaulttimeout(2)
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    resolved = 0
    for ip in ips:
        hostname = None
        if _is_public_ip(ip):
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except (socket.herror, socket.gaierror, OSError):
                hostname = None
        conn.execute(
            "INSERT OR REPLACE INTO dns_cache (ip, hostname, resolved_at) VALUES (?, ?, ?)",
            (ip, hostname, now)
        )
        if hostname:
            resolved += 1
    conn.commit()
    conn.close()
    return resolved


def _get_ungeolocated_ips(limit=100):
    return _query("""
        SELECT DISTINCT t.remote FROM traffic t
        LEFT JOIN geo_cache g ON g.ip = t.remote
        WHERE g.ip IS NULL
          AND t.remote NOT IN ('unknown', 'ipv6_or_other')
          AND t.remote NOT LIKE 'local%'
        LIMIT ?
    """, (limit,))


def resolve_geo_batch(limit=100):
    ips = [r[0] for r in _get_ungeolocated_ips(limit)]
    public_ips = [ip for ip in ips if _is_public_ip(ip)]
    now = int(time.time())

    if not public_ips:
        return 0

    try:
        req = urllib.request.Request(
            "http://ip-api.com/batch?fields=country,countryCode,city,isp,query,status",
            data=json.dumps([{"query": ip} for ip in public_ips]).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            results = json.load(r)
    except Exception:
        return 0

    conn = sqlite3.connect(DB_PATH)
    n = 0
    for item in results:
        ip = item.get("query", "")
        if not ip:
            continue
        if item.get("status") == "success":
            conn.execute(
                "INSERT OR REPLACE INTO geo_cache "
                "(ip, country, country_code, city, isp, resolved_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ip, item.get("country", ""), item.get("countryCode", ""),
                 item.get("city", ""), item.get("isp", ""), now)
            )
            n += 1
        else:
            conn.execute(
                "INSERT OR REPLACE INTO geo_cache VALUES (?, ?, ?, ?, ?, ?)",
                (ip, "Unknown", "", "", "", now)
            )
    conn.commit()
    conn.close()
    return n


def get_remote_meta(ips):
    """Return dict: ip -> {hostname, country, country_code, city, isp}."""
    if not ips:
        return {}
    placeholders = ",".join("?" * len(ips))
    dns_rows = _query(
        f"SELECT ip, hostname FROM dns_cache WHERE ip IN ({placeholders})",
        list(ips),
    )
    dns_map = {ip: hostname for ip, hostname in dns_rows}
    geo_rows = _query(
        f"SELECT ip, country, country_code, city, isp FROM geo_cache WHERE ip IN ({placeholders})",
        list(ips),
    )
    geo_map = {r[0]: {"country": r[1], "country_code": r[2], "city": r[3], "isp": r[4]} for r in geo_rows}
    out = {}
    for ip in ips:
        meta = {"hostname": dns_map.get(ip), "country": "", "country_code": "", "city": "", "isp": ""}
        meta.update(geo_map.get(ip, {}))
        out[ip] = meta
    return out


# ---------- Queries ----------

def _query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def top_apps_today(limit=10):
    today = date.today().isoformat()
    return _query(
        "SELECT app, SUM(bytes_in)+SUM(bytes_out) AS total, "
        "SUM(bytes_in), SUM(bytes_out) "
        "FROM traffic WHERE date=? GROUP BY app "
        "ORDER BY total DESC LIMIT ?",
        (today, limit)
    )


def top_apps_range(start_date, end_date, limit=20):
    return _query(
        "SELECT app, SUM(bytes_in)+SUM(bytes_out) AS total, "
        "SUM(bytes_in), SUM(bytes_out) "
        "FROM traffic WHERE date BETWEEN ? AND ? GROUP BY app "
        "ORDER BY total DESC LIMIT ?",
        (start_date, end_date, limit)
    )


def top_remotes_range(start_date, end_date, limit=30):
    return _query(
        "SELECT remote, SUM(bytes_in)+SUM(bytes_out) AS total, "
        "SUM(bytes_in), SUM(bytes_out) "
        "FROM traffic WHERE date BETWEEN ? AND ? GROUP BY remote "
        "ORDER BY total DESC LIMIT ?",
        (start_date, end_date, limit)
    )


def daily_totals_range(start_date, end_date):
    return _query(
        "SELECT date, SUM(bytes_in), SUM(bytes_out) "
        "FROM traffic WHERE date BETWEEN ? AND ? "
        "GROUP BY date ORDER BY date",
        (start_date, end_date)
    )


def total_range(start_date, end_date):
    rows = _query(
        "SELECT SUM(bytes_in), SUM(bytes_out) "
        "FROM traffic WHERE date BETWEEN ? AND ?",
        (start_date, end_date)
    )
    if not rows or rows[0][0] is None:
        return 0, 0
    return rows[0][0], rows[0][1]


def top_networks_range(start_date, end_date, limit=20):
    return _query(
        "SELECT network, SUM(bytes_in)+SUM(bytes_out) AS total, "
        "SUM(bytes_in), SUM(bytes_out) "
        "FROM traffic WHERE date BETWEEN ? AND ? GROUP BY network "
        "ORDER BY total DESC LIMIT ?",
        (start_date, end_date, limit)
    )


def hourly_buckets_range(start_date, end_date):
    """(date, hour, bytes_in, bytes_out) in local time."""
    return _query("""
        SELECT
            strftime('%Y-%m-%d', timestamp, 'unixepoch', 'localtime') AS d,
            CAST(strftime('%H', timestamp, 'unixepoch', 'localtime') AS INTEGER) AS h,
            SUM(bytes_in), SUM(bytes_out)
        FROM traffic
        WHERE date BETWEEN ? AND ?
        GROUP BY d, h
        ORDER BY d, h
    """, (start_date, end_date))


def hour_of_day_totals(start_date, end_date):
    """Aggregate totals by hour-of-day (0-23) across the range."""
    return _query("""
        SELECT
            CAST(strftime('%H', timestamp, 'unixepoch', 'localtime') AS INTEGER) AS h,
            SUM(bytes_in), SUM(bytes_out)
        FROM traffic
        WHERE date BETWEEN ? AND ?
        GROUP BY h ORDER BY h
    """, (start_date, end_date))


# ---------- Per-app queries ----------

def app_daily_trend(app, start_date, end_date):
    return _query(
        "SELECT date, SUM(bytes_in), SUM(bytes_out) FROM traffic "
        "WHERE app = ? AND date BETWEEN ? AND ? "
        "GROUP BY date ORDER BY date",
        (app, start_date, end_date)
    )


def app_top_remotes(app, start_date, end_date, limit=50):
    return _query(
        "SELECT remote, SUM(bytes_in)+SUM(bytes_out) AS total, "
        "SUM(bytes_in), SUM(bytes_out) "
        "FROM traffic WHERE app = ? AND date BETWEEN ? AND ? "
        "GROUP BY remote ORDER BY total DESC LIMIT ?",
        (app, start_date, end_date, limit)
    )


def app_hourly_buckets(app, start_date, end_date):
    return _query("""
        SELECT
            strftime('%Y-%m-%d', timestamp, 'unixepoch', 'localtime') AS d,
            CAST(strftime('%H', timestamp, 'unixepoch', 'localtime') AS INTEGER) AS h,
            SUM(bytes_in), SUM(bytes_out)
        FROM traffic
        WHERE app = ? AND date BETWEEN ? AND ?
        GROUP BY d, h
        ORDER BY d, h
    """, (app, start_date, end_date))


def app_total(app, start_date, end_date):
    rows = _query(
        "SELECT SUM(bytes_in), SUM(bytes_out) FROM traffic "
        "WHERE app = ? AND date BETWEEN ? AND ?",
        (app, start_date, end_date)
    )
    if not rows or rows[0][0] is None:
        return 0, 0
    return rows[0][0], rows[0][1]


def top_apps_for_remote(remote, start_date, end_date, limit=30):
    return _query(
        "SELECT app, SUM(bytes_in)+SUM(bytes_out) AS total, "
        "SUM(bytes_in), SUM(bytes_out) "
        "FROM traffic WHERE remote = ? AND date BETWEEN ? AND ? "
        "GROUP BY app ORDER BY total DESC LIMIT ?",
        (remote, start_date, end_date, limit)
    )


def record_speedtest(dl_bps, ul_bps, base_rtt_ms, responsiveness_rpm, network):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO speed_tests "
        "(timestamp, dl_bps, ul_bps, base_rtt_ms, responsiveness_rpm, network) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (int(time.time()), dl_bps, ul_bps, base_rtt_ms, responsiveness_rpm, network)
    )
    conn.commit()
    conn.close()


def get_speedtests(limit=20):
    return _query(
        "SELECT timestamp, dl_bps, ul_bps, base_rtt_ms, responsiveness_rpm, network "
        "FROM speed_tests ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )


def cleanup_old_data(days_to_keep):
    """Delete traffic rows older than N days. VACUUM after. Returns deleted count."""
    cutoff = (date.today() - timedelta(days=days_to_keep)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("DELETE FROM traffic WHERE date < ?", (cutoff,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    # VACUUM must run on a separate connection without an open transaction
    conn = sqlite3.connect(DB_PATH)
    conn.isolation_level = None
    conn.execute("VACUUM")
    conn.close()
    return deleted


def db_stats():
    """Return dict with row_count, oldest, newest, size_bytes."""
    rows = _query("SELECT COUNT(*), MIN(date), MAX(date) FROM traffic")
    if not rows:
        return {"row_count": 0, "oldest": None, "newest": None, "size_bytes": 0}
    count, oldest, newest = rows[0]
    try:
        size = os.path.getsize(DB_PATH)
    except OSError:
        size = 0
    return {"row_count": count or 0, "oldest": oldest, "newest": newest, "size_bytes": size}


def remote_total(remote, start_date, end_date):
    rows = _query(
        "SELECT SUM(bytes_in), SUM(bytes_out) FROM traffic "
        "WHERE remote = ? AND date BETWEEN ? AND ?",
        (remote, start_date, end_date)
    )
    if not rows or rows[0][0] is None:
        return 0, 0
    return rows[0][0], rows[0][1]


if __name__ == "__main__":
    import sys
    init_db()
    if len(sys.argv) > 1 and sys.argv[1] == "enrich":
        n_dns = resolve_dns_batch(50)
        n_geo = resolve_geo_batch(100)
        print(f"DNS resolved: {n_dns}, Geo resolved: {n_geo}")
    else:
        n = sample_and_store()
        print(f"Sampled, wrote {n} delta rows")
        print("Top apps today:")
        for row in top_apps_today(5):
            print(f"  {row[0]}: {row[1]/1024/1024:.2f} MB")
