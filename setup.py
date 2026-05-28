"""py2app build script for 1 Bit Data.

Usage:
  Quick dev build (symlinks source — fast):
    /usr/bin/python3 setup.py py2app -A
  Production build (standalone, distributable):
    /usr/bin/python3 setup.py py2app
"""
from setuptools import setup

APP = ["data_monitor.py"]
APP_NAME = "1 Bit Data"

OPTIONS = {
    "iconfile": "assets/AppIcon.icns",
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.1bitstudios.1bitdata",
        "CFBundleVersion": "0.1.1",
        "CFBundleShortVersionString": "0.1.1",
        "CFBundleExecutable": APP_NAME,
        # Menu-bar only app (no Dock icon, no main window in App Switcher)
        "LSUIElement": True,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        # Privacy descriptions (TCC prompts on first use)
        "NSAppleEventsUsageDescription":
            "1 Bit Data uses Apple events to coordinate with macOS network tools.",
        "NSSystemAdministrationUsageDescription":
            "1 Bit Data reads network usage statistics via nettop.",
        "NSHumanReadableCopyright": "© 1 Bit Studios",
    },
    "packages": ["rumps", "psutil"],
    # PyObjC sub-frameworks we touch — bundled explicitly
    "includes": [
        "objc", "Foundation", "AppKit", "Quartz", "CoreFoundation",
        "data_tracker", "dashboard", "config_ui",
        "data_report", "data_export", "speedtest", "quotas",
        "i18n",
    ],
    "resources": ["assets"],
    # Don't compile to .pyc — keeps debugging easier; size diff tiny
    "optimize": 0,
    "argv_emulation": False,
}

setup(
    app=APP,
    name=APP_NAME,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
