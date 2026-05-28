"""Localization for 1 Bit Data — 6 languages."""
import json
import os

SETTINGS_FILE = os.path.expanduser("~/.data_monitor_settings.json")
DEFAULT_LANG = "en"
SUPPORTED = ["tr", "en", "es", "ja", "zh", "hi"]

LANG_NAMES = {
    "tr": "Türkçe",
    "en": "English",
    "es": "Español",
    "ja": "日本語",
    "zh": "简体中文",
    "hi": "हिन्दी",
}

T = {
    # ----- MENU -----
    "menu.live_speed": {
        "tr": "ANLIK HIZ", "en": "LIVE SPEED", "es": "VELOCIDAD",
        "ja": "現在の速度", "zh": "实时速度", "hi": "वर्तमान गति",
    },
    "menu.today": {
        "tr": "BUGÜN", "en": "TODAY", "es": "HOY",
        "ja": "今日", "zh": "今天", "hi": "आज",
    },
    "menu.top_apps": {
        "tr": "EN ÇOK KULLANANLAR", "en": "TOP APPS", "es": "APPS PRINCIPALES",
        "ja": "上位アプリ", "zh": "顶级应用", "hi": "शीर्ष ऐप्स",
    },
    "menu.reports": {
        "tr": "Raporlar", "en": "Reports", "es": "Informes",
        "ja": "レポート", "zh": "报告", "hi": "रिपोर्ट",
    },
    "menu.settings": {
        "tr": "Ayarlar", "en": "Settings", "es": "Ajustes",
        "ja": "設定", "zh": "设置", "hi": "सेटिंग्स",
    },
    "menu.language": {
        "tr": "Dil", "en": "Language", "es": "Idioma",
        "ja": "言語", "zh": "语言", "hi": "भाषा",
    },
    "menu.report.daily": {
        "tr": "Günlük Rapor", "en": "Daily Report", "es": "Informe Diario",
        "ja": "日次レポート", "zh": "每日报告", "hi": "दैनिक रिपोर्ट",
    },
    "menu.report.monthly": {
        "tr": "Aylık Rapor", "en": "Monthly Report", "es": "Informe Mensual",
        "ja": "月次レポート", "zh": "月度报告", "hi": "मासिक रिपोर्ट",
    },
    "menu.report.yearly": {
        "tr": "Yıllık Rapor", "en": "Yearly Report", "es": "Informe Anual",
        "ja": "年次レポート", "zh": "年度报告", "hi": "वार्षिक रिपोर्ट",
    },
    "menu.report.last30": {
        "tr": "Son 30 Gün", "en": "Last 30 Days", "es": "Últimos 30 Días",
        "ja": "過去30日間", "zh": "最近30天", "hi": "पिछले 30 दिन",
    },
    "menu.reset_today": {
        "tr": "Günlük Sayacı Sıfırla", "en": "Reset Today's Counter", "es": "Reiniciar Contador del Día",
        "ja": "今日のカウンターをリセット", "zh": "重置今日计数", "hi": "आज का काउंटर रीसेट करें",
    },
    "menu.edit_networks": {
        "tr": "Ağ İsimlerini Düzenle", "en": "Edit Network Names", "es": "Editar Nombres de Red",
        "ja": "ネットワーク名を編集", "zh": "编辑网络名称", "hi": "नेटवर्क नाम संपादित करें",
    },
    "menu.quit": {
        "tr": "Çıkış", "en": "Quit", "es": "Salir",
        "ja": "終了", "zh": "退出", "hi": "बंद करें",
    },
    "menu.dashboard": {
        "tr": "Panel…", "en": "Dashboard…", "es": "Panel…",
        "ja": "ダッシュボード…", "zh": "仪表板…", "hi": "डैशबोर्ड…",
    },
    "menu.pause": {
        "tr": "Takibi Duraklat", "en": "Pause Tracking", "es": "Pausar Seguimiento",
        "ja": "トラッキング一時停止", "zh": "暂停跟踪", "hi": "ट्रैकिंग रोकें",
    },
    "menu.resume": {
        "tr": "Takibi Sürdür", "en": "Resume Tracking", "es": "Reanudar Seguimiento",
        "ja": "トラッキング再開", "zh": "恢复跟踪", "hi": "ट्रैकिंग जारी रखें",
    },
    "menu.cleanup": {
        "tr": "Eski Verileri Sil…", "en": "Delete Old Data…", "es": "Eliminar Datos Antiguos…",
        "ja": "古いデータを削除…", "zh": "删除旧数据…", "hi": "पुराना डेटा हटाएं…",
    },
    "cleanup.title": {
        "tr": "Eski Verileri Sil",
        "en": "Delete Old Data",
        "es": "Eliminar Datos Antiguos",
        "ja": "古いデータを削除",
        "zh": "删除旧数据",
        "hi": "पुराना डेटा हटाएं",
    },
    "cleanup.message": {
        "tr": "Kaç günden eski veriler silinsin?",
        "en": "Delete data older than how many days?",
        "es": "¿Eliminar datos anteriores a cuántos días?",
        "ja": "何日より古いデータを削除しますか？",
        "zh": "删除多少天前的数据？",
        "hi": "कितने दिनों से पुराना डेटा हटाएं?",
    },
    "cleanup.done": {
        "tr": "{n} satır silindi",
        "en": "{n} rows deleted",
        "es": "{n} filas eliminadas",
        "ja": "{n} 行を削除しました",
        "zh": "已删除 {n} 行",
        "hi": "{n} पंक्तियाँ हटाई गईं",
    },
    "menu.export": {
        "tr": "Dışa Aktar", "en": "Export", "es": "Exportar",
        "ja": "エクスポート", "zh": "导出", "hi": "निर्यात",
    },
    "menu.export.today": {
        "tr": "Bugün", "en": "Today", "es": "Hoy",
        "ja": "今日", "zh": "今天", "hi": "आज",
    },
    "menu.export.month": {
        "tr": "Bu Ay", "en": "This Month", "es": "Este Mes",
        "ja": "今月", "zh": "本月", "hi": "इस माह",
    },
    "menu.export.year": {
        "tr": "Bu Yıl", "en": "This Year", "es": "Este Año",
        "ja": "今年", "zh": "今年", "hi": "इस वर्ष",
    },
    "menu.export.all": {
        "tr": "Tümü", "en": "All Time", "es": "Todo",
        "ja": "全期間", "zh": "全部", "hi": "सभी",
    },
    "menu.edit_quotas": {
        "tr": "Kotaları Düzenle", "en": "Edit Quotas", "es": "Editar Cuotas",
        "ja": "クォータを編集", "zh": "编辑配额", "hi": "कोटा संपादित करें",
    },
    "notify.quota.title": {
        "tr": "Veri Kotası Aşıldı", "en": "Data Quota Exceeded", "es": "Cuota de Datos Superada",
        "ja": "データクォータを超過しました", "zh": "数据配额已超出", "hi": "डेटा कोटा पार हो गया",
    },
    "notify.quota.message": {
        "tr": "{label}: {used} / {limit} ({pct}%)",
        "en": "{label}: {used} / {limit} ({pct}%)",
        "es": "{label}: {used} / {limit} ({pct}%)",
        "ja": "{label}: {used} / {limit} ({pct}%)",
        "zh": "{label}: {used} / {limit} ({pct}%)",
        "hi": "{label}: {used} / {limit} ({pct}%)",
    },
    "notify.export.done": {
        "tr": "Dışa aktarıldı: {n} satır", "en": "Exported: {n} rows", "es": "Exportado: {n} filas",
        "ja": "エクスポート完了: {n} 行", "zh": "已导出: {n} 行", "hi": "निर्यात: {n} पंक्तियाँ",
    },

    # ----- DASHBOARD TABS -----
    "dash.tab.overview": {
        "tr": "ÖZET", "en": "OVERVIEW", "es": "RESUMEN",
        "ja": "概要", "zh": "概览", "hi": "अवलोकन",
    },
    "dash.tab.apps": {
        "tr": "UYGULAMALAR", "en": "APPS", "es": "APPS",
        "ja": "アプリ", "zh": "应用", "hi": "ऐप्स",
    },
    "dash.tab.destinations": {
        "tr": "HEDEFLER", "en": "DESTINATIONS", "es": "DESTINOS",
        "ja": "接続先", "zh": "目标", "hi": "गंतव्य",
    },
    "dash.tab.quotas": {
        "tr": "KOTALAR", "en": "QUOTAS", "es": "CUOTAS",
        "ja": "クォータ", "zh": "配额", "hi": "कोटा",
    },
    "dash.tab.networks": {
        "tr": "AĞLAR", "en": "NETWORKS", "es": "REDES",
        "ja": "ネットワーク", "zh": "网络", "hi": "नेटवर्क",
    },
    "dash.tab.reports": {
        "tr": "RAPORLAR", "en": "REPORTS", "es": "INFORMES",
        "ja": "レポート", "zh": "报告", "hi": "रिपोर्ट",
    },
    "dash.tab.export": {
        "tr": "DIŞA AKTAR", "en": "EXPORT", "es": "EXPORTAR",
        "ja": "エクスポート", "zh": "导出", "hi": "निर्यात",
    },
    "dash.tab.settings": {
        "tr": "AYARLAR", "en": "SETTINGS", "es": "AJUSTES",
        "ja": "設定", "zh": "设置", "hi": "सेटिंग्स",
    },

    # ----- DASHBOARD: OVERVIEW -----
    "dash.live_status": {
        "tr": "Anlık Durum", "en": "Live Status", "es": "Estado en Vivo",
        "ja": "現在の状況", "zh": "实时状态", "hi": "लाइव स्थिति",
    },
    "dash.network": {
        "tr": "Ağ", "en": "Network", "es": "Red",
        "ja": "ネットワーク", "zh": "网络", "hi": "नेटवर्क",
    },
    "dash.today_total": {
        "tr": "BUGÜN TOPLAM", "en": "TODAY TOTAL", "es": "HOY TOTAL",
        "ja": "今日の合計", "zh": "今日总计", "hi": "आज कुल",
    },
    "dash.live_speed": {
        "tr": "ANLIK HIZ", "en": "LIVE SPEED", "es": "VELOCIDAD",
        "ja": "現在の速度", "zh": "实时速度", "hi": "वर्तमान गति",
    },
    "dash.today_detail": {
        "tr": "BUGÜN DETAY", "en": "TODAY BREAKDOWN", "es": "DETALLE DE HOY",
        "ja": "今日の詳細", "zh": "今日明细", "hi": "आज विवरण",
    },
    "dash.downloaded": {
        "tr": "↓ İndirilen: {v}", "en": "↓ Downloaded: {v}", "es": "↓ Descargado: {v}",
        "ja": "↓ ダウンロード: {v}", "zh": "↓ 已下载: {v}", "hi": "↓ डाउनलोड: {v}",
    },
    "dash.uploaded": {
        "tr": "↑ Yüklenen: {v}", "en": "↑ Uploaded: {v}", "es": "↑ Subido: {v}",
        "ja": "↑ アップロード: {v}", "zh": "↑ 已上传: {v}", "hi": "↑ अपलोड: {v}",
    },
    "dash.auto_refresh_hint": {
        "tr": "Sol panel her 2 saniyede güncellenir",
        "en": "Left panel refreshes every 2 seconds",
        "es": "El panel izquierdo se actualiza cada 2 segundos",
        "ja": "左パネルは2秒ごとに更新されます",
        "zh": "左侧面板每 2 秒刷新一次",
        "hi": "बायाँ पैनल हर 2 सेकंड में रीफ्रेश होता है",
    },

    # ----- SPEED TEST -----
    "dash.speedtest.title": {
        "tr": "HIZ TESTİ", "en": "SPEED TEST", "es": "PRUEBA DE VELOCIDAD",
        "ja": "速度テスト", "zh": "速度测试", "hi": "स्पीड टेस्ट",
    },
    "dash.speedtest.start": {
        "tr": "Testi Başlat", "en": "Start Test", "es": "Iniciar Prueba",
        "ja": "テスト開始", "zh": "开始测试", "hi": "टेस्ट शुरू",
    },
    "dash.speedtest.stop": {
        "tr": "Testi Durdur", "en": "Stop Test", "es": "Detener Prueba",
        "ja": "テスト停止", "zh": "停止测试", "hi": "टेस्ट रोकें",
    },
    "dash.speedtest.running": {
        "tr": "Test çalışıyor (≈ 15-20 sn)…",
        "en": "Test running (≈ 15-20 s)…",
        "es": "Prueba en curso (≈ 15-20 s)…",
        "ja": "テスト実行中 (約 15-20 秒)…",
        "zh": "测试运行中 (约 15-20 秒)…",
        "hi": "टेस्ट चल रहा है (≈ 15-20 सेकंड)…",
    },
    "dash.speedtest.stopping": {
        "tr": "Durduruluyor…", "en": "Stopping…", "es": "Deteniendo…",
        "ja": "停止中…", "zh": "停止中…", "hi": "रोक रहा है…",
    },
    "dash.speedtest.done": {
        "tr": "Bitti · {time}", "en": "Done · {time}", "es": "Hecho · {time}",
        "ja": "完了 · {time}", "zh": "完成 · {time}", "hi": "हो गया · {time}",
    },
    "dash.speedtest.cancelled": {
        "tr": "İptal edildi", "en": "Cancelled", "es": "Cancelado",
        "ja": "キャンセル", "zh": "已取消", "hi": "रद्द किया गया",
    },
    "dash.speedtest.failed": {
        "tr": "Test başarısız oldu", "en": "Test failed", "es": "Prueba fallida",
        "ja": "テスト失敗", "zh": "测试失败", "hi": "टेस्ट विफल",
    },
    "dash.speedtest.not_found": {
        "tr": "networkQuality bulunamadı",
        "en": "networkQuality not found",
        "es": "networkQuality no encontrado",
        "ja": "networkQuality が見つかりません",
        "zh": "未找到 networkQuality",
        "hi": "networkQuality नहीं मिला",
    },
    "dash.speedtest.dl": {
        "tr": "İndirme", "en": "Download", "es": "Descarga",
        "ja": "ダウンロード", "zh": "下载", "hi": "डाउनलोड",
    },
    "dash.speedtest.ul": {
        "tr": "Yükleme", "en": "Upload", "es": "Subida",
        "ja": "アップロード", "zh": "上传", "hi": "अपलोड",
    },
    "dash.speedtest.latency": {
        "tr": "Gecikme (RTT)", "en": "Latency (RTT)", "es": "Latencia (RTT)",
        "ja": "遅延 (RTT)", "zh": "延迟 (RTT)", "hi": "लेटेंसी (RTT)",
    },
    "dash.speedtest.history": {
        "tr": "GEÇMİŞ", "en": "HISTORY", "es": "HISTORIAL",
        "ja": "履歴", "zh": "历史", "hi": "इतिहास",
    },
    "dash.speedtest.no_history": {
        "tr": "Henüz test yok", "en": "No tests yet", "es": "Sin pruebas aún",
        "ja": "まだテストなし", "zh": "暂无测试", "hi": "अभी कोई टेस्ट नहीं",
    },

    # ----- DASHBOARD common -----
    "dash.period": {
        "tr": "Dönem", "en": "Period", "es": "Período",
        "ja": "期間", "zh": "时段", "hi": "अवधि",
    },
    "dash.search.app": {
        "tr": "Uygulama ara…", "en": "Search apps…", "es": "Buscar apps…",
        "ja": "アプリを検索…", "zh": "搜索应用…", "hi": "ऐप खोजें…",
    },
    "dash.search.dest": {
        "tr": "IP / host / ülke / ISP ara…",
        "en": "Search IP / host / country / ISP…",
        "es": "Buscar IP / host / país / ISP…",
        "ja": "IP / ホスト / 国 / ISP を検索…",
        "zh": "搜索 IP / 主机 / 国家 / ISP…",
        "hi": "IP / होस्ट / देश / ISP खोजें…",
    },
    "dash.detail": {
        "tr": "Detay", "en": "Detail", "es": "Detalle",
        "ja": "詳細", "zh": "详情", "hi": "विवरण",
    },
    "dash.back": {
        "tr": "← Geri", "en": "← Back", "es": "← Atrás",
        "ja": "← 戻る", "zh": "← 返回", "hi": "← वापस",
    },
    "dash.full_report": {
        "tr": "Tam Rapor Aç", "en": "Open Full Report", "es": "Abrir Informe Completo",
        "ja": "完全なレポートを開く", "zh": "打开完整报告", "hi": "पूरी रिपोर्ट खोलें",
    },
    "dash.targets_for_app": {
        "tr": "HEDEFLER (bu uygulama)",
        "en": "DESTINATIONS (for this app)",
        "es": "DESTINOS (esta app)",
        "ja": "接続先 (このアプリ)",
        "zh": "目标 (此应用)",
        "hi": "गंतव्य (इस ऐप के लिए)",
    },
    "dash.apps_for_remote": {
        "tr": "BU IP'YE BAĞLANAN UYGULAMALAR",
        "en": "APPS CONNECTING TO THIS IP",
        "es": "APPS QUE CONECTAN A ESTA IP",
        "ja": "この IP に接続するアプリ",
        "zh": "连接到此 IP 的应用",
        "hi": "इस IP से जुड़ने वाले ऐप्स",
    },

    # ----- COLUMN HEADERS -----
    "dash.col.app": {
        "tr": "Uygulama", "en": "App", "es": "App",
        "ja": "アプリ", "zh": "应用", "hi": "ऐप",
    },
    "dash.col.total": {
        "tr": "Toplam", "en": "Total", "es": "Total",
        "ja": "合計", "zh": "总计", "hi": "कुल",
    },
    "dash.col.in": {
        "tr": "↓ İndirme", "en": "↓ Download", "es": "↓ Descarga",
        "ja": "↓ ダウンロード", "zh": "↓ 下载", "hi": "↓ डाउनलोड",
    },
    "dash.col.out": {
        "tr": "↑ Yükleme", "en": "↑ Upload", "es": "↑ Subida",
        "ja": "↑ アップロード", "zh": "↑ 上传", "hi": "↑ अपलोड",
    },
    "dash.col.host": {
        "tr": "IP / Host", "en": "IP / Host", "es": "IP / Host",
        "ja": "IP / ホスト", "zh": "IP / 主机", "hi": "IP / होस्ट",
    },
    "dash.col.country": {
        "tr": "Ülke", "en": "Country", "es": "País",
        "ja": "国", "zh": "国家", "hi": "देश",
    },
    "dash.col.isp": {
        "tr": "ISP / Şehir", "en": "ISP / City", "es": "ISP / Ciudad",
        "ja": "ISP / 都市", "zh": "ISP / 城市", "hi": "ISP / शहर",
    },

    # ----- SECTION TITLES -----
    "dash.title.apps": {
        "tr": "En Çok Veri Kullanan Uygulamalar",
        "en": "Top Data-Using Apps",
        "es": "Apps que Más Datos Usan",
        "ja": "データ使用量が最も多いアプリ",
        "zh": "数据使用量最多的应用",
        "hi": "सबसे अधिक डेटा उपयोग करने वाले ऐप्स",
    },
    "dash.title.dest": {
        "tr": "Veri Hedefleri", "en": "Data Destinations", "es": "Destinos de Datos",
        "ja": "データ接続先", "zh": "数据目标", "hi": "डेटा गंतव्य",
    },
    "dash.title.quotas": {
        "tr": "Veri Kotaları", "en": "Data Quotas", "es": "Cuotas de Datos",
        "ja": "データクォータ", "zh": "数据配额", "hi": "डेटा कोटा",
    },
    "dash.title.networks": {
        "tr": "Ağlar", "en": "Networks", "es": "Redes",
        "ja": "ネットワーク", "zh": "网络", "hi": "नेटवर्क",
    },
    "dash.title.reports": {
        "tr": "Raporlar", "en": "Reports", "es": "Informes",
        "ja": "レポート", "zh": "报告", "hi": "रिपोर्ट",
    },
    "dash.title.export": {
        "tr": "Dışa Aktar", "en": "Export", "es": "Exportar",
        "ja": "エクスポート", "zh": "导出", "hi": "निर्यात",
    },
    "dash.title.settings": {
        "tr": "Ayarlar", "en": "Settings", "es": "Ajustes",
        "ja": "設定", "zh": "设置", "hi": "सेटिंग्स",
    },

    # ----- QUOTAS section -----
    "dash.quotas.subtitle": {
        "tr": "Limit aşılınca macOS bildirimi ve menü uyarısı düşer.",
        "en": "macOS notification and menu warning fire when limit exceeded.",
        "es": "Notificación de macOS y aviso de menú al superar el límite.",
        "ja": "上限超過時に macOS 通知とメニュー警告が表示されます。",
        "zh": "超出限制时显示 macOS 通知和菜单警告。",
        "hi": "सीमा पार होने पर macOS सूचना और मेनू चेतावनी।",
    },
    "dash.quotas.empty": {
        "tr": 'Tanımlı kota yok. Aşağıdaki "Kotaları Düzenle" butonuyla ekleyebilirsin.',
        "en": 'No quotas defined. Use "Edit Quotas" below to add some.',
        "es": 'Sin cuotas. Usa "Editar Cuotas" abajo para añadirlas.',
        "ja": "クォータ未定義です。下の「クォータを編集」から追加してください。",
        "zh": '尚未定义配额。请使用下方的"编辑配额"添加。',
        "hi": 'कोई कोटा नहीं। नीचे "कोटा संपादित करें" से जोड़ें।',
    },
    "dash.quotas.edit_button": {
        "tr": "Kotaları Düzenle…", "en": "Edit Quotas…", "es": "Editar Cuotas…",
        "ja": "クォータを編集…", "zh": "编辑配额…", "hi": "कोटा संपादित करें…",
    },

    # ----- NETWORKS section -----
    "dash.networks.current": {
        "tr": "Şu an: {n}", "en": "Now: {n}", "es": "Ahora: {n}",
        "ja": "現在: {n}", "zh": "当前: {n}", "hi": "अभी: {n}",
    },
    "dash.networks.col_ip": {
        "tr": "Gateway IP", "en": "Gateway IP", "es": "IP de Gateway",
        "ja": "ゲートウェイ IP", "zh": "网关 IP", "hi": "गेटवे IP",
    },
    "dash.networks.col_name": {
        "tr": "Görünür Ad", "en": "Display Name", "es": "Nombre",
        "ja": "表示名", "zh": "显示名称", "hi": "प्रदर्शन नाम",
    },
    "dash.networks.empty": {
        "tr": "Kayıtlı ağ alias'ı yok.",
        "en": "No saved network aliases.",
        "es": "Sin alias de red guardados.",
        "ja": "保存されたネットワークエイリアスなし。",
        "zh": "无保存的网络别名。",
        "hi": "कोई सहेजा गया नेटवर्क उपनाम नहीं।",
    },
    "dash.networks.edit_button": {
        "tr": "Ağları Düzenle…", "en": "Edit Networks…", "es": "Editar Redes…",
        "ja": "ネットワークを編集…", "zh": "编辑网络…", "hi": "नेटवर्क संपादित करें…",
    },

    # ----- REPORTS section -----
    "dash.reports.subtitle": {
        "tr": "HTML rapor tarayıcıda açılır — grafikler, tablolar, drill-down.",
        "en": "HTML reports open in browser — charts, tables, drill-down.",
        "es": "Informes HTML en el navegador — gráficos, tablas, detalle.",
        "ja": "HTML レポートはブラウザで開きます — グラフ、表、ドリルダウン。",
        "zh": "HTML 报告在浏览器中打开 — 图表、表格、深入分析。",
        "hi": "HTML रिपोर्ट ब्राउज़र में खुलती है — चार्ट, टेबल, विस्तार।",
    },
    "dash.reports.daily_desc": {
        "tr": "Bugünün uygulama, hedef ve saatlik kırılımı",
        "en": "Today's apps, destinations, and hourly breakdown",
        "es": "Apps, destinos y desglose horario de hoy",
        "ja": "今日のアプリ、接続先、時間別内訳",
        "zh": "今日的应用、目标和按小时明细",
        "hi": "आज के ऐप्स, गंतव्य और घंटे के अनुसार विवरण",
    },
    "dash.reports.monthly_desc": {
        "tr": "Bu ayın trendleri + ısı haritası",
        "en": "This month's trends + heatmap",
        "es": "Tendencias del mes + mapa de calor",
        "ja": "今月のトレンド + ヒートマップ",
        "zh": "本月趋势 + 热图",
        "hi": "इस माह के रुझान + हीटमैप",
    },
    "dash.reports.yearly_desc": {
        "tr": "Bu yılın tamamı",
        "en": "Whole year so far",
        "es": "Año completo hasta ahora",
        "ja": "今年全体",
        "zh": "本年全部",
        "hi": "अब तक का पूरा वर्ष",
    },
    "dash.reports.last30_desc": {
        "tr": "Kayan 30 günlük analiz",
        "en": "Rolling 30-day analysis",
        "es": "Análisis móvil de 30 días",
        "ja": "過去30日間の分析",
        "zh": "滚动 30 天分析",
        "hi": "रोलिंग 30-दिन का विश्लेषण",
    },

    # ----- EXPORT section -----
    "dash.export.subtitle": {
        "tr": "Seçili dönemin ham veri tablosunu Masaüstüne kaydeder.",
        "en": "Saves the raw data table for the period to Desktop.",
        "es": "Guarda la tabla de datos sin procesar en el Escritorio.",
        "ja": "選択期間の生データ表をデスクトップに保存します。",
        "zh": "将所选时段的原始数据表保存到桌面。",
        "hi": "चुनी अवधि के कच्चे डेटा को डेस्कटॉप पर सहेजता है।",
    },
    "dash.export.format": {
        "tr": "Format", "en": "Format", "es": "Formato",
        "ja": "形式", "zh": "格式", "hi": "प्रारूप",
    },
    "dash.export.button": {
        "tr": "Masaüstüne Aktar", "en": "Export to Desktop", "es": "Exportar al Escritorio",
        "ja": "デスクトップにエクスポート", "zh": "导出到桌面", "hi": "डेस्कटॉप पर निर्यात",
    },
    "dash.export.columns": {
        "tr": "CSV sütunları: timestamp, datetime, date, app, remote, bytes_in, bytes_out, network",
        "en": "CSV columns: timestamp, datetime, date, app, remote, bytes_in, bytes_out, network",
        "es": "Columnas CSV: timestamp, datetime, date, app, remote, bytes_in, bytes_out, network",
        "ja": "CSV 列: timestamp, datetime, date, app, remote, bytes_in, bytes_out, network",
        "zh": "CSV 列: timestamp, datetime, date, app, remote, bytes_in, bytes_out, network",
        "hi": "CSV कॉलम: timestamp, datetime, date, app, remote, bytes_in, bytes_out, network",
    },
    "dash.export.success": {
        "tr": "✓ {n} satır → {path}", "en": "✓ {n} rows → {path}", "es": "✓ {n} filas → {path}",
        "ja": "✓ {n} 行 → {path}", "zh": "✓ {n} 行 → {path}", "hi": "✓ {n} पंक्तियाँ → {path}",
    },
    "dash.export.error": {
        "tr": "✗ Hata: {e}", "en": "✗ Error: {e}", "es": "✗ Error: {e}",
        "ja": "✗ エラー: {e}", "zh": "✗ 错误: {e}", "hi": "✗ त्रुटि: {e}",
    },

    # ----- SETTINGS section -----
    "dash.settings.lang": {
        "tr": "Dil", "en": "Language", "es": "Idioma",
        "ja": "言語", "zh": "语言", "hi": "भाषा",
    },
    "dash.settings.daily_counter": {
        "tr": "Günlük sayaç", "en": "Daily counter", "es": "Contador diario",
        "ja": "日次カウンター", "zh": "每日计数", "hi": "दैनिक काउंटर",
    },
    "dash.settings.reset_button": {
        "tr": "Sıfırla", "en": "Reset", "es": "Reiniciar",
        "ja": "リセット", "zh": "重置", "hi": "रीसेट",
    },
    "dash.settings.app": {
        "tr": "Uygulama", "en": "Application", "es": "Aplicación",
        "ja": "アプリケーション", "zh": "应用程序", "hi": "एप्लिकेशन",
    },
    "dash.settings.quit_button": {
        "tr": "Uygulamayı Kapat", "en": "Quit Application", "es": "Salir",
        "ja": "アプリを終了", "zh": "退出应用", "hi": "एप्लिकेशन बंद करें",
    },

    # ----- Period option names -----
    "period.today": {
        "tr": "Bugün", "en": "Today", "es": "Hoy",
        "ja": "今日", "zh": "今天", "hi": "आज",
    },
    "period.month": {
        "tr": "Bu Ay", "en": "This Month", "es": "Este Mes",
        "ja": "今月", "zh": "本月", "hi": "इस माह",
    },
    "period.year": {
        "tr": "Bu Yıl", "en": "This Year", "es": "Este Año",
        "ja": "今年", "zh": "今年", "hi": "इस वर्ष",
    },
    "period.last30": {
        "tr": "Son 30 Gün", "en": "Last 30 Days", "es": "Últimos 30 Días",
        "ja": "過去30日間", "zh": "最近30天", "hi": "पिछले 30 दिन",
    },
    "period.all": {
        "tr": "Tümü", "en": "All Time", "es": "Todo",
        "ja": "全期間", "zh": "全部", "hi": "सभी",
    },
    "menu.label.down": {
        "tr": "DOWN", "en": "DOWN", "es": "BAJA",
        "ja": "下り", "zh": "下载", "hi": "डाउन",
    },
    "menu.label.up": {
        "tr": "UP", "en": "UP", "es": "SUBE",
        "ja": "上り", "zh": "上传", "hi": "अप",
    },
    "menu.label.rx": {
        "tr": "RX", "en": "RX", "es": "RX",
        "ja": "受信", "zh": "接收", "hi": "RX",
    },
    "menu.label.tx": {
        "tr": "TX", "en": "TX", "es": "TX",
        "ja": "送信", "zh": "发送", "hi": "TX",
    },
    "menu.label.total": {
        "tr": "TOTAL", "en": "TOTAL", "es": "TOTAL",
        "ja": "合計", "zh": "总计", "hi": "कुल",
    },

    # ----- REPORT -----
    "report.title": {
        "tr": "Veri Kullanım Raporu", "en": "Data Usage Report", "es": "Informe de Uso de Datos",
        "ja": "データ使用量レポート", "zh": "数据使用报告", "hi": "डेटा उपयोग रिपोर्ट",
    },
    "report.period.today": {
        "tr": "Bugün", "en": "Today", "es": "Hoy",
        "ja": "今日", "zh": "今天", "hi": "आज",
    },
    "report.period.month": {
        "tr": "Bu Ay ({m})", "en": "This Month ({m})", "es": "Este Mes ({m})",
        "ja": "今月 ({m})", "zh": "本月 ({m})", "hi": "इस माह ({m})",
    },
    "report.period.year": {
        "tr": "Bu Yıl ({y})", "en": "This Year ({y})", "es": "Este Año ({y})",
        "ja": "今年 ({y})", "zh": "今年 ({y})", "hi": "इस वर्ष ({y})",
    },
    "report.period.last30": {
        "tr": "Son 30 Gün", "en": "Last 30 Days", "es": "Últimos 30 Días",
        "ja": "過去30日間", "zh": "最近30天", "hi": "पिछले 30 दिन",
    },
    "report.back": {
        "tr": "[ ANA RAPORA DÖN ]", "en": "[ BACK TO MAIN ]", "es": "[ VOLVER ]",
        "ja": "[ メインに戻る ]", "zh": "[ 返回主页 ]", "hi": "[ मुख्य पर वापस ]",
    },

    # ----- STATS -----
    "stat.total_data": {
        "tr": "Toplam Veri", "en": "Total Data", "es": "Datos Totales",
        "ja": "総データ量", "zh": "总数据量", "hi": "कुल डेटा",
    },
    "stat.downloaded": {
        "tr": "İndirilen", "en": "Downloaded", "es": "Descargado",
        "ja": "ダウンロード", "zh": "已下载", "hi": "डाउनलोड",
    },
    "stat.uploaded": {
        "tr": "Yüklenen", "en": "Uploaded", "es": "Subido",
        "ja": "アップロード", "zh": "已上传", "hi": "अपलोड",
    },
    "stat.sub.dl_ul": {
        "tr": "İndirme + Yükleme", "en": "Download + Upload", "es": "Descarga + Subida",
        "ja": "ダウンロード + アップロード", "zh": "下载 + 上传", "hi": "डाउनलोड + अपलोड",
    },
    "stat.total": {
        "tr": "Toplam", "en": "Total", "es": "Total",
        "ja": "合計", "zh": "总计", "hi": "कुल",
    },

    # ----- SECTIONS -----
    "section.daily_trend": {
        "tr": "Günlük Trend", "en": "Daily Trend", "es": "Tendencia Diaria",
        "ja": "日次トレンド", "zh": "每日趋势", "hi": "दैनिक रुझान",
    },
    "section.hour_usage": {
        "tr": "Saatlik Kullanım", "en": "Hourly Usage", "es": "Uso por Hora",
        "ja": "時間別使用量", "zh": "按小时使用", "hi": "घंटे के अनुसार उपयोग",
    },
    "section.hour_usage_total": {
        "tr": "Saatlik Kullanım (Tüm Dönem)", "en": "Hourly Usage (Full Period)", "es": "Uso por Hora (Todo el Periodo)",
        "ja": "時間別使用量 (全期間)", "zh": "按小时使用 (整段时间)", "hi": "घंटे के अनुसार उपयोग (पूरी अवधि)",
    },
    "section.heatmap": {
        "tr": "Saatlik Isı Haritası (Tarih × Saat)", "en": "Hourly Heatmap (Date × Hour)", "es": "Mapa de Calor (Fecha × Hora)",
        "ja": "時間ヒートマップ (日付 × 時刻)", "zh": "时间热图 (日期 × 小时)", "hi": "घंटे का हीटमैप (दिनांक × घंटा)",
    },
    "section.top_apps": {
        "tr": "En Çok Veri Kullanan Uygulamalar", "en": "Top Data-Using Apps", "es": "Apps que Más Datos Usan",
        "ja": "データ使用量が最も多いアプリ", "zh": "数据使用量最多的应用", "hi": "सबसे अधिक डेटा उपयोग करने वाले ऐप्स",
    },
    "section.app_details": {
        "tr": "Uygulama Detayları", "en": "App Details", "es": "Detalles de Apps",
        "ja": "アプリ詳細", "zh": "应用详情", "hi": "ऐप विवरण",
    },
    "section.click_for_details": {
        "tr": "(tıkla → detay)", "en": "(click → detail)", "es": "(clic → detalle)",
        "ja": "(クリック → 詳細)", "zh": "(点击 → 详情)", "hi": "(क्लिक → विवरण)",
    },
    "section.service_distribution": {
        "tr": "Servis Bazlı Dağılım", "en": "Service Breakdown", "es": "Distribución por Servicio",
        "ja": "サービス別内訳", "zh": "按服务分布", "hi": "सेवा के अनुसार वितरण",
    },
    "section.service_details": {
        "tr": "Servis Detayları", "en": "Service Details", "es": "Detalles de Servicios",
        "ja": "サービス詳細", "zh": "服务详情", "hi": "सेवा विवरण",
    },
    "section.network_usage": {
        "tr": "Ağ Bazlı Kullanım", "en": "Network Usage", "es": "Uso por Red",
        "ja": "ネットワーク別使用量", "zh": "按网络使用", "hi": "नेटवर्क के अनुसार उपयोग",
    },
    "section.destinations": {
        "tr": "Veri Gönderilen / Çekilen Hedefler (IP Detayı)",
        "en": "Destinations Sent To / Pulled From (IP Detail)",
        "es": "Destinos (Detalle de IP)",
        "ja": "送信/受信先 (IP詳細)",
        "zh": "数据收发目标 (IP详情)",
        "hi": "गंतव्य (IP विवरण)",
    },
    "section.app_targets": {
        "tr": "{app} — Hedefler", "en": "{app} — Destinations", "es": "{app} — Destinos",
        "ja": "{app} — 接続先", "zh": "{app} — 目标", "hi": "{app} — गंतव्य",
    },

    # ----- TABLE HEADERS -----
    "table.app": {
        "tr": "Uygulama", "en": "App", "es": "Aplicación",
        "ja": "アプリ", "zh": "应用", "hi": "ऐप",
    },
    "table.total": {
        "tr": "Toplam", "en": "Total", "es": "Total",
        "ja": "合計", "zh": "总计", "hi": "कुल",
    },
    "table.download": {
        "tr": "İndirme", "en": "Download", "es": "Descarga",
        "ja": "ダウンロード", "zh": "下载", "hi": "डाउनलोड",
    },
    "table.upload": {
        "tr": "Yükleme", "en": "Upload", "es": "Subida",
        "ja": "アップロード", "zh": "上传", "hi": "अपलोड",
    },
    "table.target": {
        "tr": "Hedef", "en": "Target", "es": "Destino",
        "ja": "接続先", "zh": "目标", "hi": "गंतव्य",
    },
    "table.fetched": {
        "tr": "Çekilen", "en": "Pulled", "es": "Recibido",
        "ja": "受信", "zh": "接收", "hi": "प्राप्त",
    },
    "table.sent": {
        "tr": "Gönderilen", "en": "Sent", "es": "Enviado",
        "ja": "送信", "zh": "发送", "hi": "भेजा",
    },
    "table.service": {
        "tr": "Servis", "en": "Service", "es": "Servicio",
        "ja": "サービス", "zh": "服务", "hi": "सेवा",
    },
    "table.network": {
        "tr": "Ağ", "en": "Network", "es": "Red",
        "ja": "ネットワーク", "zh": "网络", "hi": "नेटवर्क",
    },

    # ----- BUTTONS -----
    "btn.show_more": {
        "tr": "+ DAHA FAZLA GÖSTER ({n})", "en": "+ SHOW MORE ({n})", "es": "+ MOSTRAR MÁS ({n})",
        "ja": "+ もっと表示 ({n})", "zh": "+ 显示更多 ({n})", "hi": "+ और दिखाएं ({n})",
    },
    "btn.show_less": {
        "tr": "− DAHA AZ GÖSTER", "en": "− SHOW LESS", "es": "− MOSTRAR MENOS",
        "ja": "− 表示を減らす", "zh": "− 显示更少", "hi": "− कम दिखाएं",
    },

    # ----- MISC -----
    "misc.no_data": {
        "tr": "Veri yok", "en": "No data", "es": "Sin datos",
        "ja": "データなし", "zh": "无数据", "hi": "कोई डेटा नहीं",
    },
    "misc.no_network_data": {
        "tr": "Ağ verisi yok", "en": "No network data", "es": "Sin datos de red",
        "ja": "ネットワークデータなし", "zh": "无网络数据", "hi": "कोई नेटवर्क डेटा नहीं",
    },
    "misc.low": {
        "tr": "DÜŞÜK", "en": "LOW", "es": "BAJO",
        "ja": "少", "zh": "少", "hi": "कम",
    },
    "misc.high": {
        "tr": "YÜKSEK", "en": "HIGH", "es": "ALTO",
        "ja": "多", "zh": "多", "hi": "अधिक",
    },
    "misc.untracked": {
        "tr": "(kayıtsız)", "en": "(untracked)", "es": "(sin registro)",
        "ja": "(未追跡)", "zh": "(未跟踪)", "hi": "(अज्ञात)",
    },
    "misc.local_unknown": {
        "tr": "Yerel / Bilinmiyor", "en": "Local / Unknown", "es": "Local / Desconocido",
        "ja": "ローカル / 不明", "zh": "本地 / 未知", "hi": "स्थानीय / अज्ञात",
    },
    "misc.unconnected": {
        "tr": "Bağlı Değil", "en": "Not Connected", "es": "Sin Conexión",
        "ja": "未接続", "zh": "未连接", "hi": "अनकनेक्टेड",
    },

    # ----- CHART -----
    "chart.download": {
        "tr": "İNDİRME", "en": "DOWNLOAD", "es": "DESCARGA",
        "ja": "ダウンロード", "zh": "下载", "hi": "डाउनलोड",
    },
    "chart.upload": {
        "tr": "YÜKLEME", "en": "UPLOAD", "es": "SUBIDA",
        "ja": "アップロード", "zh": "上传", "hi": "अपलोड",
    },
}


def get_setting(key, default=None):
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f).get(key, default)
        except Exception:
            pass
    return default


def set_setting(key, value):
    data = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
        except Exception:
            pass
    data[key] = value
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_lang():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                lang = json.load(f).get("language")
            if lang in SUPPORTED:
                return lang
        except Exception:
            pass
    return DEFAULT_LANG


def set_lang(lang):
    if lang not in SUPPORTED:
        return False
    data = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
        except Exception:
            pass
    data["language"] = lang
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True


def t(key, lang=None, **kwargs):
    if lang is None:
        lang = get_lang()
    entry = T.get(key)
    if not entry:
        return key
    s = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return s.format(**kwargs)
        except (KeyError, IndexError):
            return s
    return s
