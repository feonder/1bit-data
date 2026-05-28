#!/usr/bin/env python3
"""Menu bar app: live network speed, daily total, top apps, HTML reports, i18n."""
import rumps
import psutil
import json
import os
import sys
import subprocess
import threading
from datetime import date

import objc
from Foundation import NSObject
from AppKit import (
    NSEventMaskLeftMouseUp, NSEventMaskRightMouseUp,
    NSEventTypeRightMouseUp, NSMenu, NSApp as _NSApp,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_tracker
import data_report
import data_export
import quotas
import config_ui
import dashboard
import i18n
from i18n import t, LANG_NAMES

STATE_FILE = os.path.expanduser("~/.data_monitor_state.json")
SAMPLE_INTERVAL = 60   # seconds between nettop samples
ENRICH_INTERVAL = 300  # seconds between DNS/GeoIP enrichment passes
ACTIVE_THRESHOLD = 10_000  # bytes/sec to consider link "active"

SPARKLINE_CHARS = ("_", "⎽", "⎼", "─", "⎻", "⎺", "‾")  # 7 horizontal-line levels
SPARKLINE_WIDTH = 15


def sparkline(values, max_val=None):
    if not values:
        return ""
    mx = max_val if max_val is not None else max(values)
    n = len(SPARKLINE_CHARS) - 1
    if mx <= 0:
        return SPARKLINE_CHARS[0] * len(values)
    return "".join(
        SPARKLINE_CHARS[min(n, int(v / mx * n))] for v in values
    )


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def fmt_speed(bps):
    bits = bps * 8
    if bits < 1_000_000:
        return f"{bits/1_000:.0f} Kbps"
    return f"{bits/1_000_000:.1f} Mbps"


def fmt_bytes_short(n):
    if n < 1024:
        return f"{int(n)}B"
    n /= 1024
    if n < 1024:
        return f"{n:.0f}K" if n >= 100 else f"{n:.1f}K"
    n /= 1024
    if n < 1024:
        return f"{n:.0f}M" if n >= 100 else f"{n:.1f}M"
    n /= 1024
    return f"{n:.1f}G"


def fmt_speed_short(bps):
    bits = bps * 8
    if bits < 1_000:
        return f"{int(bits)}b"
    if bits < 1_000_000:
        return f"{int(bits/1_000)}K"
    if bits < 1_000_000_000:
        return f"{bits/1_000_000:.1f}M"
    return f"{bits/1_000_000_000:.1f}G"


def _noop(_):
    pass


class _StatusClickHandler(NSObject):
    """NSObject that handles status-bar button clicks: left → dashboard, right → menu."""

    def init(self):
        self = objc.super(_StatusClickHandler, self).init()
        if self is None:
            return None
        self._menu_ns = None
        return self

    @objc.python_method
    def setup(self, menu_ns):
        self._menu_ns = menu_ns

    def onClick_(self, sender):
        event = _NSApp.currentEvent()
        ev_type = event.type() if event else 0
        if ev_type == NSEventTypeRightMouseUp and self._menu_ns is not None:
            NSMenu.popUpContextMenu_withEvent_forView_(self._menu_ns, event, sender)
            return
        try:
            dashboard.open_dashboard()
        except Exception as e:
            print(f"open dashboard error: {e}", flush=True)


class DataMonitor(rumps.App):
    def __init__(self):
        super().__init__("…", quit_button=None)

        self.lang = i18n.get_lang()

        # Section headers — bright with bullet marker for hierarchy
        self.mi_h_speed = rumps.MenuItem("● LIVE SPEED", callback=_noop)
        self.mi_h_today = rumps.MenuItem("● TODAY", callback=_noop)
        self.mi_h_apps = rumps.MenuItem("● TOP APPS", callback=_noop)

        # Data rows (informational, bright)
        self.mi_speed_down = rumps.MenuItem("  ↓ --", callback=_noop)
        self.mi_speed_up = rumps.MenuItem("  ↑ --", callback=_noop)
        self.mi_today_down = rumps.MenuItem("  ↓ --", callback=_noop)
        self.mi_today_up = rumps.MenuItem("  ↑ --", callback=_noop)
        self.mi_today_total = rumps.MenuItem("  = --", callback=_noop)

        self.top_apps_items = [rumps.MenuItem(f"app{i}", callback=_noop) for i in range(5)]
        for mi in self.top_apps_items:
            mi.title = "  --"

        # REPORTS submenu
        self.mi_reports = rumps.MenuItem("Reports", callback=_noop)
        self.mi_rep_daily = rumps.MenuItem("Daily", callback=lambda _: data_report.open_report("daily"))
        self.mi_rep_monthly = rumps.MenuItem("Monthly", callback=lambda _: data_report.open_report("monthly"))
        self.mi_rep_yearly = rumps.MenuItem("Yearly", callback=lambda _: data_report.open_report("yearly"))
        self.mi_rep_last30 = rumps.MenuItem("Last 30", callback=lambda _: data_report.open_report("last30"))
        for child in (self.mi_rep_daily, self.mi_rep_monthly, self.mi_rep_yearly, self.mi_rep_last30):
            self.mi_reports.add(child)

        # EXPORT submenu (top-level, not buried in Settings)
        self.mi_export = rumps.MenuItem("Export", callback=_noop)
        self.mi_exp_today_csv = rumps.MenuItem("Today (CSV)", callback=self._make_export("today", "csv"))
        self.mi_exp_today_json = rumps.MenuItem("Today (JSON)", callback=self._make_export("today", "json"))
        self.mi_exp_month_csv = rumps.MenuItem("Month (CSV)", callback=self._make_export("month", "csv"))
        self.mi_exp_month_json = rumps.MenuItem("Month (JSON)", callback=self._make_export("month", "json"))
        self.mi_exp_year_csv = rumps.MenuItem("Year (CSV)", callback=self._make_export("year", "csv"))
        self.mi_exp_all_csv = rumps.MenuItem("All (CSV)", callback=self._make_export("all", "csv"))
        self.mi_exp_all_json = rumps.MenuItem("All (JSON)", callback=self._make_export("all", "json"))
        for child in (self.mi_exp_today_csv, self.mi_exp_today_json,
                      self.mi_exp_month_csv, self.mi_exp_month_json,
                      self.mi_exp_year_csv,
                      self.mi_exp_all_csv, self.mi_exp_all_json):
            self.mi_export.add(child)

        # SETTINGS submenu (language + admin only)
        self.mi_settings = rumps.MenuItem("Settings", callback=_noop)
        self.mi_language = rumps.MenuItem("Language", callback=_noop)
        self.lang_items = {}
        for code, name in LANG_NAMES.items():
            item = rumps.MenuItem(name, callback=self._make_lang_setter(code))
            if code == self.lang:
                item.state = True
            self.lang_items[code] = item
            self.mi_language.add(item)
        self.mi_edit_networks = rumps.MenuItem("Edit Networks", callback=self.edit_networks)
        self.mi_edit_quotas = rumps.MenuItem("Edit Quotas", callback=self.edit_quotas)
        self.mi_pause = rumps.MenuItem("Pause", callback=self.toggle_pause)
        self.mi_cleanup = rumps.MenuItem("Cleanup", callback=self.cleanup_db)
        self.mi_reset = rumps.MenuItem("Reset", callback=self.reset_today)
        self.mi_settings.add(self.mi_language)
        self.mi_settings.add(self.mi_edit_networks)
        self.mi_settings.add(self.mi_edit_quotas)
        self.mi_settings.add(self.mi_pause)
        self.mi_settings.add(self.mi_cleanup)
        self.mi_settings.add(self.mi_reset)

        self.mi_dashboard = rumps.MenuItem("Dashboard…", callback=self.open_dashboard)
        self.mi_quit = rumps.MenuItem("Quit", callback=rumps.quit_application)

        self.menu = [
            self.mi_dashboard,
            None,
            self.mi_h_speed,
            self.mi_speed_down,
            self.mi_speed_up,
            None,
            self.mi_h_today,
            self.mi_today_down,
            self.mi_today_up,
            self.mi_today_total,
            None,
            self.mi_h_apps,
            *self.top_apps_items,
            None,
            self.mi_reports,
            self.mi_export,
            self.mi_settings,
            None,
            self.mi_quit,
        ]

        self.quota_breached = False
        self.paused = bool(i18n.get_setting("tracking_paused", False))
        self._speed_history = []  # last N samples of (down+up) bytes/sec

        self.refresh_titles()

        io = psutil.net_io_counters()
        self.last_recv = io.bytes_recv
        self.last_sent = io.bytes_sent

        self.state = self._load_state()
        self._ensure_today()

        data_tracker.init_db()
        try:
            data_tracker._run_nettop()
            data_tracker._last_snapshot = {
                (app, pid, remote): (b_in, b_out)
                for app, pid, remote, b_in, b_out in data_tracker._run_nettop()
            }
        except Exception:
            pass

        self._refresh_pause_title()

        self.fast_timer = rumps.Timer(self.update_fast, 2)
        self.fast_timer.start()
        self.slow_timer = rumps.Timer(self.update_slow, SAMPLE_INTERVAL)
        self.slow_timer.start()
        self.enrich_timer = rumps.Timer(self.update_enrich, ENRICH_INTERVAL)
        self.enrich_timer.start()

        # Install custom click handler once status item is ready (after run() starts)
        self._click_handler = None
        self._install_click_timer = rumps.Timer(self._install_click_override, 0.8)
        self._install_click_timer.start()

    def _make_lang_setter(self, code):
        def cb(_):
            self.set_language(code)
        return cb

    def _make_export(self, period, fmt):
        def cb(_):
            threading.Thread(
                target=self._do_export, args=(period, fmt), daemon=True
            ).start()
        return cb

    def _do_export(self, period, fmt):
        try:
            path, n = data_export.export(period, fmt)
            rumps.notification(
                title="1 Bit Data",
                subtitle="",
                message=t("notify.export.done", n=n),
            )
        except Exception as e:
            print(f"export error: {e}", flush=True)

    def set_language(self, code):
        if not i18n.set_lang(code):
            return
        self.lang = code
        for c, item in self.lang_items.items():
            item.state = (c == code)
        self.refresh_titles()

    def refresh_titles(self):
        self.mi_h_speed.title = f"● {t('menu.live_speed')}"
        self._refresh_today_header()
        self.mi_h_apps.title = f"● {t('menu.top_apps')}"

        self.mi_reports.title = t("menu.reports")
        self.mi_rep_daily.title = t("menu.report.daily")
        self.mi_rep_monthly.title = t("menu.report.monthly")
        self.mi_rep_yearly.title = t("menu.report.yearly")
        self.mi_rep_last30.title = t("menu.report.last30")

        self.mi_settings.title = t("menu.settings")
        self.mi_language.title = t("menu.language")
        self.mi_reset.title = t("menu.reset_today")
        self.mi_edit_networks.title = t("menu.edit_networks")
        self.mi_edit_quotas.title = t("menu.edit_quotas")
        self.mi_dashboard.title = t("menu.dashboard")
        self.mi_cleanup.title = t("menu.cleanup")
        self.mi_pause.title = t("menu.resume") if self.paused else t("menu.pause")
        self.mi_quit.title = t("menu.quit")

        self.mi_export.title = t("menu.export")
        self.mi_exp_today_csv.title = f"{t('menu.export.today')} — CSV"
        self.mi_exp_today_json.title = f"{t('menu.export.today')} — JSON"
        self.mi_exp_month_csv.title = f"{t('menu.export.month')} — CSV"
        self.mi_exp_month_json.title = f"{t('menu.export.month')} — JSON"
        self.mi_exp_year_csv.title = f"{t('menu.export.year')} — CSV"
        self.mi_exp_all_csv.title = f"{t('menu.export.all')} — CSV"
        self.mi_exp_all_json.title = f"{t('menu.export.all')} — JSON"

    def _refresh_today_header(self):
        try:
            net = data_tracker.get_current_network()
        except Exception:
            net = ""
        if net and net != t("misc.unconnected"):
            self.mi_h_today.title = f"● {t('menu.today')}  ·  {net}"
        else:
            self.mi_h_today.title = f"● {t('menu.today')}"

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_state(self):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(self.state, f)
        except Exception:
            pass

    def _ensure_today(self):
        today = date.today().isoformat()
        if self.state.get("date") != today:
            self.state["date"] = today
            self.state["recv"] = 0
            self.state["sent"] = 0
            self._save_state()

    def edit_networks(self, _):
        config_ui.open_networks()

    def edit_quotas(self, _):
        config_ui.open_quotas()

    def open_dashboard(self, _):
        dashboard.open_dashboard()

    def _install_click_override(self, _):
        """Replace default status-item click (menu popup) with our handler."""
        try:
            si = self._nsapp.nsstatusitem
            btn = si.button()
            menu_ns = si.menu()
        except Exception as e:
            print(f"status item not ready: {e}", flush=True)
            return
        if btn is None:
            return
        self._install_click_timer.stop()
        self._click_handler = _StatusClickHandler.alloc().init()
        # Keep a reference to the NSMenu before we detach it
        self._click_handler.setup(menu_ns)
        # Detach menu from status item so left-click does NOT auto-popup;
        # we'll pop it up manually on right-click.
        si.setMenu_(None)
        btn.setTarget_(self._click_handler)
        btn.setAction_(b"onClick:")
        btn.sendActionOn_(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)

    def toggle_pause(self, _):
        self.paused = not self.paused
        i18n.set_setting("tracking_paused", self.paused)
        self.mi_pause.title = t("menu.resume") if self.paused else t("menu.pause")
        self._refresh_pause_title()

    def _refresh_pause_title(self):
        # Force title refresh on next tick
        pass

    def cleanup_db(self, _):
        alert = rumps.alert(
            title=t("cleanup.title"),
            message=t("cleanup.message"),
            ok="30 gün", cancel="İptal",
            other="90 gün",
        )
        # rumps.alert returns: 1=ok, 0=cancel, -1=other
        days_map = {1: 30, -1: 90}
        days = days_map.get(alert)
        if not days:
            return
        try:
            deleted = data_tracker.cleanup_old_data(days)
            rumps.notification(
                title="1 Bit Data",
                subtitle=t("cleanup.title"),
                message=t("cleanup.done", n=deleted),
            )
        except Exception as e:
            print(f"cleanup error: {e}", flush=True)

    def reset_today(self, _):
        self.state["recv"] = 0
        self.state["sent"] = 0
        self.state["date"] = date.today().isoformat()
        self._save_state()

    def update_fast(self, _):
        self._ensure_today()
        io = psutil.net_io_counters()

        d_recv = max(0, io.bytes_recv - self.last_recv)
        d_sent = max(0, io.bytes_sent - self.last_sent)
        self.last_recv = io.bytes_recv
        self.last_sent = io.bytes_sent

        self.state["recv"] += d_recv
        self.state["sent"] += d_sent
        self._save_state()

        down_speed = d_recv / 2
        up_speed = d_sent / 2

        # Track speed history for sparkline (combined throughput)
        self._speed_history.append(down_speed + up_speed)
        self._speed_history = self._speed_history[-SPARKLINE_WIDTH:]
        spark = sparkline(self._speed_history)

        today_total = self.state["recv"] + self.state["sent"]
        prefix = "⏸ " if self.paused else ("⚠︎ " if self.quota_breached else "")
        if down_speed > ACTIVE_THRESHOLD or up_speed > ACTIVE_THRESHOLD:
            self.title = (
                f"{prefix}{spark} ↓{fmt_speed_short(down_speed)} "
                f"↑{fmt_speed_short(up_speed)}  "
                f"▮ {fmt_bytes_short(today_total)}"
            )
        else:
            self.title = f"{prefix}{spark} ▮ {fmt_bytes_short(today_total)}"

        ld = t("menu.label.down")
        lu = t("menu.label.up")
        lrx = t("menu.label.rx")
        ltx = t("menu.label.tx")
        ltot = t("menu.label.total")

        self.mi_speed_down.title = f"   ↓  {ld} — {fmt_speed(down_speed)}"
        self.mi_speed_up.title = f"   ↑  {lu} — {fmt_speed(up_speed)}"

        self.mi_today_down.title = f"   ↓  {lrx} — {fmt_bytes(self.state['recv'])}"
        self.mi_today_up.title = f"   ↑  {ltx} — {fmt_bytes(self.state['sent'])}"
        self.mi_today_total.title = (
            f"   =  {ltot} — {fmt_bytes(self.state['recv'] + self.state['sent'])}"
        )

    def update_slow(self, _):
        threading.Thread(target=self._sample_and_refresh, daemon=True).start()

    def _make_app_opener(self, app_name):
        def cb(_):
            data_report.open_app_report(app_name)
        return cb

    def _sample_and_refresh(self):
        if self.paused:
            return
        try:
            data_tracker.sample_and_store()
            top = data_tracker.top_apps_today(limit=5)
            for i, mi in enumerate(self.top_apps_items):
                if i < len(top):
                    app, total, b_in, b_out = top[i]
                    mi.title = f"   {app[:30]}  —  {fmt_bytes_short(total)}"
                    mi.set_callback(self._make_app_opener(app))
                else:
                    mi.title = "   —"
                    mi.set_callback(_noop)
            self._refresh_today_header()
            self._check_quotas()
        except Exception as e:
            print(f"sample error: {e}", flush=True)

    def _check_quotas(self):
        try:
            results = quotas.check_quotas()
        except Exception as e:
            print(f"quota check error: {e}", flush=True)
            return
        self.quota_breached = any(r["exceeded"] for r in results)
        for r in results:
            if r["new_breach"]:
                msg = t(
                    "notify.quota.message",
                    label=r["label"],
                    used=fmt_bytes(r["used"]),
                    limit=fmt_bytes(r["limit"]),
                    pct=r["pct"],
                )
                try:
                    rumps.notification(
                        title=t("notify.quota.title"),
                        subtitle=r["label"],
                        message=msg,
                    )
                except Exception as e:
                    print(f"notify error: {e}", flush=True)

    def update_enrich(self, _):
        threading.Thread(target=self._enrich, daemon=True).start()

    def _enrich(self):
        try:
            n_dns = data_tracker.resolve_dns_batch(50)
            n_geo = data_tracker.resolve_geo_batch(100)
            if n_dns or n_geo:
                print(f"enrich: dns={n_dns} geo={n_geo}", flush=True)
        except Exception as e:
            print(f"enrich error: {e}", flush=True)


if __name__ == "__main__":
    DataMonitor().run()
