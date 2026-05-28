#!/usr/bin/env python3
"""Generate macOS app icon (.icns) from icon.svg.
Renders all iconset sizes via PyObjC NSImage, then runs `iconutil` to bundle.
"""
import os
import sys
import subprocess

from Foundation import NSURL, NSSize
from AppKit import (
    NSImage, NSBitmapImageRep, NSGraphicsContext,
    NSCompositingOperationCopy, NSBitmapImageFileTypePNG,
)

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(HERE, "icon.svg")
ICONSET = os.path.join(HERE, "AppIcon.iconset")
ICNS = os.path.join(HERE, "AppIcon.icns")

# (filename, pixel_size)
SIZES = [
    ("icon_16x16.png",       16),
    ("icon_16x16@2x.png",    32),
    ("icon_32x32.png",       32),
    ("icon_32x32@2x.png",    64),
    ("icon_128x128.png",    128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png",    256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png",    512),
    ("icon_512x512@2x.png", 1024),
]


def render_png(svg_path, png_path, size):
    """Rasterize SVG into a PNG of the given square size via NSImage."""
    url = NSURL.fileURLWithPath_(svg_path)
    src = NSImage.alloc().initWithContentsOfURL_(url)
    if src is None:
        raise RuntimeError(f"Could not load SVG: {svg_path}")

    rep = (NSBitmapImageRep.alloc()
           .initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
                None, int(size), int(size), 8, 4, True, False,
                "NSCalibratedRGBColorSpace", 0, 0))
    rep.setSize_(NSSize(size, size))

    NSGraphicsContext.saveGraphicsState()
    try:
        ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
        NSGraphicsContext.setCurrentContext_(ctx)
        from Foundation import NSMakeRect
        src_size = src.size()
        src.drawInRect_fromRect_operation_fraction_(
            NSMakeRect(0, 0, size, size),
            NSMakeRect(0, 0, src_size.width, src_size.height),
            NSCompositingOperationCopy,
            1.0,
        )
    finally:
        NSGraphicsContext.restoreGraphicsState()

    png_data = rep.representationUsingType_properties_(NSBitmapImageFileTypePNG, None)
    if png_data is None:
        raise RuntimeError("PNG encode failed")
    if not png_data.writeToFile_atomically_(png_path, True):
        raise RuntimeError(f"PNG write failed: {png_path}")


def main():
    if not os.path.exists(SVG):
        print(f"Missing: {SVG}", file=sys.stderr)
        sys.exit(1)

    # Clean iconset
    if os.path.exists(ICONSET):
        import shutil
        shutil.rmtree(ICONSET)
    os.makedirs(ICONSET)

    for fname, size in SIZES:
        out = os.path.join(ICONSET, fname)
        render_png(SVG, out, size)
        print(f"  {size:4}x{size:<4}  ->  {fname}")

    # Bundle into .icns
    print(f"\n[iconutil] -> {ICNS}")
    subprocess.run(
        ["iconutil", "-c", "icns", ICONSET, "-o", ICNS],
        check=True
    )
    print(f"Done.  Iconset: {ICONSET}")
    print(f"       Icns:    {ICNS}")


if __name__ == "__main__":
    main()
