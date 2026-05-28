"""Full dashboard window with tabs:
  Özet · Uygulamalar · Hedefler · Kotalar · Ağlar · Raporlar · Dışa Aktar · Ayarlar
"""
import os
import sys
import json
from datetime import date, timedelta

import objc
from Foundation import NSObject, NSMakeRect, NSMakeSize, NSMakePoint, NSTimer
from AppKit import (
    NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSWindowStyleMaskFullSizeContentView,
    NSWindowTitleHidden,
    NSBackingStoreBuffered, NSTextField, NSButton, NSPopUpButton,
    NSView, NSScrollView, NSColor, NSFont, NSApp,
    NSBezelStyleRegularSquare, NSBezelStyleTexturedRounded, NSBox,
    NSLevelIndicator, NSLevelIndicatorStyleContinuousCapacity,
    NSSearchField,
    NSAttributedString,
    NSForegroundColorAttributeName, NSFontAttributeName,
    NSAppearance, NSAppearanceNameVibrantDark,
    NSMenu, NSMenuItem,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_tracker
import data_report
import data_export
import quotas as quotas_mod
import config_ui
import speedtest
import i18n
from i18n import t, LANG_NAMES
import threading
from datetime import datetime

import psutil


WINDOW_W = 980
WINDOW_H = 680


# ============================================================
# 1 Bit theme palette
# ============================================================

def _rgba(r, g, b, a=1.0):
    return NSColor.colorWithRed_green_blue_alpha_(r, g, b, a)

BG = lambda: _rgba(0.04, 0.055, 0.04)            # #0a0e0a
BG_PANEL = lambda: _rgba(0.06, 0.085, 0.06)      # slightly lighter panel
FG_GREEN = lambda: _rgba(0.0, 1.0, 0.4)          # primary bright
FG_TEXT = lambda: _rgba(0.0, 0.8, 0.33)          # body text
FG_DIM = lambda: _rgba(0.35, 0.55, 0.35)         # secondary text / hints
FG_DIMMER = lambda: _rgba(0.25, 0.4, 0.25)       # tertiary
FG_AMBER = lambda: _rgba(1.0, 0.667, 0.0)        # numeric highlights
FG_TEAL = lambda: _rgba(0.22, 0.82, 0.85)        # download
FG_PINK = lambda: _rgba(1.0, 0.475, 0.776)       # upload
FG_RED = lambda: _rgba(1.0, 0.3, 0.3)            # warnings
BORDER = lambda: _rgba(0.1, 0.35, 0.1)           # 1px green frames
BORDER_DIM = lambda: _rgba(0.06, 0.15, 0.06)     # subtle dividers


def _mono_font(size=12, bold=False):
    name = "JetBrainsMono-Bold" if bold else "JetBrainsMono-Regular"
    f = NSFont.fontWithName_size_(name, size)
    if f is None:
        name = "Menlo-Bold" if bold else "Menlo"
        f = NSFont.fontWithName_size_(name, size)
    if f is None:
        f = NSFont.userFixedPitchFontOfSize_(size)
    return f


def _set_bg(view, color):
    view.setWantsLayer_(True)
    view.layer().setBackgroundColor_(color.CGColor())


PERIOD_CODES = ["today", "month", "year", "last30", "all"]
PERIOD_KEY_MAP = {
    "today": "period.today",
    "month": "period.month",
    "year": "period.year",
    "last30": "period.last30",
    "all": "period.all",
}


def _period_labels():
    return [t(PERIOD_KEY_MAP[c]) for c in PERIOD_CODES]


def _period_range(period):
    today = date.today()
    if period == "today":
        return today.isoformat(), today.isoformat()
    if period == "month":
        return today.replace(day=1).isoformat(), today.isoformat()
    if period == "year":
        return today.replace(month=1, day=1).isoformat(), today.isoformat()
    if period == "last30":
        return (today - timedelta(days=29)).isoformat(), today.isoformat()
    return "0000-00-00", "9999-99-99"


def _period_from_label(label):
    for code in PERIOD_CODES:
        if t(PERIOD_KEY_MAP[code]) == label:
            return code
    return "today"


def fmt_bytes(n):
    if n is None or n == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"


def fmt_speed(bps):
    bits = bps * 8
    if bits < 1_000:
        return f"{int(bits)} bps"
    if bits < 1_000_000:
        return f"{int(bits/1_000)} Kbps"
    return f"{bits/1_000_000:.1f} Mbps"


def _fmt_bps(bps):
    """Format bytes/sec from speed test results — bits/sec output (Mbps/Gbps)."""
    if not bps:
        return "—"
    bits = bps * 8
    if bits < 1_000_000:
        return f"{bits/1_000:.0f} Kbps"
    if bits < 1_000_000_000:
        return f"{bits/1_000_000:.1f} Mbps"
    return f"{bits/1_000_000_000:.2f} Gbps"


# ============================================================
# UI helpers
# ============================================================

def _label(text, bold=False, color=None, size=12, width=None, align="left"):
    f = NSTextField.alloc().init()
    f.setStringValue_(text)
    f.setBezeled_(False)
    f.setDrawsBackground_(False)
    f.setEditable_(False)
    f.setSelectable_(False)
    f.setFont_(_mono_font(size, bold=bold))
    f.setTextColor_(color if color is not None else FG_TEXT())
    if align == "right":
        f.setAlignment_(2)
    elif align == "center":
        f.setAlignment_(1)
    f.sizeToFit()
    if width is not None:
        sz = f.frame().size
        f.setFrameSize_(NSMakeSize(width, sz.height))
    return f


def _mono_label(text, size=12, color=None, width=None):
    f = NSTextField.alloc().init()
    f.setStringValue_(text)
    f.setBezeled_(False)
    f.setDrawsBackground_(False)
    f.setEditable_(False)
    f.setSelectable_(True)
    f.setFont_(_mono_font(size))
    f.setTextColor_(color if color is not None else FG_TEXT())
    f.sizeToFit()
    if width is not None:
        sz = f.frame().size
        f.setFrameSize_(NSMakeSize(width, sz.height))
    return f


def _term_tab_button(label, target, action, active=False, width=130):
    """Tab bar button styled as [ LABEL ] when active, dim when inactive."""
    b = NSButton.alloc().init()
    b.setBordered_(False)
    b.setBezelStyle_(NSBezelStyleRegularSquare)
    b.setTarget_(target)
    b.setAction_(action)
    b.setFrame_(NSMakeRect(0, 0, width, 30))
    _term_tab_button_update(b, label, active)
    return b


def _term_tab_button_update(btn, label, active=False):
    text = f"[ {label} ]" if active else f"  {label}  "
    color = FG_GREEN() if active else FG_DIMMER()
    font = _mono_font(12, bold=active)
    attrs = {NSForegroundColorAttributeName: color, NSFontAttributeName: font}
    astr = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
    btn.setAttributedTitle_(astr)


def _term_button(title, target, action, width=None):
    """Bordered terminal-style button: amber text, dashed-feel border."""
    b = NSButton.alloc().init()
    b.setBordered_(False)
    b.setBezelStyle_(NSBezelStyleRegularSquare)
    b.setTarget_(target)
    b.setAction_(action)
    attrs = {NSForegroundColorAttributeName: FG_AMBER(),
             NSFontAttributeName: _mono_font(12, bold=True)}
    astr = NSAttributedString.alloc().initWithString_attributes_(
        f"[ {title} ]", attrs)
    b.setAttributedTitle_(astr)
    b.sizeToFit()
    if width:
        sz = b.frame().size
        b.setFrameSize_(NSMakeSize(width, max(sz.height, 28)))
    return b


class _TermPopup(NSView):
    """Terminal-styled dropdown: looks like [ Today ▾ ], opens themed menu on click."""

    def initWithFrame_(self, frame):
        self = objc.super(_TermPopup, self).initWithFrame_(frame)
        if self is None:
            return None
        self._items = []
        self._selected = ""
        self._target = None
        self._action_sel = None
        self._button = NSButton.alloc().initWithFrame_(
            NSMakeRect(0, 0, frame.size.width, frame.size.height))
        self._button.setBordered_(False)
        self._button.setBezelStyle_(NSBezelStyleRegularSquare)
        self._button.setAutoresizingMask_(2 | 16)
        self._button.setTarget_(self)
        self._button.setAction_(b"showMenu:")
        self.addSubview_(self._button)
        return self

    @objc.python_method
    def configure(self, items, selected, target, action):
        self._items = list(items)
        if selected and selected in self._items:
            self._selected = selected
        elif self._items:
            self._selected = self._items[0]
        self._target = target
        self._action_sel = action
        self._render_title()

    @objc.python_method
    def _render_title(self):
        attrs = {NSForegroundColorAttributeName: FG_AMBER(),
                 NSFontAttributeName: _mono_font(12, bold=True)}
        astr = NSAttributedString.alloc().initWithString_attributes_(
            f"[ {self._selected}  ▾ ]", attrs)
        self._button.setAttributedTitle_(astr)

    def showMenu_(self, _sender):
        menu = NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)
        for item in self._items:
            mi = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                item, b"itemSelected:", "")
            is_active = (item == self._selected)
            color = FG_GREEN() if is_active else FG_TEXT()
            marker = "✓ " if is_active else "   "
            attrs = {NSForegroundColorAttributeName: color,
                     NSFontAttributeName: _mono_font(12, bold=is_active)}
            astr = NSAttributedString.alloc().initWithString_attributes_(
                f"{marker}{item}", attrs)
            mi.setAttributedTitle_(astr)
            mi.setTarget_(self)
            mi.setRepresentedObject_(item)
            menu.addItem_(mi)
        location = NSMakePoint(0, self.frame().size.height)
        menu.popUpMenuPositioningItem_atLocation_inView_(None, location, self)

    def itemSelected_(self, sender):
        val = sender.representedObject()
        if val is None:
            return
        self._selected = str(val)
        self._render_title()
        if self._target is not None and self._action_sel is not None:
            try:
                self._target.performSelector_withObject_(self._action_sel, self)
            except Exception as e:
                print(f"term popup action error: {e}", flush=True)

    def titleOfSelectedItem(self):
        return self._selected

    def stringValue(self):
        return self._selected


