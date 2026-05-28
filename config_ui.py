"""Native AppKit windows for editing networks & quotas.
Runs in the same process as the rumps daemon (shared AppKit run loop).
"""
import json
import os
import sys

import objc
from Foundation import NSObject, NSMakeRect, NSMakeSize, NSPoint
from AppKit import (
    NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered, NSTextField, NSButton, NSPopUpButton,
    NSView, NSScrollView, NSStackView, NSUserInterfaceLayoutOrientationVertical,
    NSUserInterfaceLayoutOrientationHorizontal, NSStackViewDistributionFill,
    NSColor, NSFont, NSApp, NSBezelStyleRegularSquare, NSBezelStyleRounded,
    NSLayoutAttributeWidth, NSLayoutAttributeHeight,
    NSAlert, NSAlertStyleWarning, NSImageView, NSImage,
    NSStackViewGravityTop, NSStackViewGravityBottom,
    NSStackViewGravityLeading, NSStackViewGravityTrailing,
    NSLayoutConstraint, NSLayoutAttributeLeading, NSLayoutAttributeTrailing,
    NSLayoutRelationEqual, NSWindowController, NSWindowTitleVisible,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_tracker
import quotas as quotas_mod

NETWORK_FILE = os.path.expanduser("~/.data_monitor_networks.json")

UNITS = [("KB", 1024), ("MB", 1024 ** 2), ("GB", 1024 ** 3), ("TB", 1024 ** 4)]
UNIT_BY_NAME = dict(UNITS)
PERIODS_APP = ["daily", "weekly", "monthly"]
PERIODS_NET = ["daily", "monthly"]


def bytes_to_unit(n):
    if not n:
        return ("", "MB")
    for name, factor in reversed(UNITS):
        if n >= factor:
            v = n / factor
            return (f"{v:g}" if v == int(v) else f"{v:.2f}", name)
    return (f"{n}", "KB")


def to_bytes(num_str, unit_name):
    try:
        return int(float(num_str) * UNIT_BY_NAME.get(unit_name, 1024 ** 2))
    except (TypeError, ValueError):
        return None


def _label(text, bold=False, color=None, size=12):
    f = NSTextField.alloc().init()
    f.setStringValue_(text)
    f.setBezeled_(False)
    f.setDrawsBackground_(False)
    f.setEditable_(False)
    f.setSelectable_(False)
    font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
    f.setFont_(font)
    if color:
        f.setTextColor_(color)
    f.sizeToFit()
    return f


def _entry(value="", width=140, mono=False):
    f = NSTextField.alloc().init()
    f.setStringValue_(value)
    f.setFrameSize_(NSMakeSize(width, 22))
    if mono:
        f.setFont_(NSFont.userFixedPitchFontOfSize_(12))
    return f


def _popup(items, selected=None, width=110):
    p = NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(0, 0, width, 24), False)
    p.addItemsWithTitles_(items)
    if selected and selected in items:
        p.selectItemWithTitle_(selected)
    return p


def _button(title, target, action, bezel=True):
    b = NSButton.alloc().init()
    b.setTitle_(title)
    b.setTarget_(target)
    b.setAction_(action)
    if not bezel:
        b.setBordered_(False)
    b.sizeToFit()
    return b


def _h(views, spacing=8):
    s = NSStackView.alloc().init()
    s.setOrientation_(NSUserInterfaceLayoutOrientationHorizontal)
    s.setSpacing_(spacing)
    for v in views:
        s.addArrangedSubview_(v)
    return s


def _v(views, spacing=8):
    s = NSStackView.alloc().init()
    s.setOrientation_(NSUserInterfaceLayoutOrientationVertical)
    s.setSpacing_(spacing)
    s.setAlignment_(1)  # NSLayoutAttributeLeading = 1
    for v in views:
        s.addArrangedSubview_(v)
    return s


def _alert(message):
    alert = NSAlert.alloc().init()
    alert.setMessageText_("Hata")
    alert.setInformativeText_(message)
    alert.setAlertStyle_(NSAlertStyleWarning)
    alert.runModal()


# ============================================================
# Network Editor Window
# ============================================================

