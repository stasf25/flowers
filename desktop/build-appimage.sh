#!/usr/bin/env bash
# Сборка CompetitorMonitor-x86_64.AppImage внутри qt6-контейнера.
# Запуск С ХОСТА (xubuntu) из корня проекта (desktop/ хоста проброшен в /work контейнера):
#   docker build -t competitor-desktop ./desktop
#   docker run --rm -u $(`id -u`):$(`id -g`) -v "$PWD/desktop:/work" competitor-desktop bash /work/build-appimage.sh
# Результат: desktop/CompetitorMonitor-x86_64.AppImage
set -euo pipefail

WORKDIR=/work
OUTDIR="$WORKDIR/build"
APPDIR="$OUTDIR/AppDir"
TOOLS="$WORKDIR/.tools"
VENV="$WORKDIR/build-venv"
BUILD="$OUTDIR/build"
DIST="$OUTDIR/dist"
FONTS="$APPDIR/usr/share/fonts"

rm -rf "$OUTDIR"
mkdir -p "$OUTDIR" "$TOOLS" "$BUILD" "$DIST" "$FONTS"
echo "*" > "$OUTDIR/.gitignore"
echo "*" > "$TOOLS/.gitignore"
cd "$WORKDIR"

# --- 0. venv + зависимости ---
python3.10 -m venv "$VENV"
"$VENV/bin/pip" install -U pip
"$VENV/bin/pip" install -r requirements.txt
echo "*" > "$VENV/.gitignore"

# --- 1. PyInstaller: one-dir сборка ---
"$VENV/bin/pyinstaller" \
  --name CompetitorMonitor \
  --onedir \
  --windowed \
  --noconfirm \
  --clean \
  --hidden-import PyQt6 \
  --hidden-import PyQt6.QtCore \
  --hidden-import PyQt6.QtWidgets \
  --hidden-import PyQt6.QtGui \
  --hidden-import requests \
  --workpath "$BUILD" \
  --distpath "$DIST" \
  --specpath "$OUTDIR" \
  main.py

EXE="$DIST/CompetitorMonitor/CompetitorMonitor"
test -x "$EXE" || { echo "ERR: бинарник не собран: $EXE"; exit 1; }

# Перемещаем в APPDIR вместе с _internal
mv "$DIST/CompetitorMonitor" "$APPDIR/usr/bin"

# --- 2. Иконка 256x256 (генерируем, чтобы не тащить бинарный ассет в git) ---
ICON="$OUTDIR/competitor-monitor.png"
"$VENV/bin/python" - "$ICON" <<'EOF'
import math, sys
from PIL import Image, ImageDraw
path, S = sys.argv[1], 256
img = Image.new("RGBA", (S, S), (13, 18, 38, 255))
d = ImageDraw.Draw(img)
cx = cy = S // 2
for i in range(6):  # лепестки
    a = math.pi * i / 3
    x, y = cx + int(52 * math.cos(a)), cy + int(52 * math.sin(a))
    d.ellipse([x - 34, y - 34, x + 34, y + 34], fill=(34, 211, 238, 255))
d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(251, 191, 36, 255))  # серединка
img.save(path)
print("icon:", path)
EOF

# --- 3. Шрифты с кириллицей внутрь AppDir (DejaVu устанавливается в desktop/Dockerfile) ---
cp -r /usr/share/fonts/truetype/dejavu "$FONTS" 2>/dev/null || echo "WARN: DejaVu не найден, кириллица — шрифтами хоста"

# --- 4. linuxdeploy: скачивание один раз ---
LINUXDEPLOY="$TOOLS/linuxdeploy-x86_64.AppImage"

if [ ! -x "$LINUXDEPLOY" ]; then
  wget -q -O "$LINUXDEPLOY" https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
  chmod +x "$LINUXDEPLOY"
fi

# --- 5. Сборка AppImage ---
export QMAKE="$(which qmake6)"
export APPIMAGE_EXTRACT_AND_RUN=1
#export DEBUG=1

"$LINUXDEPLOY" \
  --appdir "$APPDIR" \
  -e "$APPDIR/usr/bin/CompetitorMonitor" \
  -d "$WORKDIR/assets/competitor-monitor.desktop" \
  -i "$ICON" \
  --output appimage