def _popup(items, selected=None, width=130, target=None, action=None):
    p = _TermPopup.alloc().initWithFrame_(NSMakeRect(0, 0, width, 26))
    p.configure(items, selected, target, action)
    return p


class _TermSearch(NSView):
    """Terminal-styled text input: 1px green border, mono font, dim placeholder."""

    def initWithFrame_(self, frame):
        self = objc.super(_TermSearch, self).initWithFrame_(frame)
        if self is None:
            return None
        self._target = None
        self._action_sel = None
        # Layer for bg + border
        self.setWantsLayer_(True)
        self.layer().setBackgroundColor_(BG_PANEL().CGColor())
        self.layer().setBorderColor_(BORDER().CGColor())
        self.layer().setBorderWidth_(1.0)
        self.layer().setCornerRadius_(0)
        # Inner text field
        self._field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(10, 4, frame.size.width - 20, frame.size.height - 8))
        self._field.setBezeled_(False)
        self._field.setDrawsBackground_(False)
        self._field.setEditable_(True)
        self._field.setSelectable_(True)
        self._field.setFont_(_mono_font(12))
        self._field.setTextColor_(FG_TEXT())
        self._field.setFocusRingType_(1)  # NSFocusRingTypeNone
        self._field.cell().setUsesSingleLineMode_(True)
        self._field.cell().setScrollable_(True)
        self._field.setAutoresizingMask_(2 | 16)
        self._field.setDelegate_(self)
        self.addSubview_(self._field)
        return self

    @objc.python_method
    def configure(self, placeholder, target, action):
        ph_attrs = {NSForegroundColorAttributeName: FG_DIMMER(),
                    NSFontAttributeName: _mono_font(12)}
        ph_astr = NSAttributedString.alloc().initWithString_attributes_(
            placeholder, ph_attrs)
        self._field.cell().setPlaceholderAttributedString_(ph_astr)
        self._target = target
        self._action_sel = action

    def controlTextDidChange_(self, notification):
        if self._target is not None and self._action_sel is not None:
            try:
                self._target.performSelector_withObject_(self._action_sel, self)
            except Exception as e:
                print(f"term search action error: {e}", flush=True)

    def stringValue(self):
        return self._field.stringValue() if self._field else ""

    def setStringValue_(self, s):
        if self._field is not None:
            self._field.setStringValue_(s)


def _button(title, target, action, width=None):
    return _term_button(title, target, action, width=width)


def _position(view, x, y, w, h):
    view.setFrame_(NSMakeRect(x, y, w, h))
    return view


def _sort_header(label, target, action, width=120):
    """Clickable header button styled as a small label (for sortable columns)."""
    b = NSButton.alloc().init()
    b.setBordered_(False)
    b.setBezelStyle_(NSBezelStyleRegularSquare)
    b.setAlignment_(0)  # left
    b.setTarget_(target)
    b.setAction_(action)
    attrs = {NSForegroundColorAttributeName: FG_DIM(),
             NSFontAttributeName: _mono_font(10, bold=True)}
    astr = NSAttributedString.alloc().initWithString_attributes_(label, attrs)
    b.setAttributedTitle_(astr)
    b.sizeToFit()
    sz = b.frame().size
    b.setFrameSize_(NSMakeSize(width, max(sz.height, 18)))
    return b


def _read_state():
    try:
        with open(os.path.expanduser("~/.data_monitor_state.json")) as f:
            s = json.load(f)
        return s.get("recv", 0), s.get("sent", 0)
    except Exception:
        return 0, 0


# ============================================================
# Dashboard window
# ============================================================

