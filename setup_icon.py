#!/usr/bin/env python3
"""One-time setup: creates the Crypto Digest .app on your Desktop."""

import os
import sys
import subprocess
import shutil
import tempfile
import textwrap
from pathlib import Path

HOME = Path.home()
DESKTOP = HOME / "Desktop"
PROJECT_DIR = HOME / "crypto-digest"
PYTHON = sys.executable
APP_NAME = "Crypto Digest"
APP_PATH = DESKTOP / f"{APP_NAME}.app"

# ── 1. AppleScript launcher ──────────────────────────────────────────────────

APPLESCRIPT = textwrap.dedent(f'''\
    on run
        set projectDir to "{PROJECT_DIR}"
        set pythonPath to "{PYTHON}"
        set logFile to "/tmp/crypto-digest.log"

        -- Check if server is already running
        set serverRunning to false
        try
            do shell script "curl -sf --max-time 2 http://localhost:8080/api/status > /dev/null"
            set serverRunning to true
        end try

        if not serverRunning then
            do shell script "cd " & quoted form of projectDir & " && nohup " & pythonPath & " run.py >> " & logFile & " 2>&1 &"

            -- Wait up to 20 seconds
            set attempts to 0
            repeat
                delay 1
                set attempts to attempts + 1
                try
                    do shell script "curl -sf --max-time 2 http://localhost:8080/api/status > /dev/null"
                    exit repeat
                on error
                    if attempts >= 20 then
                        display dialog "Crypto Digest failed to start." & return & "Check /tmp/crypto-digest.log for details." buttons {{"OK"}} default button 1 with icon stop with title "Crypto Digest"
                        return
                    end if
                end try
            end repeat
        end if

        try
            tell application "Google Chrome"
                activate
                open location "http://localhost:8080"
            end tell
        on error
            do shell script "open 'http://localhost:8080'"
        end try
    end run
''')

script_file = PROJECT_DIR / "_launcher.applescript"
script_file.write_text(APPLESCRIPT)

if APP_PATH.exists():
    shutil.rmtree(APP_PATH)

result = subprocess.run(
    ["osacompile", "-o", str(APP_PATH), str(script_file)],
    capture_output=True, text=True,
)
if result.returncode != 0:
    print(f"osacompile error: {result.stderr}")
    sys.exit(1)
script_file.unlink()
print(f"[1/3] App bundle created: {APP_PATH}")

# ── 2. Generate icon ─────────────────────────────────────────────────────────

from PIL import Image, ImageDraw

SIZE = 1024
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

MARGIN = SIZE // 16
RADIUS = SIZE // 5

# Deep indigo background
draw.rounded_rectangle(
    [(MARGIN, MARGIN), (SIZE - MARGIN, SIZE - MARGIN)],
    radius=RADIUS,
    fill=(67, 56, 202, 255),  # indigo-700
)

# Subtle inner highlight at top
for y in range(MARGIN + RADIUS // 2, MARGIN + RADIUS * 2):
    alpha = int(25 * (1 - (y - MARGIN - RADIUS // 2) / (RADIUS * 1.5)))
    if alpha > 0:
        draw.line(
            [(MARGIN + RADIUS, y), (SIZE - MARGIN - RADIUS, y)],
            fill=(255, 255, 255, alpha),
        )

# Trend line points
LINE_W = SIZE // 22
PAD = SIZE // 5
points = [
    (PAD, int(SIZE * 0.68)),
    (int(SIZE * 0.30), int(SIZE * 0.56)),
    (int(SIZE * 0.48), int(SIZE * 0.63)),
    (int(SIZE * 0.68), int(SIZE * 0.36)),
    (SIZE - PAD, int(SIZE * 0.24)),
]

# Drop shadow
shadow = [(x + 10, y + 10) for x, y in points]
draw.line(shadow, fill=(0, 0, 0, 55), width=LINE_W + 4)

# Main white trend line
draw.line(points, fill=(255, 255, 255, 235), width=LINE_W)

# Filled circles at each data point
DOT_R = int(LINE_W * 1.4)
for px, py in points:
    draw.ellipse(
        [(px - DOT_R, py - DOT_R), (px + DOT_R, py + DOT_R)],
        fill=(255, 255, 255, 255),
    )

# Arrow at the last point (pointing up-right)
ex, ey = points[-1]
AH = int(LINE_W * 1.6)
draw.polygon(
    [(ex - AH, ey + AH * 2), (ex + AH, ey + AH * 2), (ex, ey - AH)],
    fill=(255, 255, 255, 235),
)

icon_1024 = PROJECT_DIR / "_icon_1024.png"
img.save(str(icon_1024))
print("[2/3] Icon PNG generated")

# ── 3. Convert to .icns and apply ────────────────────────────────────────────

with tempfile.TemporaryDirectory() as tmpdir:
    iconset = Path(tmpdir) / "icon.iconset"
    iconset.mkdir()

    sizes = [
        (16, 1), (16, 2),
        (32, 1), (32, 2),
        (128, 1), (128, 2),
        (256, 1), (256, 2),
        (512, 1), (512, 2),
    ]
    for base_sz, scale in sizes:
        px = base_sz * scale
        name = f"icon_{base_sz}x{base_sz}{'@2x' if scale == 2 else ''}.png"
        subprocess.run(
            ["sips", "-z", str(px), str(px), str(icon_1024), "--out", str(iconset / name)],
            capture_output=True, check=True,
        )

    icns_out = PROJECT_DIR / "_icon.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_out)],
        check=True, capture_output=True,
    )

    # Replace the default applet icon inside the .app bundle
    resources = APP_PATH / "Contents" / "Resources"
    shutil.copy(str(icns_out), str(resources / "applet.icns"))

# Clean up temp files
icon_1024.unlink(missing_ok=True)
icns_out.unlink(missing_ok=True)
print("[3/3] Icon applied to app bundle")

# Refresh Finder so icon shows immediately
subprocess.run(["touch", str(APP_PATH)], check=True)
subprocess.run(["killall", "Finder"], capture_output=True)

print(f"\nDone! Open your Desktop and double-click '{APP_NAME}'.")
print("Make sure ~/crypto-digest/.env has your ANTHROPIC_API_KEY set.")
