#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

echo "==> Building frontend"
if [[ ! -d frontend/node_modules ]]; then
  (cd frontend && npm ci)
fi
(cd frontend && npm run build)

echo "==> Installing desktop packaging deps"
python3 -m pip install --no-cache-dir -r requirements-desktop.txt

echo "==> Packaging desktop app"
python3 -m PyInstaller packaging/aisummarizer.spec --noconfirm --clean

RELEASE_ROOT="$ROOT/releases/desktop"
mkdir -p "$RELEASE_ROOT"

if [[ "$(uname)" == "Darwin" && -d "dist/AI Study Guide Generator.app" ]]; then
  MAC_DIR="$RELEASE_ROOT/mac"
  rm -rf "$MAC_DIR"
  mkdir -p "$MAC_DIR"
  cp -R "dist/AI Study Guide Generator.app" "$MAC_DIR/"
  DMG="$MAC_DIR/AI-Study-Guide-Generator.dmg"
  echo "==> Creating DMG installer"
  hdiutil create -volname "AI Study Guide Generator" -srcfolder "dist/AI Study Guide Generator.app" -ov -format UDZO "$DMG"
  OUT="$MAC_DIR"
elif [[ -d "dist/AI Study Guide Generator" ]]; then
  WIN_DIR="$RELEASE_ROOT/windows"
  rm -rf "$WIN_DIR"
  mkdir -p "$WIN_DIR"
  cp -R "dist/AI Study Guide Generator" "$WIN_DIR/"
  OUT="$WIN_DIR"
else
  OUT="dist/AI Study Guide Generator"
fi

echo ""
echo "Done. Release folder:"
echo "  $OUT"