class NetworkEditor(NSObject):

    def init(self):
        self = objc.super(NetworkEditor, self).init()
        if self is None:
            return None
        self.rows = []  # list of (ip_field, name_field, container)
        self.build()
        return self

    @objc.python_method
    def build(self):
        try:
            with open(NETWORK_FILE) as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

        try:
            current = data_tracker.get_current_network()
        except Exception:
            current = ""

        rect = NSMakeRect(200, 400, 540, 460)
        mask = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
                | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        self.window = (NSWindow.alloc()
                       .initWithContentRect_styleMask_backing_defer_(rect, mask, NSBackingStoreBuffered, False))
        self.window.setTitle_("Ağ İsimleri")
        self.window.setReleasedWhenClosed_(False)

        content = self.window.contentView()

        # Title + subtitle
        title = _label("Ağ İsimleri", bold=True, size=18)
        title.setFrame_(NSMakeRect(20, 410, 400, 28))
        content.addSubview_(title)

        subtitle = _label("Gateway IP → görünür ad eşlemesi",
                          color=NSColor.secondaryLabelColor(), size=12)
        subtitle.setFrame_(NSMakeRect(20, 390, 500, 18))
        content.addSubview_(subtitle)

        if current:
            cur = _label(f"Şu an bağlı: {current}",
                         color=NSColor.systemGreenColor(), size=11)
            cur.setFrame_(NSMakeRect(20, 368, 500, 18))
            content.addSubview_(cur)

        # Column headers
        hdr_ip = _label("Gateway IP", bold=True, size=11,
                        color=NSColor.secondaryLabelColor())
        hdr_ip.setFrame_(NSMakeRect(20, 340, 200, 16))
        content.addSubview_(hdr_ip)

        hdr_name = _label("Görünür Ad", bold=True, size=11,
                          color=NSColor.secondaryLabelColor())
        hdr_name.setFrame_(NSMakeRect(230, 340, 200, 16))
        content.addSubview_(hdr_name)

        # Scrollable rows area
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 70, 500, 260))
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(1)  # bezel
        self.rows_container = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 480, 260))
        scroll.setDocumentView_(self.rows_container)
        content.addSubview_(scroll)

        # Populate existing
        for ip, name in cfg.items():
            self.add_row_for(ip, name)
        if not cfg and current and "(" in current:
            ip_part = current.split("(")[-1].rstrip(")")
            if ip_part.replace(".", "").isdigit():
                self.add_row_for(ip_part, "")
        if not self.rows:
            self.add_row_for("", "")

        # Bottom buttons
        add_btn = _button("+ Satır Ekle", self, b"addRow:")
        add_btn.setFrame_(NSMakeRect(20, 25, 130, 28))
        content.addSubview_(add_btn)

        cancel_btn = _button("İptal", self, b"cancel:")
        cancel_btn.setFrame_(NSMakeRect(360, 25, 80, 28))
        content.addSubview_(cancel_btn)

        save_btn = _button("Kaydet", self, b"save:")
        save_btn.setFrame_(NSMakeRect(445, 25, 80, 28))
        save_btn.setKeyEquivalent_("\r")  # default button
        content.addSubview_(save_btn)

        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    @objc.python_method
    def add_row_for(self, ip="", name=""):
        y = len(self.rows) * 32
        row = NSView.alloc().initWithFrame_(NSMakeRect(0, y, 480, 28))

        ip_field = _entry(ip, width=200, mono=True)
        ip_field.setFrame_(NSMakeRect(0, 2, 200, 24))
        row.addSubview_(ip_field)

        name_field = _entry(name, width=200, mono=True)
        name_field.setFrame_(NSMakeRect(210, 2, 200, 24))
        row.addSubview_(name_field)

        remove_btn = _button("×", self, b"removeRow:")
        remove_btn.setFrame_(NSMakeRect(420, 2, 30, 24))
        remove_btn.setTag_(len(self.rows))
        row.addSubview_(remove_btn)

        self.rows_container.addSubview_(row)
        self.rows.append((ip_field, name_field, row))
        self.reflow_rows()

    @objc.python_method
    def reflow_rows(self):
        h = max(260, len(self.rows) * 32 + 8)
        self.rows_container.setFrameSize_(NSMakeSize(480, h))
        for i, (_, _, row) in enumerate(self.rows):
            row.setFrame_(NSMakeRect(0, h - (i + 1) * 32, 480, 28))

    def addRow_(self, sender):
        self.add_row_for("", "")

    def removeRow_(self, sender):
        for i, (_, _, row) in enumerate(self.rows):
            if sender in row.subviews():
                row.removeFromSuperview()
                self.rows.pop(i)
                self.reflow_rows()
                return

    def cancel_(self, sender):
        self.window.close()

    def save_(self, sender):
        data = {}
        for ip_field, name_field, _ in self.rows:
            ip = str(ip_field.stringValue()).strip()
            name = str(name_field.stringValue()).strip()
            if ip and name:
                data[ip] = name
        try:
            with open(NETWORK_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.window.close()
        except Exception as e:
            _alert(f"Kaydedilemedi: {e}")


# ============================================================
# Quota Editor Window
# ============================================================

class QuotaEditor(NSObject):

    def init(self):
        self = objc.super(QuotaEditor, self).init()
        if self is None:
            return None
        self.app_rows = []
        self.net_rows = []
        self.build()
        return self

    @objc.python_method
    def build(self):
        cfg = quotas_mod.load_quotas()

        rect = NSMakeRect(200, 200, 720, 660)
        mask = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
                | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        self.window = (NSWindow.alloc()
                       .initWithContentRect_styleMask_backing_defer_(rect, mask, NSBackingStoreBuffered, False))
        self.window.setTitle_("Veri Kotaları")
        self.window.setReleasedWhenClosed_(False)
        content = self.window.contentView()

        # Header
        title = _label("Veri Kotaları", bold=True, size=18)
        title.setFrame_(NSMakeRect(20, 610, 400, 28))
        content.addSubview_(title)

        subtitle = _label("Limit aşılınca bildirim ve menü çubuğu uyarısı gelir",
                          color=NSColor.secondaryLabelColor(), size=12)
        subtitle.setFrame_(NSMakeRect(20, 590, 500, 18))
        content.addSubview_(subtitle)

        # ---- Totals section ----
        sec_y = 510
        sec_label = _label("TOPLAM LİMİTLER", bold=True, size=11,
                           color=NSColor.secondaryLabelColor())
        sec_label.setFrame_(NSMakeRect(20, sec_y + 60, 200, 16))
        content.addSubview_(sec_label)

        d_val, d_unit = bytes_to_unit(cfg.get("daily_total"))
        m_val, m_unit = bytes_to_unit(cfg.get("monthly_total"))

        # Daily row
        d_lbl = _label("Günlük Toplam:", size=12)
        d_lbl.setFrame_(NSMakeRect(20, sec_y + 32, 130, 22))
        content.addSubview_(d_lbl)

        self.daily_field = _entry(d_val, width=90, mono=True)
        self.daily_field.setFrame_(NSMakeRect(155, sec_y + 30, 90, 24))
        content.addSubview_(self.daily_field)

        self.daily_unit = _popup([u[0] for u in UNITS], d_unit, width=80)
        self.daily_unit.setFrame_(NSMakeRect(250, sec_y + 28, 80, 26))
        content.addSubview_(self.daily_unit)

        d_hint = _label("(boş = limitsiz)",
                        color=NSColor.tertiaryLabelColor(), size=11)
        d_hint.setFrame_(NSMakeRect(340, sec_y + 32, 200, 18))
        content.addSubview_(d_hint)

        # Monthly row
        m_lbl = _label("Aylık Toplam:", size=12)
        m_lbl.setFrame_(NSMakeRect(20, sec_y, 130, 22))
        content.addSubview_(m_lbl)

        self.monthly_field = _entry(m_val, width=90, mono=True)
        self.monthly_field.setFrame_(NSMakeRect(155, sec_y - 2, 90, 24))
        content.addSubview_(self.monthly_field)

        self.monthly_unit = _popup([u[0] for u in UNITS], m_unit, width=80)
        self.monthly_unit.setFrame_(NSMakeRect(250, sec_y - 4, 80, 26))
        content.addSubview_(self.monthly_unit)

        m_hint = _label("(boş = limitsiz)",
                        color=NSColor.tertiaryLabelColor(), size=11)
        m_hint.setFrame_(NSMakeRect(340, sec_y, 200, 18))
        content.addSubview_(m_hint)

        # ---- Per-app section ----
        app_top = 470
        app_label = _label("UYGULAMA BAZLI", bold=True, size=11,
                           color=NSColor.secondaryLabelColor())
        app_label.setFrame_(NSMakeRect(20, app_top, 200, 16))
        content.addSubview_(app_label)

        # Column headers
        ah_app = _label("Uygulama", bold=True, size=10, color=NSColor.tertiaryLabelColor())
        ah_app.setFrame_(NSMakeRect(20, app_top - 22, 200, 14))
        content.addSubview_(ah_app)
        ah_per = _label("Dönem", bold=True, size=10, color=NSColor.tertiaryLabelColor())
        ah_per.setFrame_(NSMakeRect(240, app_top - 22, 100, 14))
        content.addSubview_(ah_per)
        ah_lim = _label("Limit", bold=True, size=10, color=NSColor.tertiaryLabelColor())
        ah_lim.setFrame_(NSMakeRect(360, app_top - 22, 100, 14))
        content.addSubview_(ah_lim)

        app_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 295, 680, 140))
        app_scroll.setHasVerticalScroller_(True)
        app_scroll.setBorderType_(1)
        self.app_rows_container = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 660, 140))
        app_scroll.setDocumentView_(self.app_rows_container)
        content.addSubview_(app_scroll)

        for name, cfg_a in (cfg.get("apps") or {}).items():
            self.add_app_row_for(name, cfg_a.get("period", "daily"), cfg_a.get("limit"))

        add_app = _button("+ Uygulama Ekle", self, b"addApp:")
        add_app.setFrame_(NSMakeRect(20, 265, 150, 24))
        content.addSubview_(add_app)

        # ---- Per-network section ----
        net_top = 235
        net_label = _label("AĞ BAZLI", bold=True, size=11,
                           color=NSColor.secondaryLabelColor())
        net_label.setFrame_(NSMakeRect(20, net_top, 200, 16))
        content.addSubview_(net_label)

        nh_net = _label("Ağ", bold=True, size=10, color=NSColor.tertiaryLabelColor())
        nh_net.setFrame_(NSMakeRect(20, net_top - 22, 200, 14))
        content.addSubview_(nh_net)
        nh_per = _label("Dönem", bold=True, size=10, color=NSColor.tertiaryLabelColor())
        nh_per.setFrame_(NSMakeRect(240, net_top - 22, 100, 14))
        content.addSubview_(nh_per)
        nh_lim = _label("Limit", bold=True, size=10, color=NSColor.tertiaryLabelColor())
        nh_lim.setFrame_(NSMakeRect(360, net_top - 22, 100, 14))
        content.addSubview_(nh_lim)

        net_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 60, 680, 140))
        net_scroll.setHasVerticalScroller_(True)
        net_scroll.setBorderType_(1)
        self.net_rows_container = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 660, 140))
        net_scroll.setDocumentView_(self.net_rows_container)
        content.addSubview_(net_scroll)

        for name, cfg_n in (cfg.get("networks") or {}).items():
            self.add_net_row_for(name, cfg_n.get("period", "daily"), cfg_n.get("limit"))

        add_net = _button("+ Ağ Ekle", self, b"addNet:")
        add_net.setFrame_(NSMakeRect(20, 30, 150, 24))
        content.addSubview_(add_net)

        # ---- Bottom buttons ----
        cancel_btn = _button("İptal", self, b"cancel:")
        cancel_btn.setFrame_(NSMakeRect(530, 18, 80, 28))
        content.addSubview_(cancel_btn)

        save_btn = _button("Kaydet", self, b"save:")
        save_btn.setFrame_(NSMakeRect(615, 18, 85, 28))
        save_btn.setKeyEquivalent_("\r")
        content.addSubview_(save_btn)

        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    @objc.python_method
    def add_quota_row(self, container_view, registry, periods, name, period, limit):
        y = len(registry) * 32
        row = NSView.alloc().initWithFrame_(NSMakeRect(0, y, 660, 28))

        name_field = _entry(name, width=200, mono=True)
        name_field.setFrame_(NSMakeRect(0, 2, 215, 24))
        row.addSubview_(name_field)

        period_popup = _popup(periods, period or periods[0], width=100)
        period_popup.setFrame_(NSMakeRect(225, 0, 100, 26))
        row.addSubview_(period_popup)

        val_str, unit_name = bytes_to_unit(limit)
        val_field = _entry(val_str, width=80, mono=True)
        val_field.setFrame_(NSMakeRect(345, 2, 80, 24))
        row.addSubview_(val_field)

        unit_popup = _popup([u[0] for u in UNITS], unit_name, width=70)
        unit_popup.setFrame_(NSMakeRect(430, 0, 70, 26))
        row.addSubview_(unit_popup)

        # Remove button (action depends on which list)
        if registry is self.app_rows:
            sel = b"removeApp:"
        else:
            sel = b"removeNet:"
        remove_btn = _button("×", self, sel)
        remove_btn.setFrame_(NSMakeRect(510, 2, 30, 24))
        row.addSubview_(remove_btn)

        container_view.addSubview_(row)
        registry.append({"name": name_field, "period": period_popup,
                         "val": val_field, "unit": unit_popup, "row": row})
        self.reflow(container_view, registry)

    @objc.python_method
    def reflow(self, container_view, registry):
        h = max(140, len(registry) * 32 + 8)
        container_view.setFrameSize_(NSMakeSize(660, h))
        for i, r in enumerate(registry):
            r["row"].setFrame_(NSMakeRect(0, h - (i + 1) * 32, 660, 28))

    @objc.python_method
    def add_app_row_for(self, name, period, limit):
        self.add_quota_row(self.app_rows_container, self.app_rows, PERIODS_APP, name, period, limit)

    @objc.python_method
    def add_net_row_for(self, name, period, limit):
        self.add_quota_row(self.net_rows_container, self.net_rows, PERIODS_NET, name, period, limit)

    def addApp_(self, sender):
        self.add_app_row_for("", "daily", None)

    def addNet_(self, sender):
        self.add_net_row_for("", "daily", None)

    @objc.python_method
    def remove_from(self, registry, container, sender):
        for i, r in enumerate(registry):
            if sender in r["row"].subviews():
                r["row"].removeFromSuperview()
                registry.pop(i)
                self.reflow(container, registry)
                return

    def removeApp_(self, sender):
        self.remove_from(self.app_rows, self.app_rows_container, sender)

    def removeNet_(self, sender):
        self.remove_from(self.net_rows, self.net_rows_container, sender)

    def cancel_(self, sender):
        self.window.close()

    def save_(self, sender):
        cfg = quotas_mod.load_quotas()

        cfg["daily_total"] = to_bytes(self.daily_field.stringValue(),
                                      self.daily_unit.titleOfSelectedItem())
        cfg["monthly_total"] = to_bytes(self.monthly_field.stringValue(),
                                        self.monthly_unit.titleOfSelectedItem())

        apps = {}
        for r in self.app_rows:
            n = str(r["name"].stringValue()).strip()
            limit = to_bytes(r["val"].stringValue(), r["unit"].titleOfSelectedItem())
            if n and limit:
                apps[n] = {"period": str(r["period"].titleOfSelectedItem()), "limit": limit}
        cfg["apps"] = apps

        nets = {}
        for r in self.net_rows:
            n = str(r["name"].stringValue()).strip()
            limit = to_bytes(r["val"].stringValue(), r["unit"].titleOfSelectedItem())
            if n and limit:
                nets[n] = {"period": str(r["period"].titleOfSelectedItem()), "limit": limit}
        cfg["networks"] = nets

        try:
            quotas_mod.save_quotas(cfg)
            self.window.close()
        except Exception as e:
            _alert(f"Kaydedilemedi: {e}")


# Keep references so windows don't get GC'd
_open_windows = []


def open_networks():
    ed = NetworkEditor.alloc().init()
    _open_windows.append(ed)
    return ed


def open_quotas():
    ed = QuotaEditor.alloc().init()
    _open_windows.append(ed)
    return ed
