#!/usr/bin/env bash
# Build the Linux portable archive and .deb installer into dist/.
# Run from the project root with the virtual environment active:
#   python -m pip install -r requirements.txt pyinstaller
#   bash packaging/build_linux.sh
set -euo pipefail

VERSION="$(python -c 'import tidytray; print(tidytray.__version__)')"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"

pyinstaller --noconfirm --clean --windowed --name TidyTray \
  --icon packaging/tidytray.png run_tidytray.py

# License texts travel with every build.
cp LICENSE THIRD_PARTY_NOTICES.md README.md dist/TidyTray/

# Portable: unpack anywhere and run ./TidyTray/TidyTray. No root needed.
cp packaging/tidytray.png dist/TidyTray/tidytray.png
tar -C dist -czf "dist/TidyTray-${VERSION}-linux-x86_64-portable.tar.gz" TidyTray

# Installer: a .deb that installs to /opt/tidytray with a menu entry.
PKG="build/deb/tidytray_${VERSION}_${ARCH}"
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt" "$PKG/usr/bin" \
  "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/256x256/apps" \
  "$PKG/usr/share/doc/tidytray"
cp -a dist/TidyTray "$PKG/opt/tidytray"
ln -s /opt/tidytray/TidyTray "$PKG/usr/bin/tidytray"
sed 's/^Icon=.*/Icon=tidytray/' packaging/tidytray.desktop > "$PKG/usr/share/applications/tidytray.desktop"
cp packaging/tidytray.png "$PKG/usr/share/icons/hicolor/256x256/apps/tidytray.png"
{
  echo "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"
  echo "Upstream-Name: TidyTray"
  echo "Source: https://github.com/naOomeow/tidytray"
  echo
  echo "Files: *"
  echo "Copyright: 2026 naOomeow"
  echo "License: GPL-3+"
  echo " On Debian systems the full license text is in /usr/share/common-licenses/GPL-3."
  echo " Bundled third-party components are listed in /opt/tidytray/THIRD_PARTY_NOTICES.md."
} > "$PKG/usr/share/doc/tidytray/copyright"
INSTALLED_KB="$(du -sk "$PKG" | cut -f1)"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: tidytray
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_KB}
Depends: libegl1, libgl1, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libfontconfig1, libdbus-1-3
Maintainer: naOomeow <noreply@github.com>
Homepage: https://github.com/naOomeow/tidytray
Description: Safely organize a cluttered Downloads folder
 Sorts the files directly inside a folder into category folders after you
 review and confirm a plan. Never overwrites or deletes files, and every
 cleanup can be undone. Works offline.
CONTROL
dpkg-deb --build --root-owner-group "$PKG" "dist/tidytray_${VERSION}_${ARCH}.deb"

ls -lh dist/*.tar.gz dist/*.deb
