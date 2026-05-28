#!/bin/bash
# Build polished DMG for 1 Bit Data with custom background + drag-to-Applications layout
set -euo pipefail

APP_NAME="1 Bit Data"
VERSION="0.1.1"
HERE="$(cd "$(dirname "$0")" && pwd)"
DIST="$HERE/dist"
APP="$DIST/$APP_NAME.app"
BG_PNG="$HERE/assets/dmg-bg.png"
BG_PNG_2X="$HERE/assets/dmg-bg@2x.png"
DMG_OUT="$DIST/$APP_NAME $VERSION.dmg"
DMG_TMP="$DIST/$APP_NAME-rw.dmg"
VOL_NAME="$APP_NAME"
STAGING="$DIST/dmg-staging"
IDENTITY="Developer ID Application: Fatih Emir Önder (RLJA79W3WW)"

# --- Sanity ---
[ -d "$APP" ] || { echo "Missing $APP"; exit 1; }
[ -f "$BG_PNG" ] || { echo "Missing $BG_PNG"; exit 1; }

# --- Clean ---
rm -rf "$STAGING" "$DMG_OUT" "$DMG_TMP"
mkdir -p "$STAGING"

# --- Stage contents ---
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
mkdir "$STAGING/.background"
cp "$BG_PNG" "$STAGING/.background/bg.png"
cp "$BG_PNG_2X" "$STAGING/.background/bg@2x.png"

# --- Create read-write DMG (big enough for app + bg) ---
hdiutil create -volname "$VOL_NAME" -srcfolder "$STAGING" \
  -fs HFS+ -fsargs "-c c=64,a=16,e=16" \
  -format UDRW -size 60m "$DMG_TMP"

# --- Mount ---
MOUNT_OUTPUT=$(hdiutil attach -readwrite -noverify -noautoopen "$DMG_TMP")
DEVICE=$(echo "$MOUNT_OUTPUT" | grep -E '^/dev/' | head -1 | awk '{print $1}')
MOUNT_POINT="/Volumes/$VOL_NAME"
sleep 2

# --- Configure Finder window via AppleScript ---
osascript <<APPLESCRIPT
tell application "Finder"
    tell disk "$VOL_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {200, 120, 920, 560}

        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 144
        set text size of viewOptions to 13
        set background picture of viewOptions to file ".background:bg.png"
        set label position of viewOptions to bottom

        set position of item "$APP_NAME.app" of container window to {180, 230}
        set position of item "Applications" of container window to {540, 230}

        close
        open
        update without registering applications
        delay 1
    end tell
end tell
APPLESCRIPT

sleep 2
sync
hdiutil detach "$DEVICE" -force || true
sleep 1

# --- Convert to compressed read-only ---
hdiutil convert "$DMG_TMP" -format UDZO -imagekey zlib-level=9 -o "$DMG_OUT"
rm -f "$DMG_TMP"
rm -rf "$STAGING"

# --- Sign DMG ---
codesign --force --sign "$IDENTITY" --timestamp "$DMG_OUT"

# --- Notarize + staple ---
echo ""
echo "=== Notarizing DMG ==="
xcrun notarytool submit "$DMG_OUT" \
  --keychain-profile "1bitdata-notarize" \
  --wait

xcrun stapler staple "$DMG_OUT"

echo ""
echo "=== DONE ==="
ls -lh "$DMG_OUT"
spctl -a -t open --context context:primary-signature -v "$DMG_OUT"
