#!/bin/bash
# ═══════════════════════════════════════════════════════
#  CTpaste — Linux .deb Builder
#  Run this INSIDE your Ubuntu 20.04+ VM/machine.
#  Output: ctpaste_1.0_amd64.deb
# ═══════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/deb_build"
DIST_DIR="$SCRIPT_DIR/dist"
DEB_NAME="ctpaste_1.0_amd64.deb"

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║   CTpaste Linux .deb Builder 🐧      ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 1: Check we're on Linux ─────────────────────
echo -e "[ ${YELLOW}1/6${NC} ] Checking environment..."
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}✗ This script must be run on Linux (Ubuntu 20.04+ recommended).${NC}"
    exit 1
fi

ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    echo -e "${RED}✗ Only x86_64 (64-bit) is supported. Got: $ARCH${NC}"
    exit 1
fi

OS=$(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown Linux")
GLIBC=$(ldd --version | head -1 | grep -oP '\d+\.\d+$')
PYTHON_VER=$(python3 --version 2>/dev/null || echo "none")
echo -e "      OS: ${GREEN}$OS${NC}"
echo -e "      GLIBC: ${GREEN}$GLIBC${NC}"
echo -e "      Python: ${GREEN}$PYTHON_VER${NC}"
echo -e "      ${GREEN}✓ Environment OK${NC}"
echo ""

# ── Step 2: Install system dependencies ──────────────
echo -e "[ ${YELLOW}2/6${NC} ] Installing system dependencies..."

# Remove cdrom source if present (common on fresh VM installs, breaks apt)
sudo sed -i '/^deb cdrom:/d' /etc/apt/sources.list 2>/dev/null || true

# Enable universe repo (needed for xdotool, upx etc.)
sudo add-apt-repository -y universe 2>/dev/null || true

sudo apt-get update -q

# Install packages (with fallback for upx)
sudo apt-get install -y -q python3 python3-pip python3-venv binutils xdotool || {
    echo -e "      ${YELLOW}Trying alternative pip install via get-pip.py...${NC}"
    sudo apt-get install -y -q python3 binutils xdotool curl
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | sudo python3
    sudo apt-get install -y -q python3-venv || python3 -m pip install virtualenv
}

# Install upx (optional, just for compression — skip if missing)
sudo apt-get install -y -q upx-ucl 2>/dev/null || \
sudo apt-get install -y -q upx 2>/dev/null || \
echo -e "      ${YELLOW}⚠ UPX not found — binary won't be compressed but will still work${NC}"

echo -e "      ${GREEN}✓ System dependencies installed${NC}"
echo ""

# ── Step 3: Set up Python virtual environment ────────
echo -e "[ ${YELLOW}3/6${NC} ] Setting up Python virtual environment..."
cd "$SCRIPT_DIR"
if [ -d "venv" ]; then
    echo "      Removing old venv..."
    rm -rf venv
fi
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet \
    pyperclip \
    pynput \
    requests \
    "PyQt6==6.4.2" \
    pymongo \
    pyinstaller
echo -e "      ${GREEN}✓ Virtual environment ready${NC}"
echo ""

# ── Step 4: Build binary with PyInstaller ────────────
echo -e "[ ${YELLOW}4/6${NC} ] Building binary with PyInstaller..."
pyi-makespec \
    --onefile \
    --windowed \
    --name ctpaste \
    --add-data "firebase_config.json:." \
    --collect-all PyQt6 \
    --collect-all pymongo \
    --hidden-import=pynput \
    --hidden-import=pynput.keyboard \
    --hidden-import=pynput.mouse \
    --hidden-import=pyperclip \
    --hidden-import=requests \
    main.py

# Patch the spec file to exclude conflicting system libraries and schemas
python3 -c "
with open('ctpaste.spec', 'r') as f: lines = f.readlines()
with open('ctpaste.spec', 'w') as f:
    for line in lines:
        if 'pyz = PYZ' in line:
            f.write('a.binaries = [x for x in a.binaries if not x[0].startswith(\"libstdc++.so\") and not x[0].startswith(\"libgcc_s.so\")]\n')
            f.write('a.datas = [x for x in a.datas if \"glib-2.0/schemas\" not in x[0]]\n')
        f.write(line)
"

pyinstaller --clean ctpaste.spec

if [ ! -f "$DIST_DIR/ctpaste" ]; then
    echo -e "${RED}✗ Build failed — ctpaste binary not found in dist/${NC}"
    exit 1
fi

chmod +x "$DIST_DIR/ctpaste"
BIN_SIZE=$(du -h "$DIST_DIR/ctpaste" | cut -f1)
echo -e "      ${GREEN}✓ Binary built successfully ($BIN_SIZE)${NC}"
echo ""

# ── Step 5: Package as .deb ──────────────────────────
echo -e "[ ${YELLOW}5/6${NC} ] Creating .deb package..."

# Clean old build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/opt/ctpaste"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/DEBIAN"

# Binary
cp "$DIST_DIR/ctpaste" "$BUILD_DIR/opt/ctpaste/ctpaste"

# Control file
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: ctpaste
Version: 1.0
Architecture: amd64
Maintainer: CTpaste <support@ctpaste.com>
Depends: xdotool, libxcb-cursor0, libgl1, libxcb-xinerama0
Description: CTpaste - Automated clipboard typing tool
 CTpaste lets you paste code into any application by
 simulating keystrokes, bypassing paste restrictions.
 Requires an active session from the CTpaste website.
EOF

# Create /usr/bin symlink so `ctpaste` works in terminal
ln -sf /opt/ctpaste/ctpaste "$BUILD_DIR/usr/bin/ctpaste"

# Postinst script to set permissions
cat > "$BUILD_DIR/DEBIAN/postinst" << EOF
#!/bin/bash
chmod +x /opt/ctpaste/ctpaste
ln -sf /opt/ctpaste/ctpaste /usr/local/bin/ctpaste 2>/dev/null || true
EOF
chmod +x "$BUILD_DIR/DEBIAN/postinst"

# Desktop entry
cat > "$BUILD_DIR/usr/share/applications/ctpaste.desktop" << EOF
[Desktop Entry]
Version=1.0
Name=CTpaste
Comment=Automated clipboard typing tool
Exec=/opt/ctpaste/ctpaste
Icon=utilities-terminal
Type=Application
Categories=Utility;
Terminal=false
StartupNotify=false
EOF

# Build the .deb
dpkg-deb --build "$BUILD_DIR" "$SCRIPT_DIR/$DEB_NAME"

if [ ! -f "$SCRIPT_DIR/$DEB_NAME" ]; then
    echo -e "${RED}✗ .deb creation failed.${NC}"
    exit 1
fi

DEB_SIZE=$(du -h "$SCRIPT_DIR/$DEB_NAME" | cut -f1)
echo -e "      ${GREEN}✓ .deb created ($DEB_SIZE)${NC}"
echo ""

# ── Step 6: Verify ────────────────────────────────────
echo -e "[ ${YELLOW}6/6${NC} ] Verifying package integrity..."
dpkg-deb --info "$SCRIPT_DIR/$DEB_NAME" | grep -E "Package|Version|Architecture|Size"
echo -e "      ${GREEN}✓ Package verified${NC}"
echo ""

# Cleanup
rm -rf "$BUILD_DIR"
deactivate 2>/dev/null || true

echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Build complete!${NC}"
echo -e "${GREEN}  Output: $SCRIPT_DIR/$DEB_NAME${NC}"
echo ""
echo -e "${CYAN}  To install and test locally:${NC}"
echo -e "  sudo dpkg -i $SCRIPT_DIR/$DEB_NAME"
echo -e "  ctpaste"
echo ""
echo -e "${CYAN}  Then copy the .deb to your website folder to deploy.${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
