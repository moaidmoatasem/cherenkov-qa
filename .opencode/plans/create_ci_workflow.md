#!/usr/bin/env python3
"""Create CI workflow, VS Code icon (PNG), fix package.json."""
import json, struct, zlib, os

PROJ = "/home/moaid/cherenkov-qa"

# CI workflow
ci = """name: Cherenkov Conformance

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Run Cherenkov conformance
        uses: ./
        with:
          spec_path: stub/openapi_3_1.yaml
          target_url: http://localhost:8000
          format: sarif
          mode: full
"""

d = os.path.join(PROJ, ".github", "workflows")
os.makedirs(d, exist_ok=True)
with open(os.path.join(d, "cherenkov-ci.yml"), "w") as f:
    f.write(ci)
print(f"CI workflow: {len(ci)} bytes")

# Create PNG icon
def create_png(width, height, r, g, b):
    def chunk(ctype, data):
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw = b""
    for y in range(height):
        raw += b"\x00"
        for x in range(width):
            raw += bytes([r, g, b])
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend

img_d = os.path.join(PROJ, "vscode", "images")
os.makedirs(img_d, exist_ok=True)
png_data = create_png(128, 128, 88, 166, 255)
with open(os.path.join(img_d, "icon.png"), "wb") as f:
    f.write(png_data)
print(f"PNG icon: {len(png_data)} bytes")

# Update package.json icon
pkg_path = os.path.join(PROJ, "vscode", "package.json")
with open(pkg_path) as f:
    pkg = json.load(f)
pkg["icon"] = "images/icon.png"
with open(pkg_path, "w") as f:
    json.dump(pkg, f, indent=2)
print(f"Package.json icon: images/icon.png")