class DashboardWindow(NSObject):

    def init(self):
        self = objc.super(DashboardWindow, self).init()
        if self is None:
            return None
        self._psutil_last_recv = 0
        self._psutil_last_sent = 0
        self._app_period = "today"
        self._dest_period = "today"
        self._app_buttons = []
        self._dest_buttons = []
        self._report_periods = ["daily", "monthly", "yearly", "last30"]
        self._app_detail_current = None
        self._dest_detail_current = None
        self._app_filter = ""
        self._dest_filter = ""
        self._app_sort = ("total", "desc")   # (col, dir)
        self._dest_sort = ("total", "desc")
        self._speedtest_proc = None
        self._speedtest_cancelled = False
        self._st_live_timer = None
        self._st_last_recv = 0
        self._st_last_sent = 0
        self._st_last_ts = 0
        self.timer = None
        self.build()
        return self

    @objc.python_method
    def build(self):
        rect = NSMakeRect(120, 80, WINDOW_W, WINDOW_H)
        mask = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
                | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        self.window = (NSWindow.alloc()
                       .initWithContentRect_styleMask_backing_defer_(
                           rect, mask, NSBackingStoreBuffered, False))
        self.window.setTitle_("1 Bit Data")
        self.window.setReleasedWhenClosed_(False)
        self.window.setDelegate_(self)
        # Force vibrant dark appearance regardless of system theme
        try:
            appr = NSAppearance.appearanceNamed_(NSAppearanceNameVibrantDark)
            if appr is not None:
                self.window.setAppearance_(appr)
        except Exception:
            pass

        content = self.window.contentView()
        _set_bg(content, BG())

        # ----- Tab bar (top) -----
        tab_bar_h = 44
        self.tab_bar = NSView.alloc().initWithFrame_(
            NSMakeRect(0, WINDOW_H - tab_bar_h, WINDOW_W, tab_bar_h))
        self.tab_bar.setAutoresizingMask_(2 | 8)  # width + minY
        _set_bg(self.tab_bar, BG())
        content.addSubview_(self.tab_bar)

        # Divider below tab bar
        div = NSView.alloc().initWithFrame_(
            NSMakeRect(0, WINDOW_H - tab_bar_h - 1, WINDOW_W, 1))
        div.setAutoresizingMask_(2 | 8)
        _set_bg(div, BORDER())
        content.addSubview_(div)

        tab_defs = [
            ("overview", t("dash.tab.overview"), self.tab_overview),
            ("apps", t("dash.tab.apps"), self.tab_apps),
            ("destinations", t("dash.tab.destinations"), self.tab_destinations),
            ("quotas", t("dash.tab.quotas"), self.tab_quotas),
            ("networks", t("dash.tab.networks"), self.tab_networks),
            ("reports", t("dash.tab.reports"), self.tab_reports),
            ("export", t("dash.tab.export"), self.tab_export),
            ("settings", t("dash.tab.settings"), self.tab_settings),
        ]
        self.tab_buttons = []
        self.tab_sections = []
        self.tab_labels = [d[1] for d in tab_defs]

        btn_w = 120
        x = 8
        y_btn = (tab_bar_h - 30) // 2
        for idx, (ident, label, _builder) in enumerate(tab_defs):
            btn = _term_tab_button(label, self, b"tabClicked:",
                                   active=(idx == 0), width=btn_w)
            btn.setTag_(idx)
            btn.setFrame_(NSMakeRect(x, y_btn, btn_w, 30))
            self.tab_bar.addSubview_(btn)
            self.tab_buttons.append(btn)
            x += btn_w

        # ----- Content container -----
        c_y = 12
        c_h = WINDOW_H - tab_bar_h - 1 - c_y - 12
        self.content_container = NSView.alloc().initWithFrame_(
            NSMakeRect(12, c_y, WINDOW_W - 24, c_h))
        self.content_container.setAutoresizingMask_(2 | 16)
        _set_bg(self.content_container, BG())
        content.addSubview_(self.content_container)

        # Build each section view inside container
        sec_w = WINDOW_W - 24
        sec_h = c_h
        for idx, (ident, label, builder) in enumerate(tab_defs):
            sec = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, sec_w, sec_h))
            sec.setAutoresizingMask_(2 | 16)
            _set_bg(sec, BG())
            sec.setHidden_(idx != 0)
            builder(sec)
            self.content_container.addSubview_(sec)
            self.tab_sections.append(sec)

        self.refresh_data()

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, b"tick:", None, True)

        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    def tabClicked_(self, sender):
        idx = int(sender.tag())
        for i, sec in enumerate(self.tab_sections):
            sec.setHidden_(i != idx)
        for i, btn in enumerate(self.tab_buttons):
            _term_tab_button_update(btn, self.tab_labels[i], active=(i == idx))

    # ============================================================
    # Tab builders
    # ============================================================

    @objc.python_method
    def tab_overview(self, view):
        w = view.frame().size.width
        h = view.frame().size.height
        col_w = (w - 60) // 2  # 2 columns with gap
        right_x = 40 + col_w  # x of right column

        # Title
        title = _label(t("dash.live_status"), bold=True, size=22)
        title.setFrame_(NSMakeRect(20, h - 50, 600, 28))
        view.addSubview_(title)

        # ========== LEFT COLUMN: live status ==========
        self.lbl_status_net = _label("Ağ: —", size=14, width=col_w)
        self.lbl_status_net.setFrame_(NSMakeRect(20, h - 90, col_w, 20))
        view.addSubview_(self.lbl_status_net)

        lbl_today_caption = _label(t("dash.today_total"), bold=True, size=11,
                                   color=FG_DIMMER())
        lbl_today_caption.setFrame_(NSMakeRect(20, h - 140, col_w, 16))
        view.addSubview_(lbl_today_caption)

        self.lbl_today_big = _label("—", bold=True, size=44,
                                    color=FG_AMBER())
        self.lbl_today_big.setFrame_(NSMakeRect(20, h - 200, col_w, 56))
        view.addSubview_(self.lbl_today_big)

        lbl_speed_caption = _label(t("dash.live_speed"), bold=True, size=11,
                                   color=FG_DIMMER())
        lbl_speed_caption.setFrame_(NSMakeRect(20, h - 250, col_w, 16))
        view.addSubview_(lbl_speed_caption)

        self.lbl_speed_dn = _label("↓ —", size=20,
                                   color=FG_TEAL(), width=col_w // 2 - 5)
        self.lbl_speed_dn.setFrame_(NSMakeRect(20, h - 285, col_w // 2 - 5, 28))
        view.addSubview_(self.lbl_speed_dn)

        self.lbl_speed_up = _label("↑ —", size=20,
                                   color=FG_PINK(), width=col_w // 2 - 5)
        self.lbl_speed_up.setFrame_(NSMakeRect(20 + col_w // 2, h - 285, col_w // 2 - 5, 28))
        view.addSubview_(self.lbl_speed_up)

        lbl_break_caption = _label(t("dash.today_detail"), bold=True, size=11,
                                   color=FG_DIMMER())
        lbl_break_caption.setFrame_(NSMakeRect(20, h - 340, col_w, 16))
        view.addSubview_(lbl_break_caption)

        self.lbl_today_in = _label(t("dash.downloaded", v="—"), size=14,
                                   color=FG_TEAL(), width=col_w)
        self.lbl_today_in.setFrame_(NSMakeRect(20, h - 370, col_w, 20))
        view.addSubview_(self.lbl_today_in)

        self.lbl_today_out = _label(t("dash.uploaded", v="—"), size=14,
                                    color=FG_PINK(), width=col_w)
        self.lbl_today_out.setFrame_(NSMakeRect(20, h - 395, col_w, 20))
        view.addSubview_(self.lbl_today_out)

        hint = _label(t("dash.auto_refresh_hint"),
                      size=11, color=FG_DIMMER())
        hint.setFrame_(NSMakeRect(20, 16, col_w, 16))
        view.addSubview_(hint)

        # ========== RIGHT COLUMN: speed test ==========
        st_cap = _label(t("dash.speedtest.title"), bold=True, size=11,
                        color=FG_DIMMER())
        st_cap.setFrame_(NSMakeRect(right_x, h - 90, col_w, 16))
        view.addSubview_(st_cap)

        self.st_button = _button(t("dash.speedtest.start"), self, b"startSpeedTest:", width=170)
        self.st_button.setFrame_(NSMakeRect(right_x, h - 130, 170, 34))
        view.addSubview_(self.st_button)

        self.st_status = _label("", size=12, color=FG_DIM(),
                                width=col_w - 20)
        self.st_status.setFrame_(NSMakeRect(right_x + 180, h - 124, col_w - 200, 18))
        view.addSubview_(self.st_status)

        # Result block
        self.st_dl_label = _label(t("dash.speedtest.dl"), bold=True, size=10,
                                  color=FG_DIMMER())
        self.st_dl_label.setFrame_(NSMakeRect(right_x, h - 165, 100, 14))
        view.addSubview_(self.st_dl_label)

        self.st_dl_value = _label("—", bold=True, size=20,
                                  color=FG_TEAL(), width=180)
        self.st_dl_value.setFrame_(NSMakeRect(right_x, h - 195, 180, 28))
        view.addSubview_(self.st_dl_value)

        self.st_ul_label = _label(t("dash.speedtest.ul"), bold=True, size=10,
                                  color=FG_DIMMER())
        self.st_ul_label.setFrame_(NSMakeRect(right_x + 190, h - 165, 100, 14))
        view.addSubview_(self.st_ul_label)

        self.st_ul_value = _label("—", bold=True, size=20,
                                  color=FG_PINK(), width=180)
        self.st_ul_value.setFrame_(NSMakeRect(right_x + 190, h - 195, 180, 28))
        view.addSubview_(self.st_ul_value)

        self.st_rtt_label = _label(t("dash.speedtest.latency"), bold=True, size=10,
                                   color=FG_DIMMER())
        self.st_rtt_label.setFrame_(NSMakeRect(right_x, h - 225, 200, 14))
        view.addSubview_(self.st_rtt_label)

        self.st_rtt_value = _label("—", bold=True, size=14, width=col_w - 20)
        self.st_rtt_value.setFrame_(NSMakeRect(right_x, h - 250, col_w - 20, 20))
        view.addSubview_(self.st_rtt_value)

        # History label
        self.st_hist_cap = _label(t("dash.speedtest.history"), bold=True, size=11,
                                  color=FG_DIMMER())
        self.st_hist_cap.setFrame_(NSMakeRect(right_x, h - 290, col_w, 16))
        view.addSubview_(self.st_hist_cap)

        # History scroll
        hist_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(right_x, 40, col_w - 20, h - 340))
        hist_scroll.setHasVerticalScroller_(True)
        hist_scroll.setBorderType_(0)
        self.st_hist_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, col_w - 40, h - 340))
        hist_scroll.setDocumentView_(self.st_hist_view)
        view.addSubview_(hist_scroll)

        self._refresh_speedtest_history()

    @objc.python_method
    def tab_apps(self, view):
        w = view.frame().size.width
        h = view.frame().size.height

        # --- Title bar (toggle between list / detail title) ---
        self.apps_title = _label(t("dash.title.apps"),
                                 bold=True, size=18, width=700)
        self.apps_title.setFrame_(NSMakeRect(20, h - 40, 700, 24))
        view.addSubview_(self.apps_title)

        self.apps_back_btn = _button(t("dash.back"), self, b"appBack:", width=90)
        self.apps_back_btn.setFrame_(NSMakeRect(20, h - 42, 90, 26))
        self.apps_back_btn.setHidden_(True)
        view.addSubview_(self.apps_back_btn)

        self.apps_full_report_btn = _button(t("dash.full_report"), self, b"appOpenFullReport:", width=160)
        self.apps_full_report_btn.setFrame_(NSMakeRect(w - 180, h - 42, 160, 26))
        self.apps_full_report_btn.setHidden_(True)
        view.addSubview_(self.apps_full_report_btn)

        # --- LIST MODE widgets ---
        self.apps_list_views = []

        lbl = _label(t("dash.period") + ":", size=12)
        lbl.setFrame_(NSMakeRect(20, h - 78, 60, 18))
        view.addSubview_(lbl)
        self.apps_list_views.append(lbl)

        self.app_period = _popup(_period_labels(), t("period.today"),
                                 width=140, target=self,
                                 action=b"appPeriodChanged:")
        self.app_period.setFrame_(NSMakeRect(80, h - 82, 140, 26))
        view.addSubview_(self.app_period)
        self.apps_list_views.append(self.app_period)

        # Search field (terminal-styled)
        self.app_search = _TermSearch.alloc().initWithFrame_(
            NSMakeRect(240, h - 84, 280, 28))
        self.app_search.configure(t("dash.search.app"), self, b"appSearchChanged:")
        view.addSubview_(self.app_search)
        self.apps_list_views.append(self.app_search)

        # Sortable column headers (clickable buttons styled as labels)
        self.app_header_buttons = {}
        col_y = h - 116
        for x, cw, col_key, label in [
            (20, 360, "name", t("dash.col.app")),
            (380, 120, "total", t("dash.col.total")),
            (500, 120, "in", t("dash.col.in")),
            (620, 120, "out", t("dash.col.out")),
        ]:
            hdr = _sort_header(label, self, b"appSortHeader:", width=cw)
            hdr.setTag_(["name", "total", "in", "out"].index(col_key))
            hdr.setFrame_(NSMakeRect(x, col_y - 6, cw, 22))
            view.addSubview_(hdr)
            self.app_header_buttons[col_key] = hdr
            self.apps_list_views.append(hdr)
        # Action column header (no sort)
        empty_hdr = _position(_label("", width=80), 740, col_y, 80, 14)
        view.addSubview_(empty_hdr)
        self.apps_list_views.append(empty_hdr)

        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, 20, w - 40, h - 150))
        scroll.setHasVerticalScroller_(True)
        scroll.setAutoresizingMask_(2 | 16)
        scroll.setBorderType_(0)
        self.apps_rows_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w - 60, h - 150))
        scroll.setDocumentView_(self.apps_rows_view)
        view.addSubview_(scroll)
        self.apps_list_views.append(scroll)

        # --- DETAIL MODE widgets ---
        self.apps_detail_views = []

        # Big stats row
        self.apps_d_total = _label("—", bold=True, size=26,
                                   color=FG_AMBER(), width=220)
        self.apps_d_total.setFrame_(NSMakeRect(20, h - 110, 220, 32))
        view.addSubview_(self.apps_d_total)
        self.apps_detail_views.append(self.apps_d_total)

        self.apps_d_total_cap = _label(t("dash.col.total").upper(), bold=True, size=10,
                                       color=FG_DIMMER(), width=200)
        self.apps_d_total_cap.setFrame_(NSMakeRect(20, h - 82, 200, 14))
        view.addSubview_(self.apps_d_total_cap)
        self.apps_detail_views.append(self.apps_d_total_cap)

        self.apps_d_in = _label("—", bold=True, size=20,
                                color=FG_TEAL(), width=220)
        self.apps_d_in.setFrame_(NSMakeRect(260, h - 108, 220, 28))
        view.addSubview_(self.apps_d_in)
        self.apps_detail_views.append(self.apps_d_in)

        self.apps_d_in_cap = _label(t("dash.col.in").upper(), bold=True, size=10,
                                    color=FG_DIMMER(), width=200)
        self.apps_d_in_cap.setFrame_(NSMakeRect(260, h - 82, 200, 14))
        view.addSubview_(self.apps_d_in_cap)
        self.apps_detail_views.append(self.apps_d_in_cap)

        self.apps_d_out = _label("—", bold=True, size=20,
                                 color=FG_PINK(), width=220)
        self.apps_d_out.setFrame_(NSMakeRect(500, h - 108, 220, 28))
        view.addSubview_(self.apps_d_out)
        self.apps_detail_views.append(self.apps_d_out)

        self.apps_d_out_cap = _label(t("dash.col.out").upper(), bold=True, size=10,
                                     color=FG_DIMMER(), width=200)
        self.apps_d_out_cap.setFrame_(NSMakeRect(500, h - 82, 200, 14))
        view.addSubview_(self.apps_d_out_cap)
        self.apps_detail_views.append(self.apps_d_out_cap)

        # Section label
        self.apps_d_section = _label(t("dash.targets_for_app"), bold=True, size=11,
                                     color=FG_DIMMER(), width=400)
        self.apps_d_section.setFrame_(NSMakeRect(20, h - 142, 400, 14))
        view.addSubview_(self.apps_d_section)
        self.apps_detail_views.append(self.apps_d_section)

        # Detail column headers
        for x, cw, label in [(20, 240, t("dash.col.host")), (260, 60, t("dash.col.country")),
                             (320, 220, t("dash.col.isp")), (540, 110, t("dash.col.total")),
                             (660, 110, "↓"), (780, 110, "↑")]:
            hdr = _position(_label(label, bold=True, size=10,
                                   color=FG_DIMMER(), width=cw),
                            x, h - 168, cw, 14)
            view.addSubview_(hdr)
            self.apps_detail_views.append(hdr)

        d_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, 20, w - 40, h - 200))
        d_scroll.setHasVerticalScroller_(True)
        d_scroll.setAutoresizingMask_(2 | 16)
        d_scroll.setBorderType_(0)
        self.apps_d_rows_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w - 60, h - 200))
        d_scroll.setDocumentView_(self.apps_d_rows_view)
        view.addSubview_(d_scroll)
        self.apps_detail_views.append(d_scroll)

        # Hide detail by default
        for v in self.apps_detail_views:
            v.setHidden_(True)

    @objc.python_method
    def tab_destinations(self, view):
        w = view.frame().size.width
        h = view.frame().size.height

        self.dest_title = _label(t("dash.title.dest"), bold=True, size=18, width=700)
        self.dest_title.setFrame_(NSMakeRect(20, h - 40, 700, 24))
        view.addSubview_(self.dest_title)

        self.dest_back_btn = _button(t("dash.back"), self, b"destBack:", width=90)
        self.dest_back_btn.setFrame_(NSMakeRect(20, h - 42, 90, 26))
        self.dest_back_btn.setHidden_(True)
        view.addSubview_(self.dest_back_btn)

        # --- LIST MODE ---
        self.dest_list_views = []

        lbl = _label(t("dash.period") + ":", size=12)
        lbl.setFrame_(NSMakeRect(20, h - 78, 60, 18))
        view.addSubview_(lbl)
        self.dest_list_views.append(lbl)

        self.dest_period = _popup(_period_labels(), t("period.today"),
                                  width=140, target=self,
                                  action=b"destPeriodChanged:")
        self.dest_period.setFrame_(NSMakeRect(80, h - 82, 140, 26))
        view.addSubview_(self.dest_period)
        self.dest_list_views.append(self.dest_period)

        # Search field (terminal-styled)
        self.dest_search = _TermSearch.alloc().initWithFrame_(
            NSMakeRect(240, h - 84, 280, 28))
        self.dest_search.configure(t("dash.search.dest"), self, b"destSearchChanged:")
        view.addSubview_(self.dest_search)
        self.dest_list_views.append(self.dest_search)

        self.dest_header_buttons = {}
        col_y = h - 116
        for x, cw, col_key, label in [
            (20, 220, "host", t("dash.col.host")),
            (240, 60, "country", t("dash.col.country")),
            (300, 220, "isp", t("dash.col.isp")),
            (520, 110, "total", t("dash.col.total")),
            (640, 110, "in", "↓"),
            (760, 110, "out", "↑"),
        ]:
            hdr = _sort_header(label, self, b"destSortHeader:", width=cw)
            hdr.setTag_(["host", "country", "isp", "total", "in", "out"].index(col_key))
            hdr.setFrame_(NSMakeRect(x, col_y - 6, cw, 22))
            view.addSubview_(hdr)
            self.dest_header_buttons[col_key] = hdr
            self.dest_list_views.append(hdr)
        empty_hdr = _position(_label("", width=60), 840, col_y, 60, 14)
        view.addSubview_(empty_hdr)
        self.dest_list_views.append(empty_hdr)

        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, 20, w - 40, h - 150))
        scroll.setHasVerticalScroller_(True)
        scroll.setAutoresizingMask_(2 | 16)
        scroll.setBorderType_(0)
        self.dest_rows_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w - 60, h - 150))
        scroll.setDocumentView_(self.dest_rows_view)
        view.addSubview_(scroll)
        self.dest_list_views.append(scroll)

        # --- DETAIL MODE ---
        self.dest_detail_views = []

        self.dest_d_total = _label("—", bold=True, size=26,
                                   color=FG_AMBER(), width=220)
        self.dest_d_total.setFrame_(NSMakeRect(20, h - 110, 220, 32))
        view.addSubview_(self.dest_d_total)
        self.dest_detail_views.append(self.dest_d_total)

        self.dest_d_total_cap = _label(t("dash.col.total").upper(), bold=True, size=10,
                                       color=FG_DIMMER(), width=200)
        self.dest_d_total_cap.setFrame_(NSMakeRect(20, h - 82, 200, 14))
        view.addSubview_(self.dest_d_total_cap)
        self.dest_detail_views.append(self.dest_d_total_cap)

        self.dest_d_in = _label("—", bold=True, size=20,
                                color=FG_TEAL(), width=220)
        self.dest_d_in.setFrame_(NSMakeRect(260, h - 108, 220, 28))
        view.addSubview_(self.dest_d_in)
        self.dest_detail_views.append(self.dest_d_in)

        self.dest_d_in_cap = _label("↓ " + t("table.fetched").upper(), bold=True, size=10,
                                    color=FG_DIMMER(), width=200)
        self.dest_d_in_cap.setFrame_(NSMakeRect(260, h - 82, 200, 14))
        view.addSubview_(self.dest_d_in_cap)
        self.dest_detail_views.append(self.dest_d_in_cap)

        self.dest_d_out = _label("—", bold=True, size=20,
                                 color=FG_PINK(), width=220)
        self.dest_d_out.setFrame_(NSMakeRect(500, h - 108, 220, 28))
        view.addSubview_(self.dest_d_out)
        self.dest_detail_views.append(self.dest_d_out)

        self.dest_d_out_cap = _label("↑ " + t("table.sent").upper(), bold=True, size=10,
                                     color=FG_DIMMER(), width=200)
        self.dest_d_out_cap.setFrame_(NSMakeRect(500, h - 82, 200, 14))
        view.addSubview_(self.dest_d_out_cap)
        self.dest_detail_views.append(self.dest_d_out_cap)

        # Geo / host info
        self.dest_d_info = _label("—", size=12,
                                  color=FG_DIM(), width=900)
        self.dest_d_info.setFrame_(NSMakeRect(20, h - 138, 900, 18))
        view.addSubview_(self.dest_d_info)
        self.dest_detail_views.append(self.dest_d_info)

        self.dest_d_section = _label(t("dash.apps_for_remote"), bold=True, size=11,
                                     color=FG_DIMMER(), width=400)
        self.dest_d_section.setFrame_(NSMakeRect(20, h - 168, 400, 14))
        view.addSubview_(self.dest_d_section)
        self.dest_detail_views.append(self.dest_d_section)

        for x, cw, label in [(20, 360, t("dash.col.app")), (380, 120, t("dash.col.total")),
                             (500, 120, t("dash.col.in")), (620, 120, t("dash.col.out"))]:
            hdr = _position(_label(label, bold=True, size=10,
                                   color=FG_DIMMER(), width=cw),
                            x, h - 192, cw, 14)
            view.addSubview_(hdr)
            self.dest_detail_views.append(hdr)

        d_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, 20, w - 40, h - 220))
        d_scroll.setHasVerticalScroller_(True)
        d_scroll.setAutoresizingMask_(2 | 16)
        d_scroll.setBorderType_(0)
        self.dest_d_rows_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w - 60, h - 220))
        d_scroll.setDocumentView_(self.dest_d_rows_view)
        view.addSubview_(d_scroll)
        self.dest_detail_views.append(d_scroll)

        for v in self.dest_detail_views:
            v.setHidden_(True)

    @objc.python_method
    def tab_quotas(self, view):
        w = view.frame().size.width
        h = view.frame().size.height

        title = _label(t("dash.title.quotas"), bold=True, size=18)
        title.setFrame_(NSMakeRect(20, h - 40, 500, 24))
        view.addSubview_(title)

        subtitle = _label(t("dash.quotas.subtitle"),
                          size=12, color=FG_DIM())
        subtitle.setFrame_(NSMakeRect(20, h - 64, 600, 18))
        view.addSubview_(subtitle)

        # Scroll area for quota rows
        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, 70, w - 40, h - 150))
        scroll.setHasVerticalScroller_(True)
        scroll.setAutoresizingMask_(2 | 16)
        scroll.setBorderType_(0)
        self.quota_rows_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w - 60, h - 150))
        scroll.setDocumentView_(self.quota_rows_view)
        view.addSubview_(scroll)

        # Edit button
        btn = _button(t("dash.quotas.edit_button"), self, b"openQuotaEditor:", width=180)
        btn.setFrame_(NSMakeRect(20, 22, 180, 28))
        view.addSubview_(btn)

    @objc.python_method
    def tab_networks(self, view):
        w = view.frame().size.width
        h = view.frame().size.height

        title = _label(t("dash.title.networks"), bold=True, size=18)
        title.setFrame_(NSMakeRect(20, h - 40, 500, 24))
        view.addSubview_(title)

        self.lbl_net_current = _label("Şu an: —", bold=True, size=14, width=600)
        self.lbl_net_current.setFrame_(NSMakeRect(20, h - 75, 600, 20))
        view.addSubview_(self.lbl_net_current)

        # Headers
        view.addSubview_(_position(
            _label(t("dash.networks.col_ip"), bold=True, size=10,
                   color=FG_DIMMER(), width=220),
            20, h - 110, 220, 14))
        view.addSubview_(_position(
            _label(t("dash.networks.col_name"), bold=True, size=10,
                   color=FG_DIMMER(), width=300),
            260, h - 110, 300, 14))

        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, 70, w - 40, h - 200))
        scroll.setHasVerticalScroller_(True)
        scroll.setAutoresizingMask_(2 | 16)
        scroll.setBorderType_(0)
        self.net_aliases_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w - 60, h - 200))
        scroll.setDocumentView_(self.net_aliases_view)
        view.addSubview_(scroll)

        btn = _button(t("dash.networks.edit_button"), self, b"openNetworkEditor:", width=180)
        btn.setFrame_(NSMakeRect(20, 22, 180, 28))
        view.addSubview_(btn)

    @objc.python_method
    def tab_reports(self, view):
        w = view.frame().size.width
        h = view.frame().size.height

        title = _label(t("dash.title.reports"), bold=True, size=18)
        title.setFrame_(NSMakeRect(20, h - 40, 500, 24))
        view.addSubview_(title)

        desc = _label(t("dash.reports.subtitle"),
                      size=12, color=FG_DIM())
        desc.setFrame_(NSMakeRect(20, h - 64, 700, 18))
        view.addSubview_(desc)

        labels = [t("menu.report.daily"), t("menu.report.monthly"),
                  t("menu.report.yearly"), t("menu.report.last30")]
        descs = [t("dash.reports.daily_desc"),
                 t("dash.reports.monthly_desc"),
                 t("dash.reports.yearly_desc"),
                 t("dash.reports.last30_desc")]
        for i, (label, dtext) in enumerate(zip(labels, descs)):
            y = h - 130 - i * 70
            btn = _button(label, self, b"openReportByTag:", width=220)
            btn.setTag_(i)
            btn.setFrame_(NSMakeRect(20, y, 220, 32))
            view.addSubview_(btn)

            d = _label(dtext, size=12, color=FG_DIM(),
                       width=600)
            d.setFrame_(NSMakeRect(260, y + 6, 600, 18))
            view.addSubview_(d)

    @objc.python_method
    def tab_export(self, view):
        w = view.frame().size.width
        h = view.frame().size.height

        title = _label(t("dash.title.export"), bold=True, size=18)
        title.setFrame_(NSMakeRect(20, h - 40, 500, 24))
        view.addSubview_(title)

        desc = _label(t("dash.export.subtitle"),
                      size=12, color=FG_DIM())
        desc.setFrame_(NSMakeRect(20, h - 64, 700, 18))
        view.addSubview_(desc)

        # Period
        lbl1 = _label(t("dash.period") + ":", size=12)
        lbl1.setFrame_(NSMakeRect(20, h - 110, 70, 18))
        view.addSubview_(lbl1)
        self.exp_period = _popup(_period_labels(), t("period.today"), width=140)
        self.exp_period.setFrame_(NSMakeRect(95, h - 114, 140, 26))
        view.addSubview_(self.exp_period)

        # Format
        lbl2 = _label(t("dash.export.format") + ":", size=12)
        lbl2.setFrame_(NSMakeRect(265, h - 110, 70, 18))
        view.addSubview_(lbl2)
        self.exp_format = _popup(["CSV", "JSON"], "CSV", width=100)
        self.exp_format.setFrame_(NSMakeRect(335, h - 114, 100, 26))
        view.addSubview_(self.exp_format)

        # Button
        btn = _button(t("dash.export.button"), self, b"doExport:", width=200)
        btn.setFrame_(NSMakeRect(465, h - 114, 200, 26))
        view.addSubview_(btn)

        # Status
        self.exp_status = _label("", size=12,
                                 color=FG_DIMMER(), width=800)
        self.exp_status.setFrame_(NSMakeRect(20, h - 160, 800, 18))
        view.addSubview_(self.exp_status)

        # CSV format hint
        hint = _label(
            t("dash.export.columns"),
            size=11, color=FG_DIMMER())
        hint.setFrame_(NSMakeRect(20, h - 200, 800, 16))
        view.addSubview_(hint)

    @objc.python_method
    def tab_settings(self, view):
        w = view.frame().size.width
        h = view.frame().size.height

        title = _label(t("dash.title.settings"), bold=True, size=18)
        title.setFrame_(NSMakeRect(20, h - 40, 500, 24))
        view.addSubview_(title)

        # Language
        lbl = _label(t("dash.settings.lang") + ":", size=13)
        lbl.setFrame_(NSMakeRect(20, h - 84, 80, 20))
        view.addSubview_(lbl)

        current_lang = i18n.get_lang()
        lang_titles = list(LANG_NAMES.values())
        current_title = LANG_NAMES.get(current_lang, "Türkçe")
        self.lang_popup = _popup(lang_titles, current_title, width=200,
                                 target=self, action=b"languageChanged:")
        self.lang_popup.setFrame_(NSMakeRect(110, h - 88, 200, 26))
        view.addSubview_(self.lang_popup)

        # Reset
        lbl2 = _label(t("dash.settings.daily_counter") + ":", size=13)
        lbl2.setFrame_(NSMakeRect(20, h - 130, 130, 20))
        view.addSubview_(lbl2)

        btn = _button(t("dash.settings.reset_button"), self, b"resetToday:", width=120)
        btn.setFrame_(NSMakeRect(160, h - 134, 120, 26))
        view.addSubview_(btn)

        # Quit app
        lbl3 = _label(t("dash.settings.app") + ":", size=13)
        lbl3.setFrame_(NSMakeRect(20, h - 176, 130, 20))
        view.addSubview_(lbl3)

        quit_btn = _button(t("dash.settings.quit_button"), self, b"quitApp:", width=200)
        quit_btn.setFrame_(NSMakeRect(160, h - 180, 200, 26))
        view.addSubview_(quit_btn)

        # Version
        ver = _label("1 Bit Data · v0.1 · Python + rumps + PyObjC",
                     size=11, color=FG_DIMMER())
        ver.setFrame_(NSMakeRect(20, 16, 700, 16))
        view.addSubview_(ver)

    # ============================================================
    # Data refresh
    # ============================================================

    @objc.python_method
    def refresh_data(self):
        try:
            self._refresh_overview()
            if self._app_detail_current:
                self._populate_app_detail(self._app_detail_current)
            else:
                self._refresh_apps()
            if self._dest_detail_current:
                self._populate_dest_detail(self._dest_detail_current)
            else:
                self._refresh_destinations()
            self._refresh_quotas()
            self._refresh_networks()
        except Exception as e:
            print(f"dashboard refresh error: {e}", flush=True)

    @objc.python_method
    def _refresh_overview(self):
        try:
            net = data_tracker.get_current_network()
        except Exception:
            net = "—"
        self.lbl_status_net.setStringValue_(t("dash.network") + f": {net}")

        recv, sent = _read_state()
        total = recv + sent
        self.lbl_today_big.setStringValue_(fmt_bytes(total))
        self.lbl_today_in.setStringValue_(t("dash.downloaded", v=fmt_bytes(recv)))
        self.lbl_today_out.setStringValue_(t("dash.uploaded", v=fmt_bytes(sent)))

        io = psutil.net_io_counters()
        if self._psutil_last_recv == 0:
            self._psutil_last_recv = io.bytes_recv
            self._psutil_last_sent = io.bytes_sent
            self.lbl_speed_dn.setStringValue_("↓ —")
            self.lbl_speed_up.setStringValue_("↑ —")
            return
        d_recv = max(0, io.bytes_recv - self._psutil_last_recv) / 2
        d_sent = max(0, io.bytes_sent - self._psutil_last_sent) / 2
        self._psutil_last_recv = io.bytes_recv
        self._psutil_last_sent = io.bytes_sent
        self.lbl_speed_dn.setStringValue_(f"↓ {fmt_speed(d_recv)}")
        self.lbl_speed_up.setStringValue_(f"↑ {fmt_speed(d_sent)}")

    @objc.python_method
    def _refresh_apps(self):
        for sub in list(self.apps_rows_view.subviews()):
            sub.removeFromSuperview()
        self._app_buttons = []

        start, end = _period_range(self._app_period)
        rows = data_tracker.top_apps_range(start, end, limit=500)

        # Apply filter
        if self._app_filter:
            f = self._app_filter.lower()
            rows = [r for r in rows if f in r[0].lower()]

        # Apply sort
        col, direction = self._app_sort
        key_fn = {"name": lambda r: r[0].lower(), "total": lambda r: r[1],
                  "in": lambda r: r[2] or 0, "out": lambda r: r[3] or 0}.get(col)
        if key_fn:
            rows.sort(key=key_fn, reverse=(direction == "desc"))
        rows = rows[:200]

        # Update header indicators
        self._refresh_app_header_titles()

        row_h = 28
        total_h = max(40, len(rows) * row_h + 12)
        w = self.apps_rows_view.frame().size.width
        self.apps_rows_view.setFrameSize_(NSMakeSize(w, total_h))

        for i, (app, total, b_in, b_out) in enumerate(rows):
            y = total_h - (i + 1) * row_h
            container = NSView.alloc().initWithFrame_(NSMakeRect(0, y, w, row_h))

            container.addSubview_(_position(
                _mono_label(app[:48], width=360), 0, 6, 360, 18))
            container.addSubview_(_position(
                _mono_label(fmt_bytes(total), width=120,
                            color=FG_AMBER()), 360, 6, 120, 18))
            container.addSubview_(_position(
                _mono_label(fmt_bytes(b_in), width=120,
                            color=FG_TEAL()), 480, 6, 120, 18))
            container.addSubview_(_position(
                _mono_label(fmt_bytes(b_out), width=120,
                            color=FG_PINK()), 600, 6, 120, 18))

            btn = _button(t("dash.detail"), self, b"openAppDetail:", width=80)
            btn.setTag_(i)
            btn.setFrame_(NSMakeRect(720, 2, 80, 24))
            container.addSubview_(btn)
            self._app_buttons.append(app)

            self.apps_rows_view.addSubview_(container)

    @objc.python_method
    def _refresh_destinations(self):
        for sub in list(self.dest_rows_view.subviews()):
            sub.removeFromSuperview()
        self._dest_buttons = []

        start, end = _period_range(self._dest_period)
        rows = data_tracker.top_remotes_range(start, end, limit=500)
        ips = [r[0] for r in rows]
        meta = data_tracker.get_remote_meta(ips)

        # Apply filter
        if self._dest_filter:
            f = self._dest_filter.lower()
            def matches(r):
                ip = r[0]
                m = meta.get(ip, {})
                blob = " ".join(filter(None, [
                    ip,
                    m.get("hostname") or "",
                    m.get("country") or "",
                    m.get("country_code") or "",
                    m.get("isp") or "",
                    m.get("city") or "",
                ])).lower()
                return f in blob
            rows = [r for r in rows if matches(r)]

        # Sort
        col, direction = self._dest_sort
        def k_host(r): return (meta.get(r[0], {}).get("hostname") or r[0]).lower()
        def k_country(r): return (meta.get(r[0], {}).get("country") or "").lower()
        def k_isp(r): return (meta.get(r[0], {}).get("isp") or "").lower()
        key_fn = {"host": k_host, "country": k_country, "isp": k_isp,
                  "total": lambda r: r[1], "in": lambda r: r[2] or 0,
                  "out": lambda r: r[3] or 0}.get(col)
        if key_fn:
            rows.sort(key=key_fn, reverse=(direction == "desc"))
        rows = rows[:200]

        self._refresh_dest_header_titles()

        row_h = 28
        total_h = max(40, len(rows) * row_h + 12)
        w = self.dest_rows_view.frame().size.width
        self.dest_rows_view.setFrameSize_(NSMakeSize(w, total_h))

        for i, (remote, total, b_in, b_out) in enumerate(rows):
            y = total_h - (i + 1) * row_h
            container = NSView.alloc().initWithFrame_(NSMakeRect(0, y, w, row_h))

            m = meta.get(remote, {})
            host = m.get("hostname") or remote
            cc = (m.get("country_code") or "").upper()
            isp = m.get("isp") or ""
            city = m.get("city") or ""
            isp_str = isp + (f" / {city}" if city else "")

            container.addSubview_(_position(
                _mono_label(host[:32], width=220), 0, 6, 220, 18))
            container.addSubview_(_position(
                _mono_label(f"[{cc}]" if cc else "—", width=60), 220, 6, 60, 18))
            container.addSubview_(_position(
                _mono_label(isp_str[:32], width=220), 280, 6, 220, 18))
            container.addSubview_(_position(
                _mono_label(fmt_bytes(total), width=110,
                            color=FG_AMBER()), 500, 6, 110, 18))
            container.addSubview_(_position(
                _mono_label(fmt_bytes(b_in), width=110,
                            color=FG_TEAL()), 620, 6, 110, 18))
            container.addSubview_(_position(
                _mono_label(fmt_bytes(b_out), width=110,
                            color=FG_PINK()), 740, 6, 110, 18))

            btn = _button(t("dash.detail"), self, b"openDestDetail:", width=60)
            btn.setTag_(i)
            btn.setFrame_(NSMakeRect(820, 2, 60, 24))
            container.addSubview_(btn)
            self._dest_buttons.append(remote)

            self.dest_rows_view.addSubview_(container)

    @objc.python_method
    def _refresh_quotas(self):
        for sub in list(self.quota_rows_view.subviews()):
            sub.removeFromSuperview()

        try:
            results = quotas_mod.check_quotas()
        except Exception:
            results = []

        w = self.quota_rows_view.frame().size.width
        if not results:
            l = _label(t("dash.quotas.empty"),
                       size=12, color=FG_DIMMER())
            l.setFrame_(NSMakeRect(10, self.quota_rows_view.frame().size.height - 30, w - 20, 18))
            self.quota_rows_view.addSubview_(l)
            return

        row_h = 50
        total_h = max(80, len(results) * row_h + 16)
        self.quota_rows_view.setFrameSize_(NSMakeSize(w, total_h))

        for i, r in enumerate(results):
            y = total_h - (i + 1) * row_h
            pct = min(100, r["pct"])
            color = FG_RED() if r["exceeded"] else (
                FG_AMBER() if pct > 80 else FG_GREEN())

            self.quota_rows_view.addSubview_(_position(
                _label(f"{r['label']}  ·  {r['period']}",
                       bold=True, size=13, width=400),
                10, y + 26, 400, 18))

            self.quota_rows_view.addSubview_(_position(
                _label(f"{fmt_bytes(r['used'])} / {fmt_bytes(r['limit'])}  ({pct}%)",
                       size=12, color=color, width=300, align="right"),
                w - 320, y + 26, 310, 18))

            bar = NSLevelIndicator.alloc().initWithFrame_(NSMakeRect(10, y + 4, w - 30, 14))
            bar.setLevelIndicatorStyle_(NSLevelIndicatorStyleContinuousCapacity)
            bar.setMinValue_(0)
            bar.setMaxValue_(100)
            bar.setWarningValue_(80)
            bar.setCriticalValue_(100)
            bar.setIntValue_(pct)
            self.quota_rows_view.addSubview_(bar)

    @objc.python_method
    def _refresh_networks(self):
        try:
            current = data_tracker.get_current_network()
        except Exception:
            current = "—"
        self.lbl_net_current.setStringValue_(t("dash.networks.current", n=current))

        for sub in list(self.net_aliases_view.subviews()):
            sub.removeFromSuperview()

        aliases = {}
        try:
            with open(os.path.expanduser("~/.data_monitor_networks.json")) as f:
                aliases = json.load(f)
        except Exception:
            pass

        w = self.net_aliases_view.frame().size.width
        if not aliases:
            l = _label(t("dash.networks.empty"), size=12,
                       color=FG_DIMMER())
            l.setFrame_(NSMakeRect(10, self.net_aliases_view.frame().size.height - 26, 400, 18))
            self.net_aliases_view.addSubview_(l)
            return

        row_h = 28
        total_h = max(60, len(aliases) * row_h + 12)
        self.net_aliases_view.setFrameSize_(NSMakeSize(w, total_h))

        for i, (ip, name) in enumerate(aliases.items()):
            y = total_h - (i + 1) * row_h
            self.net_aliases_view.addSubview_(_position(
                _mono_label(ip, width=220), 10, y + 4, 220, 18))
            self.net_aliases_view.addSubview_(_position(
                _mono_label(name, width=400), 250, y + 4, 400, 18))

    # ============================================================
    # ObjC actions
    # ============================================================

    def tick_(self, _):
        self.refresh_data()

    # ===== Speed test =====

    def startSpeedTest_(self, _):
        # Toggle: if running, stop; else start
        if self._speedtest_proc is not None:
            self._speedtest_cancelled = True
            try:
                self._speedtest_proc.terminate()
            except Exception:
                pass
            self.st_status.setStringValue_(t("dash.speedtest.stopping"))
            return

        self._speedtest_cancelled = False
        self.st_status.setStringValue_(t("dash.speedtest.running"))
        # Clear previous values so live numbers can fill in
        self.st_dl_value.setStringValue_("…")
        self.st_ul_value.setStringValue_("…")
        self.st_rtt_value.setStringValue_("…")
        # Initialize live counter baselines
        io = psutil.net_io_counters()
        import time as _t
        self._st_last_recv = io.bytes_recv
        self._st_last_sent = io.bytes_sent
        self._st_last_ts = _t.time()
        try:
            self._speedtest_proc = speedtest.start_test()
        except FileNotFoundError:
            self.st_status.setStringValue_(t("dash.speedtest.not_found"))
            return
        except Exception as e:
            self.st_status.setStringValue_(t("dash.speedtest.failed") + f": {e}")
            return
        # Restyle button as "Stop" (red)
        attrs = {NSForegroundColorAttributeName: FG_RED(),
                 NSFontAttributeName: _mono_font(12, bold=True)}
        astr = NSAttributedString.alloc().initWithString_attributes_(
            f"[ {t('dash.speedtest.stop')} ]", attrs)
        self.st_button.setAttributedTitle_(astr)
        # Live update timer (twice per second) while test runs
        if self._st_live_timer is None:
            self._st_live_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.5, self, b"speedtestLiveTick:", None, True)
        threading.Thread(target=self._wait_for_speedtest, daemon=True).start()

    def speedtestLiveTick_(self, _):
        """While test runs, show live psutil-measured throughput as DL/UL values."""
        if self._speedtest_proc is None:
            return
        import time as _t
        io = psutil.net_io_counters()
        now = _t.time()
        dt = max(0.001, now - self._st_last_ts)
        d_recv = max(0, io.bytes_recv - self._st_last_recv) / dt
        d_sent = max(0, io.bytes_sent - self._st_last_sent) / dt
        self._st_last_recv = io.bytes_recv
        self._st_last_sent = io.bytes_sent
        self._st_last_ts = now
        self.st_dl_value.setStringValue_(_fmt_bps(d_recv))
        self.st_ul_value.setStringValue_(_fmt_bps(d_sent))

    @objc.python_method
    def _wait_for_speedtest(self):
        proc = self._speedtest_proc
        result = None
        try:
            out, _ = proc.communicate(timeout=120)
            if proc.returncode == 0:
                result = speedtest.parse_output(out)
        except Exception as e:
            print(f"speedtest wait error: {e}", flush=True)
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            b"_speedTestFinished:", result or {}, False)

    def _speedTestFinished_(self, result):
        cancelled = self._speedtest_cancelled
        self._speedtest_proc = None
        self._speedtest_cancelled = False
        # Stop live update timer
        if self._st_live_timer is not None:
            self._st_live_timer.invalidate()
            self._st_live_timer = None
        # Restore button styling (amber Start)
        attrs = {NSForegroundColorAttributeName: FG_AMBER(),
                 NSFontAttributeName: _mono_font(12, bold=True)}
        astr = NSAttributedString.alloc().initWithString_attributes_(
            f"[ {t('dash.speedtest.start')} ]", attrs)
        self.st_button.setAttributedTitle_(astr)

        if cancelled:
            self.st_status.setStringValue_(t("dash.speedtest.cancelled"))
            return
        if not result or not result.get("dl_bps"):
            self.st_status.setStringValue_(t("dash.speedtest.failed"))
            return

        dl = result.get("dl_bps")
        ul = result.get("ul_bps")
        rtt = result.get("base_rtt_ms")
        rpm = result.get("responsiveness_rpm")

        self.st_status.setStringValue_(t("dash.speedtest.done", time=datetime.now().strftime("%H:%M")))
        self.st_dl_value.setStringValue_(_fmt_bps(dl))
        self.st_ul_value.setStringValue_(_fmt_bps(ul))
        rtt_str = f"{rtt:.0f} ms" if rtt else "—"
        if rpm:
            rtt_str += f"   ·   {rpm:.0f} RPM"
        self.st_rtt_value.setStringValue_(rtt_str)

        try:
            net = data_tracker.get_current_network()
        except Exception:
            net = ""
        try:
            data_tracker.record_speedtest(dl, ul, rtt, rpm, net)
            self._refresh_speedtest_history()
        except Exception as e:
            print(f"speedtest record error: {e}", flush=True)

    @objc.python_method
    def _refresh_speedtest_history(self):
        for sub in list(self.st_hist_view.subviews()):
            sub.removeFromSuperview()

        rows = data_tracker.get_speedtests(limit=50)
        w = self.st_hist_view.frame().size.width
        if not rows:
            l = _label(t("dash.speedtest.no_history"), size=11,
                       color=FG_DIMMER())
            l.setFrame_(NSMakeRect(8, self.st_hist_view.frame().size.height - 22, w, 18))
            self.st_hist_view.addSubview_(l)
            return

        row_h = 24
        total_h = max(60, len(rows) * row_h + 8)
        self.st_hist_view.setFrameSize_(NSMakeSize(w, total_h))

        for i, (ts, dl, ul, rtt, rpm, net) in enumerate(rows):
            y = total_h - (i + 1) * row_h
            container = NSView.alloc().initWithFrame_(NSMakeRect(0, y, w, row_h))
            when = datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")
            container.addSubview_(_position(
                _mono_label(when, size=11, width=110), 4, 4, 110, 16))
            container.addSubview_(_position(
                _mono_label(_fmt_bps(dl), size=11,
                            color=FG_TEAL(), width=110),
                118, 4, 110, 16))
            container.addSubview_(_position(
                _mono_label(_fmt_bps(ul), size=11,
                            color=FG_PINK(), width=110),
                232, 4, 110, 16))
            if rtt:
                container.addSubview_(_position(
                    _mono_label(f"{rtt:.0f}ms", size=10,
                                color=FG_DIMMER(), width=80),
                    346, 4, 80, 16))
            self.st_hist_view.addSubview_(container)

    def appPeriodChanged_(self, sender):
        self._app_period = _period_from_label(str(sender.titleOfSelectedItem()))
        self._refresh_apps()

    def destPeriodChanged_(self, sender):
        self._dest_period = _period_from_label(str(sender.titleOfSelectedItem()))
        self._refresh_destinations()

    def openQuotaEditor_(self, _):
        config_ui.open_quotas()

    def openNetworkEditor_(self, _):
        config_ui.open_networks()

    def openAppDetail_(self, sender):
        tag = int(sender.tag())
        if 0 <= tag < len(self._app_buttons):
            self.show_app_detail(self._app_buttons[tag])

    def appBack_(self, _):
        self._app_detail_current = None
        self.apps_title.setStringValue_(t("dash.title.apps"))
        self.apps_back_btn.setHidden_(True)
        self.apps_full_report_btn.setHidden_(True)
        for v in self.apps_list_views:
            v.setHidden_(False)
        for v in self.apps_detail_views:
            v.setHidden_(True)

    @objc.python_method
    def _refresh_app_header_titles(self):
        labels = {"name": t("dash.col.app"), "total": t("dash.col.total"),
                  "in": t("dash.col.in"), "out": t("dash.col.out")}
        active_col, direction = self._app_sort
        arrow = "  ↓" if direction == "desc" else "  ↑"
        for key, btn in self.app_header_buttons.items():
            base = labels[key]
            btn.setTitle_(base + (arrow if key == active_col else ""))

    def appSearchChanged_(self, sender):
        self._app_filter = str(sender.stringValue())
        self._refresh_apps()

    def appSortHeader_(self, sender):
        cols = ["name", "total", "in", "out"]
        col = cols[int(sender.tag())]
        if self._app_sort[0] == col:
            self._app_sort = (col, "asc" if self._app_sort[1] == "desc" else "desc")
        else:
            # Numeric columns default desc; name defaults asc
            self._app_sort = (col, "asc" if col == "name" else "desc")
        self._refresh_apps()

    def appOpenFullReport_(self, _):
        if self._app_detail_current:
            try:
                data_report.open_app_report(self._app_detail_current)
            except Exception as e:
                print(f"full app report error: {e}", flush=True)

    @objc.python_method
    def show_app_detail(self, app):
        self._app_detail_current = app
        self.apps_title.setStringValue_(app)
        self.apps_back_btn.setHidden_(False)
        self.apps_full_report_btn.setHidden_(False)
        for v in self.apps_list_views:
            v.setHidden_(True)
        for v in self.apps_detail_views:
            v.setHidden_(False)
        self._populate_app_detail(app)

    @objc.python_method
    def _populate_app_detail(self, app):
        start, end = _period_range(self._app_period)
        t_in, t_out = data_tracker.app_total(app, start, end)
        total = (t_in or 0) + (t_out or 0)
        self.apps_d_total.setStringValue_(fmt_bytes(total))
        self.apps_d_in.setStringValue_(fmt_bytes(t_in or 0))
        self.apps_d_out.setStringValue_(fmt_bytes(t_out or 0))

        # Populate destinations rows
        for sub in list(self.apps_d_rows_view.subviews()):
            sub.removeFromSuperview()

        remotes = data_tracker.app_top_remotes(app, start, end, limit=100)
        ips = [r[0] for r in remotes]
        meta = data_tracker.get_remote_meta(ips)

        row_h = 26
        total_h = max(40, len(remotes) * row_h + 12)
        w = self.apps_d_rows_view.frame().size.width
        self.apps_d_rows_view.setFrameSize_(NSMakeSize(w, total_h))

        for i, (remote, rtotal, b_in, b_out) in enumerate(remotes):
            y = total_h - (i + 1) * row_h
            container = NSView.alloc().initWithFrame_(NSMakeRect(0, y, w, row_h))
            m = meta.get(remote, {})
            host = m.get("hostname") or remote
            cc = (m.get("country_code") or "").upper()
            isp = m.get("isp") or ""
            city = m.get("city") or ""
            isp_str = isp + (f" / {city}" if city else "")

            container.addSubview_(_position(_mono_label(host[:32], width=240), 0, 4, 240, 18))
            container.addSubview_(_position(_mono_label(f"[{cc}]" if cc else "—", width=60), 240, 4, 60, 18))
            container.addSubview_(_position(_mono_label(isp_str[:32], width=220), 300, 4, 220, 18))
            container.addSubview_(_position(_mono_label(fmt_bytes(rtotal), width=110,
                                                        color=FG_AMBER()), 520, 4, 110, 18))
            container.addSubview_(_position(_mono_label(fmt_bytes(b_in), width=110,
                                                        color=FG_TEAL()), 640, 4, 110, 18))
            container.addSubview_(_position(_mono_label(fmt_bytes(b_out), width=110,
                                                        color=FG_PINK()), 760, 4, 110, 18))
            self.apps_d_rows_view.addSubview_(container)

    @objc.python_method
    def _refresh_dest_header_titles(self):
        labels = {"host": t("dash.col.host"), "country": t("dash.col.country"), "isp": t("dash.col.isp"),
                  "total": t("dash.col.total"), "in": "↓", "out": "↑"}
        active_col, direction = self._dest_sort
        arrow = "  ↓" if direction == "desc" else "  ↑"
        for key, btn in self.dest_header_buttons.items():
            base = labels[key]
            btn.setTitle_(base + (arrow if key == active_col else ""))

    def destSearchChanged_(self, sender):
        self._dest_filter = str(sender.stringValue())
        self._refresh_destinations()

    def destSortHeader_(self, sender):
        cols = ["host", "country", "isp", "total", "in", "out"]
        col = cols[int(sender.tag())]
        if self._dest_sort[0] == col:
            self._dest_sort = (col, "asc" if self._dest_sort[1] == "desc" else "desc")
        else:
            self._dest_sort = (col, "asc" if col in ("host", "country", "isp") else "desc")
        self._refresh_destinations()

    def openDestDetail_(self, sender):
        tag = int(sender.tag())
        if 0 <= tag < len(self._dest_buttons):
            self.show_dest_detail(self._dest_buttons[tag])

    def destBack_(self, _):
        self._dest_detail_current = None
        self.dest_title.setStringValue_(t("dash.title.dest"))
        self.dest_back_btn.setHidden_(True)
        for v in self.dest_list_views:
            v.setHidden_(False)
        for v in self.dest_detail_views:
            v.setHidden_(True)

    @objc.python_method
    def show_dest_detail(self, remote):
        self._dest_detail_current = remote
        self.dest_title.setStringValue_(remote)
        self.dest_back_btn.setHidden_(False)
        for v in self.dest_list_views:
            v.setHidden_(True)
        for v in self.dest_detail_views:
            v.setHidden_(False)
        self._populate_dest_detail(remote)

    @objc.python_method
    def _populate_dest_detail(self, remote):
        start, end = _period_range(self._dest_period)
        t_in, t_out = data_tracker.remote_total(remote, start, end)
        total = (t_in or 0) + (t_out or 0)
        self.dest_d_total.setStringValue_(fmt_bytes(total))
        self.dest_d_in.setStringValue_(fmt_bytes(t_in or 0))
        self.dest_d_out.setStringValue_(fmt_bytes(t_out or 0))

        # Geo info row
        meta = data_tracker.get_remote_meta([remote])
        m = meta.get(remote, {})
        host = m.get("hostname") or "—"
        cc = (m.get("country_code") or "").upper()
        country = m.get("country") or ""
        city = m.get("city") or ""
        isp = m.get("isp") or ""
        parts = []
        if host and host != "—":
            parts.append(f"{t('dash.col.host')}: {host}")
        if cc:
            parts.append(f"{t('dash.col.country')}: {country} [{cc}]")
        if city:
            parts.append(f"City: {city}")
        if isp:
            parts.append(f"ISP: {isp}")
        self.dest_d_info.setStringValue_("  ·  ".join(parts) if parts else "")

        # Apps for this remote
        for sub in list(self.dest_d_rows_view.subviews()):
            sub.removeFromSuperview()

        apps = data_tracker.top_apps_for_remote(remote, start, end, limit=100)
        row_h = 26
        total_h = max(40, len(apps) * row_h + 12)
        w = self.dest_d_rows_view.frame().size.width
        self.dest_d_rows_view.setFrameSize_(NSMakeSize(w, total_h))

        for i, (app, atotal, b_in, b_out) in enumerate(apps):
            y = total_h - (i + 1) * row_h
            container = NSView.alloc().initWithFrame_(NSMakeRect(0, y, w, row_h))
            container.addSubview_(_position(_mono_label(app[:48], width=360), 0, 4, 360, 18))
            container.addSubview_(_position(_mono_label(fmt_bytes(atotal), width=120,
                                                        color=FG_AMBER()), 360, 4, 120, 18))
            container.addSubview_(_position(_mono_label(fmt_bytes(b_in), width=120,
                                                        color=FG_TEAL()), 480, 4, 120, 18))
            container.addSubview_(_position(_mono_label(fmt_bytes(b_out), width=120,
                                                        color=FG_PINK()), 600, 4, 120, 18))
            self.dest_d_rows_view.addSubview_(container)

    def openReportByTag_(self, sender):
        tag = int(sender.tag())
        if 0 <= tag < len(self._report_periods):
            try:
                data_report.open_report(self._report_periods[tag])
            except Exception as e:
                print(f"report open error: {e}", flush=True)

    def doExport_(self, _):
        period = _period_from_label(str(self.exp_period.titleOfSelectedItem()))
        fmt = str(self.exp_format.titleOfSelectedItem()).lower()
        try:
            path, n = data_export.export(period, fmt)
            self.exp_status.setStringValue_(t("dash.export.success", n=n, path=path))
        except Exception as e:
            self.exp_status.setStringValue_(t("dash.export.error", e=e))

    def languageChanged_(self, sender):
        title = str(sender.titleOfSelectedItem())
        for code, name in LANG_NAMES.items():
            if name == title:
                i18n.set_lang(code)
                break

    def quitApp_(self, _):
        NSApp.terminate_(None)

    def resetToday_(self, _):
        state_file = os.path.expanduser("~/.data_monitor_state.json")
        try:
            with open(state_file) as f:
                s = json.load(f)
        except Exception:
            s = {}
        s["recv"] = 0
        s["sent"] = 0
        s["date"] = date.today().isoformat()
        with open(state_file, "w") as f:
            json.dump(s, f)
        self.refresh_data()

    def windowWillClose_(self, _):
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None


# Keep references so windows don't GC
_open_windows = []


def open_dashboard():
    win = DashboardWindow.alloc().init()
    _open_windows.append(win)
    return win
