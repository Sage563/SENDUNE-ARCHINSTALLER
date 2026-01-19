#!/bin/bash
# =============================================
# SENDUNE ISO Builder v3.0.0 (Multi-OS)
# Custom profile - no Arch releng dependency
# =============================================
set -euo pipefail
IFS=$'\n\t'

# ---------- CONFIGURATION ----------
INSTALLER_DIR="${1:-}"
OUTPUT_ISO="${2:-./out-iso/sendune.iso}"
ISO_NAME="${3:-SENDUNE}"
CLEAN="${4:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# ---------- USAGE ----------
usage() {
    cat <<EOF
Usage: $0 <installer_dir> [output_iso] [iso_name] [clean]

Arguments:
    installer_dir   Path to SENDUNE installer directory (required)
    output_iso      Output ISO path (default: ./out-iso/sendune.iso)
    iso_name        ISO volume name (default: SENDUNE)
    clean           Pass 'clean' to force fresh build

Example:
    $0 ./installer ./sendune-custom.iso SENDUNE clean
EOF
    exit 1
}

# ---------- VALIDATE ARGUMENTS ----------
if [ -z "$INSTALLER_DIR" ]; then
    error "Missing required argument: installer_dir"
fi

if [ ! -d "$INSTALLER_DIR" ]; then
    error "Installer directory not found: $INSTALLER_DIR"
fi

# Convert to absolute path
INSTALLER_DIR="$(cd "$INSTALLER_DIR" && pwd)"

# ---------- DETECT OS ----------
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/arch-release ]; then
        echo "arch"
    else
        echo "unknown"
    fi
}

OS_ID=$(detect_os)
info "Detected OS: $OS_ID"

# ---------- DOCKER BUILD FUNCTION ----------
build_with_docker() {
    info "Building SENDUNE ISO using Docker with Arch Linux container..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first:
    Ubuntu/Debian: sudo apt install docker.io
    Fedora: sudo dnf install docker
    Then enable it: sudo systemctl start docker"
    fi

    # Check Docker daemon
    if ! sudo docker info &> /dev/null; then
        error "Docker daemon is not running. Start it with: sudo systemctl start docker"
    fi

    # Prepare directories
    SCRIPT_DIR="$(pwd)"
    OUTPUT_DIR="$(cd "$(dirname "$OUTPUT_ISO")" && pwd)"
    OUTPUT_FILENAME="$(basename "$OUTPUT_ISO")"

    info "Creating Dockerfile..."
    DOCKER_DIR="$SCRIPT_DIR/.docker_build"
    mkdir -p "$DOCKER_DIR"

    cat > "$DOCKER_DIR/Dockerfile" <<'DOCKERFILE'
FROM archlinux:latest

# Update system and install minimal dependencies
RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm \
    base \
    archiso \
    git \
    sudo \
    imagemagick && \
    pacman -Scc --noconfirm

# Create build user and directory
RUN useradd -m -G wheel builder && \
    echo "builder ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    mkdir -p /build && \
    chown -R builder:builder /build

USER builder
WORKDIR /build

CMD ["/bin/bash"]
DOCKERFILE

    info "Building Docker image (this may take a few minutes)..."
    sudo docker build -t sendune-iso-builder "$DOCKER_DIR" || error "Failed to build Docker image"

    info "Creating SENDUNE custom profile..."
    PROFILE_DIR="$DOCKER_DIR/sendune_profile"
    rm -rf "$PROFILE_DIR"
    mkdir -p "$PROFILE_DIR"

    # Create profiledef.sh with updated boot modes
    cat > "$PROFILE_DIR/profiledef.sh" <<EOF
#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="${ISO_NAME,,}"
iso_label="${ISO_NAME^^}"
iso_publisher="SENDUNE <https://sendune.org>"
iso_application="SENDUNE Live/Rescue System"
iso_version="\$(date +%Y.%m.%d)"
install_dir="sendune"
buildmodes=('iso')
bootmodes=('bios.syslinux' 'uefi-x64.systemd-boot.esp' 'uefi-x64.systemd-boot.eltorito')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
bootstrap_tarball_compression=('gzip')
file_permissions=()
EOF

    # Create minimal packages list
    cat > "$PROFILE_DIR/packages.x86_64" <<'EOF'
# Base system
base
linux
linux-firmware

# Boot and firmware
syslinux
efibootmgr
efivar
memtest86+
systemd

# Filesystem tools
dosfstools
e2fsprogs
ntfs-3g
exfatprogs

# Installation tools
arch-install-scripts
pacman

# Networking
dhcpcd
iwd
networkmanager

# Compression
squashfs-tools
xz

# System utilities
sudo
nano
vim
bash-completion

# Hardware detection
pciutils
usbutils
lshw

# Disk utilities
parted
gptfdisk
hdparm

# Additional utilities
wget
curl
rsync
less
man-db
man-pages

# Python for installer
python
python-pip
python-setuptools
python-wheel
EOF

    # Create pacman.conf
    cat > "$PROFILE_DIR/pacman.conf" <<'EOF'
[options]
HoldPkg     = pacman glibc
Architecture = auto
CheckSpace
SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional

[core]
Include = /etc/pacman.d/mirrorlist

[extra]
Include = /etc/pacman.d/mirrorlist
EOF

    # Create airootfs directory structure
    mkdir -p "$PROFILE_DIR/airootfs/etc"
    mkdir -p "$PROFILE_DIR/airootfs/etc/systemd/system"
    mkdir -p "$PROFILE_DIR/airootfs/etc/systemd/network"
    mkdir -p "$PROFILE_DIR/airootfs/root"

    # Create syslinux boot configuration
    mkdir -p "$PROFILE_DIR/syslinux"

    cat > "$PROFILE_DIR/syslinux/syslinux.cfg" <<'EOF'
DEFAULT loadconfig

LABEL loadconfig
  CONFIG archiso.cfg
  APPEND ../../%INSTALL_DIR%/boot/syslinux/
EOF

    cat > "$PROFILE_DIR/syslinux/archiso.cfg" <<'EOF'
SERIAL 0 115200
UI vesamenu.c32
MENU TITLE SENDUNE Live Environment

MENU WIDTH 78
MENU MARGIN 4
MENU ROWS 7
MENU VSHIFT 10
MENU TIMEOUTROW 13
MENU TABMSGROW 14
MENU CMDLINEROW 14
MENU HELPMSGROW 16
MENU HELPMSGENDROW 29

MENU COLOR border       30;44   #40ffffff #a0000000 std
MENU COLOR title        1;36;44 #9033ccff #a0000000 std
MENU COLOR sel          7;37;40 #e0ffffff #20ffffff all
MENU COLOR unsel        37;44   #50ffffff #a0000000 std
MENU COLOR help         37;40   #c0ffffff #a0000000 std
MENU COLOR timeout_msg  37;40   #80ffffff #00000000 std
MENU COLOR timeout      1;37;40 #c0ffffff #00000000 std
MENU COLOR msg07        37;40   #90ffffff #a0000000 std
MENU COLOR tabmsg       31;40   #30ffffff #00000000 std

TIMEOUT 150
ONTIMEOUT sendune

LABEL sendune
TEXT HELP
Boot the SENDUNE live environment.
ENDTEXT
MENU LABEL SENDUNE (x86_64)
LINUX /%INSTALL_DIR%/boot/x86_64/vmlinuz-linux
INITRD /%INSTALL_DIR%/boot/x86_64/initramfs-linux.img
APPEND archisobasedir=%INSTALL_DIR% archisolabel=%ARCHISO_LABEL%

LABEL sendune-nomodeset
TEXT HELP
Boot with nomodeset for compatibility.
ENDTEXT
MENU LABEL SENDUNE (nomodeset)
LINUX /%INSTALL_DIR%/boot/x86_64/vmlinuz-linux
INITRD /%INSTALL_DIR%/boot/x86_64/initramfs-linux.img
APPEND archisobasedir=%INSTALL_DIR% archisolabel=%ARCHISO_LABEL% nomodeset

LABEL memtest
MENU LABEL Memory Test (memtest86+)
LINUX /%INSTALL_DIR%/boot/memtest86+/memtest.bin
EOF

    # Create efiboot configuration
    mkdir -p "$PROFILE_DIR/efiboot/loader/entries"

    cat > "$PROFILE_DIR/efiboot/loader/loader.conf" <<'EOF'
timeout 15
default sendune.conf
EOF

    cat > "$PROFILE_DIR/efiboot/loader/entries/sendune.conf" <<'EOF'
title   SENDUNE Live Environment
linux   /%INSTALL_DIR%/boot/x86_64/vmlinuz-linux
initrd  /%INSTALL_DIR%/boot/x86_64/initramfs-linux.img
options archisobasedir=%INSTALL_DIR% archisolabel=%ARCHISO_LABEL%
EOF

    cat > "$PROFILE_DIR/efiboot/loader/entries/sendune-nomodeset.conf" <<'EOF'
title   SENDUNE (nomodeset)
linux   /%INSTALL_DIR%/boot/x86_64/vmlinuz-linux
initrd  /%INSTALL_DIR%/boot/x86_64/initramfs-linux.img
options archisobasedir=%INSTALL_DIR% archisolabel=%ARCHISO_LABEL% nomodeset
EOF

    # Remove old motd
    rm -f "$PROFILE_DIR/airootfs/etc/motd"

    # Create hostname
    echo "sendune" > "$PROFILE_DIR/airootfs/etc/hostname"

    # Create hosts file
    cat > "$PROFILE_DIR/airootfs/etc/hosts" <<'EOF'
127.0.0.1   localhost
::1         localhost
127.0.1.1   sendune.localdomain sendune
EOF

    # Create locale.gen
    cat > "$PROFILE_DIR/airootfs/etc/locale.gen" <<'EOF'
en_US.UTF-8 UTF-8
EOF

    # Create locale.conf
    cat > "$PROFILE_DIR/airootfs/etc/locale.conf" <<'EOF'
LANG=en_US.UTF-8
EOF

    # Create vconsole.conf
    cat > "$PROFILE_DIR/airootfs/etc/vconsole.conf" <<'EOF'
KEYMAP=us
EOF

    # Enable NetworkManager
    mkdir -p "$PROFILE_DIR/airootfs/etc/systemd/system/multi-user.target.wants"
    ln -sf /usr/lib/systemd/system/NetworkManager.service \
        "$PROFILE_DIR/airootfs/etc/systemd/system/multi-user.target.wants/NetworkManager.service"

    # Enable dhcpcd
    ln -sf /usr/lib/systemd/system/dhcpcd.service \
        "$PROFILE_DIR/airootfs/etc/systemd/system/multi-user.target.wants/dhcpcd.service"

    # Create welcome message
    cat > "$PROFILE_DIR/airootfs/etc/motd" <<'EOF'

███████╗███████╗███╗   ███╗██████╗ ██╗   ██╗███╗   ██╗███████╗
██╔════╝██╔════╝████╗ ████║██╔══██╗██║   ██║████╗  ██║██╔════╝
███████╗█████╗  ██╔████╔██║██║  ██║██║   ██║██╔██╗ ██║█████╗
╚════██║██╔══╝  ██║╚██╔╝██║██║  ██║██║   ██║██║╚██╗██║██╔══╝
███████║███████╗██║ ╚═╝ ██║██████╔╝╚██████╔╝██║ ╚████║███████╗
╚══════╝╚══════╝╚═╝     ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝

Welcome to SENDUNE Live Environment!

Installer location: /root/SENDUNE_installer
To install SENDUNE: cd /root/SENDUNE_installer && ./install.sh

EOF

    # Create auto-login and installer launcher
    cat > "$PROFILE_DIR/airootfs/root/.bash_profile" <<'EOF'
#!/bin/bash

# Run only in interactive shells
[[ $- != *i* ]] && return

# Clear screen and show welcome
clear
cat << 'WELCOME'

███████╗███████╗███╗   ███╗██████╗ ██╗   ██╗███╗   ██╗███████╗
██╔════╝██╔════╝████╗ ████║██╔══██╗██║   ██║████╗  ██║██╔════╝
███████╗█████╗  ██╔████╔██║██║  ██║██║   ██║██╔██╗ ██║█████╗
╚════██║██╔══╝  ██║╚██╔╝██║██║  ██║██║   ██║██║╚██╗██║██╔══╝
███████║███████╗██║ ╚═╝ ██║██████╔╝╚██████╔╝██║ ╚████║███████╗
╚══════╝╚══════╝╚═╝     ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝

WELCOME

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Welcome to SENDUNE Live Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  To install SENDUNE, run:"
echo ""
echo "    sendune-installer"
echo ""
echo "  Or manually:"
echo "    cd /root/SENDUNE_installer && python -m SENDUNE_installer"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
EOF
    chmod +x "$PROFILE_DIR/airootfs/root/.bash_profile"

    # Create build script
    cat > "$DOCKER_DIR/build_in_container.sh" <<'BUILDSCRIPT'
#!/bin/bash
set -euo pipefail

echo "════════════════════════════════════════════════════"
echo "  SENDUNE ISO Builder - Container Build Process"
echo "════════════════════════════════════════════════════"
echo ""

# Copy profile to work location
echo "[1/6] Preparing build environment..."
cp -r /build/profile /build/sendune_profile
chmod +x /build/sendune_profile/profiledef.sh

# Inject installer
echo "[2/6] Injecting SENDUNE installer..."
cp -r /build/installer /build/sendune_profile/airootfs/root/SENDUNE_installer
find /build/sendune_profile/airootfs/root/SENDUNE_installer -type f -name "*.sh" -exec chmod +x {} \;

# Build Python wheel if setup.py or pyproject.toml exists
echo "[2.1/6] Building SENDUNE installer as Python package..."
if [ -f /build/sendune_profile/airootfs/root/SENDUNE_installer/setup.py ] || \
   [ -f /build/sendune_profile/airootfs/root/SENDUNE_installer/pyproject.toml ]; then

    cd /build/sendune_profile/airootfs/root/SENDUNE_installer

    # Build wheel
    echo "  → Building Python wheel package..."
    python -m pip install --upgrade pip wheel setuptools 2>/dev/null || true
    python -m pip wheel . --no-deps -w /tmp/sendune_wheels 2>/dev/null || {
        echo "  ⚠ Wheel build failed, will install from source"
    }

    # Create installer script that will be available in PATH
    echo "  → Creating sendune-installer command..."
    mkdir -p /build/sendune_profile/airootfs/usr/local/bin
    cat > /build/sendune_profile/airootfs/usr/local/bin/sendune-installer <<'INSTALLER_SCRIPT'
#!/bin/bash
# SENDUNE Installer Wrapper
cd /root/SENDUNE_installer

# Try to install from wheel first, then fallback to source
if [ -d /tmp/sendune_wheels ] && [ -n "$(ls -A /tmp/sendune_wheels/*.whl 2>/dev/null)" ]; then
    echo "Installing SENDUNE from wheel package..."
    pip install --user /tmp/sendune_wheels/*.whl 2>/dev/null || {
        echo "Wheel installation failed, running from source..."
        python -m SENDUNE_installer "$@"
        exit $?
    }
    # Run the installed command
    sendune-runner "$@"
else
    # Run from source
    python -m SENDUNE_installer "$@"
fi
INSTALLER_SCRIPT
    chmod +x /build/sendune_profile/airootfs/usr/local/bin/sendune-installer
    echo "  ✓ sendune-installer command created"

    cd /build
else
    echo "  ⚠ No setup.py or pyproject.toml found, creating simple launcher..."
    mkdir -p /build/sendune_profile/airootfs/usr/local/bin
    cat > /build/sendune_profile/airootfs/usr/local/bin/sendune-installer <<'SIMPLE_SCRIPT'
#!/bin/bash
cd /root/SENDUNE_installer && python -m SENDUNE_installer "$@"
SIMPLE_SCRIPT
    chmod +x /build/sendune_profile/airootfs/usr/local/bin/sendune-installer
fi

# Copy splash image if exists
WALLPAPER_PATH="/build/sendune_profile/airootfs/root/SENDUNE_installer/assets/sendune_wallpaper.png"
if [ -f "$WALLPAPER_PATH" ]; then
    echo "  → Copying SENDUNE splash image for boot menu..."
    mkdir -p /build/sendune_profile/syslinux

    # Convert PNG to proper format and resolution for syslinux (640x480, 16 colors)
    if command -v convert &> /dev/null; then
        echo "  → Converting image to syslinux format (640x480, 16 colors)..."
        convert "$WALLPAPER_PATH" -resize 640x480 -colors 16 /build/sendune_profile/syslinux/splash.png 2>/dev/null || {
            echo "  ⚠ Conversion failed, copying original..."
            cp "$WALLPAPER_PATH" /build/sendune_profile/syslinux/splash.png
        }
    else
        echo "  ⚠ ImageMagick not found, copying original image..."
        cp "$WALLPAPER_PATH" /build/sendune_profile/syslinux/splash.png
    fi

    # Verify splash image was created
    if [ -f /build/sendune_profile/syslinux/splash.png ]; then
        echo "  ✓ Splash image ready: $(du -h /build/sendune_profile/syslinux/splash.png | cut -f1)"
        # Add background to syslinux config
        sed -i '/MENU TITLE SENDUNE Live Environment/a MENU BACKGROUND splash.png' /build/sendune_profile/syslinux/archiso.cfg
    else
        echo "  ✗ Failed to create splash.png"
    fi
else
    echo "  ⚠ Warning: sendune_wallpaper.png not found at $WALLPAPER_PATH"
    echo "  → Boot menu will use default styling"
fi

# Validate profile
echo "[3/6] Validating profile structure..."
ls -la /build/sendune_profile/

# Create work directory with proper permissions
echo "[4/6] Creating work directories..."
sudo mkdir -p /build/work /build/output
sudo chown -R builder:builder /build/work /build/output

# Build ISO
echo "[5/6] Building ISO with mkarchiso..."
echo "This may take 5-15 minutes depending on your system..."
sudo mkarchiso -v -w /build/work -o /build/output /build/sendune_profile

# Fix permissions
echo "[6/6] Finalizing..."
sudo chown -R builder:builder /build/output

echo ""
echo "════════════════════════════════════════════════════"
echo "  Build Complete!"
echo "════════════════════════════════════════════════════"
ls -lh /build/output/*.iso 2>/dev/null || find /build/output -name "*.iso" -exec ls -lh {} \;
BUILDSCRIPT

    chmod +x "$DOCKER_DIR/build_in_container.sh"

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    info "Running build in Docker container..."
    info "This will download packages and build the ISO (may take 10-20 minutes)..."

    sudo docker run --rm \
        --privileged \
        -v "$INSTALLER_DIR:/build/installer:ro" \
        -v "$PROFILE_DIR:/build/profile:ro" \
        -v "$DOCKER_DIR/build_in_container.sh:/build/build.sh:ro" \
        -v "$OUTPUT_DIR:/build/output" \
        sendune-iso-builder \
        bash /build/build.sh \
        || error "Docker build failed"

    # Find and rename output ISO
    info "Locating built ISO file..."

    # Fix permissions on output directory
    sudo chown -R $USER:$USER "$OUTPUT_DIR" 2>/dev/null || true

    BUILT_ISO=$(find "$OUTPUT_DIR" -name "*.iso" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)

    if [ -n "$BUILT_ISO" ] && [ -f "$BUILT_ISO" ]; then
        if [ "$BUILT_ISO" != "$OUTPUT_DIR/$OUTPUT_FILENAME" ]; then
            mv "$BUILT_ISO" "$OUTPUT_DIR/$OUTPUT_FILENAME"
        fi
        success "ISO successfully built at: $OUTPUT_DIR/$OUTPUT_FILENAME"
        info "ISO size: $(du -h "$OUTPUT_DIR/$OUTPUT_FILENAME" | cut -f1)"
        echo ""
        info "Next steps:"
        info "  1. Test with: qemu-system-x86_64 -cdrom $OUTPUT_DIR/$OUTPUT_FILENAME -m 2048"
        info "  2. Write to USB: sudo dd if=$OUTPUT_DIR/$OUTPUT_FILENAME of=/dev/sdX bs=4M status=progress"
        info "  3. Or use Ventoy, Rufus, or Etcher to create bootable USB"
    else
        error "ISO file not found after build"
    fi

    # Cleanup
    if [ -n "$CLEAN" ]; then
        info "Cleaning up Docker build directory..."
        rm -rf "$DOCKER_DIR"
    fi
}

# ---------- NATIVE ARCH BUILD FUNCTION ----------
build_native_arch() {
    info "Building SENDUNE ISO natively on Arch Linux..."

    # Install dependencies
    info "Installing dependencies..."
    sudo pacman -Syu --needed --noconfirm archiso git imagemagick || error "Failed to install dependencies"

    # Prepare directories
    PROFILE_DIR="$(pwd)/sendune_profile"
    OUTPUT_DIR="$(dirname "$OUTPUT_ISO")"
    WORK_DIR="$(pwd)/work"

    mkdir -p "$OUTPUT_DIR"

    # Clean if requested
    if [ -n "$CLEAN" ]; then
        info "Cleaning existing work directories..."
        rm -rf "$PROFILE_DIR" "$WORK_DIR"
    fi

    info "Creating SENDUNE custom profile..."
    rm -rf "$PROFILE_DIR"
    mkdir -p "$PROFILE_DIR"

    # Create profiledef.sh with updated boot modes
    cat > "$PROFILE_DIR/profiledef.sh" <<EOF
#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="${ISO_NAME,,}"
iso_label="${ISO_NAME^^}"
iso_publisher="SENDUNE <https://sendune.org>"
iso_application="SENDUNE Live/Rescue System"
iso_version="\$(date +%Y.%m.%d)"
install_dir="sendune"
buildmodes=('iso')
bootmodes=('bios.syslinux' 'uefi-x64.systemd-boot.esp' 'uefi-x64.systemd-boot.eltorito')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
bootstrap_tarball_compression=('gzip')
file_permissions=()
EOF

    # Create minimal packages list
    cat > "$PROFILE_DIR/packages.x86_64" <<'EOF'
base
linux
linux-firmware
syslinux
efibootmgr
efivar
memtest86+
systemd
dosfstools
e2fsprogs
ntfs-3g
exfatprogs
arch-install-scripts
pacman
dhcpcd
iwd
networkmanager
squashfs-tools
xz
sudo
nano
vim
bash-completion
pciutils
usbutils
lshw
parted
gptfdisk
hdparm
wget
curl
rsync
less
man-db
man-pages
python
python-pip
python-setuptools
python-wheel
EOF

    # Create pacman.conf
    cat > "$PROFILE_DIR/pacman.conf" <<'EOF'
[options]
HoldPkg     = pacman glibc
Architecture = auto
CheckSpace
SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional

[core]
Include = /etc/pacman.d/mirrorlist

[extra]
Include = /etc/pacman.d/mirrorlist
EOF

    # Create airootfs directory structure
    mkdir -p "$PROFILE_DIR/airootfs/etc"
    mkdir -p "$PROFILE_DIR/airootfs/etc/systemd/system/multi-user.target.wants"
    mkdir -p "$PROFILE_DIR/airootfs/root"

    # Create syslinux boot configuration
    mkdir -p "$PROFILE_DIR/syslinux"

    cat > "$PROFILE_DIR/syslinux/syslinux.cfg" <<'EOF'
DEFAULT loadconfig

LABEL loadconfig
  CONFIG archiso.cfg
  APPEND ../../%INSTALL_DIR%/boot/syslinux/
EOF

    cat > "$PROFILE_DIR/syslinux/archiso.cfg" <<'EOF'
SERIAL 0 115200
UI vesamenu.c32
MENU TITLE SENDUNE Live Environment

MENU WIDTH 78
MENU MARGIN 4
MENU ROWS 7
MENU VSHIFT 10
MENU TIMEOUTROW 13
MENU TABMSGROW 14
MENU CMDLINEROW 14
MENU HELPMSGROW 16
MENU HELPMSGENDROW 29

MENU COLOR border       30;44   #40ffffff #a0000000 std
MENU COLOR title        1;36;44 #9033ccff #a0000000 std
MENU COLOR sel          7;37;40 #e0ffffff #20ffffff all
MENU COLOR unsel        37;44   #50ffffff #a0000000 std
MENU COLOR help         37;40   #c0ffffff #a0000000 std
MENU COLOR timeout_msg  37;40   #80ffffff #00000000 std
MENU COLOR timeout      1;37;40 #c0ffffff #00000000 std
MENU COLOR msg07        37;40   #90ffffff #a0000000 std
MENU COLOR tabmsg       31;40   #30ffffff #00000000 std

TIMEOUT 150
ONTIMEOUT sendune

LABEL sendune
TEXT HELP
Boot the SENDUNE live environment.
ENDTEXT
MENU LABEL SENDUNE (x86_64)
LINUX /%INSTALL_DIR%/boot/x86_64/vmlinuz-linux
INITRD /%INSTALL_DIR%/boot/x86_64/initramfs-linux.img
APPEND archisobasedir=%INSTALL_DIR% archisolabel=%ARCHISO_LABEL%

LABEL sendune-nomodeset
TEXT HELP
Boot with nomodeset for compatibility.
ENDTEXT
MENU LABEL SENDUNE (nomodeset)
LINUX /%INSTALL_DIR%/boot/x86_64/vmlinuz-linux
INITRD /%INSTALL_DIR%/boot/x86_64/initramfs-linux.img
APPEND archisobasedir=%INSTALL_DIR% archisolabel=%ARCHISO_LABEL% nomodeset

LABEL memtest
MENU LABEL Memory Test (memtest86+)
LINUX /%INSTALL_DIR%/boot/memtest86+/memtest.bin
EOF

    # Create efiboot configuration
    mkdir -p "$PROFILE_DIR/efiboot/loader/entries"

    cat > "$PROFILE_DIR/efiboot/loader/loader.conf" <<'EOF'
timeout 15
default sendune.conf
EOF

    cat > "$PROFILE_DIR/efiboot/loader/entries/sendune.conf" <<'EOF'
title   SENDUNE Live Environment (x86_64, UEFI)
linux   /%INSTALL_DIR%/boot/x86_64/vmlinuz-linux
initrd  /%INSTALL_DIR%/boot/x86_64/initramfs-linux.img
options archisobasedir=%INSTALL_DIR% archisolabel=%ARCHISO_LABEL%
EOF

    cat > "$PROFILE_DIR/efiboot/loader/entries/sendune-nomodeset.conf" <<'EOF'
title   SENDUNE (nomodeset, UEFI)
linux   /%INSTALL_DIR%/boot/x86_64/vmlinuz-linux
initrd  /%INSTALL_DIR%/boot/x86_64/initramfs-linux.img
options archisobasedir=%INSTALL_DIR% archisolabel=%ARCHISO_LABEL% nomodeset
EOF

    echo "sendune" > "$PROFILE_DIR/airootfs/etc/hostname"

    cat > "$PROFILE_DIR/airootfs/etc/hosts" <<'EOF'
127.0.0.1   localhost
::1         localhost
127.0.1.1   sendune.localdomain sendune
EOF

    cat > "$PROFILE_DIR/airootfs/etc/locale.gen" <<'EOF'
en_US.UTF-8 UTF-8
EOF

    cat > "$PROFILE_DIR/airootfs/etc/locale.conf" <<'EOF'
LANG=en_US.UTF-8
EOF

    cat > "$PROFILE_DIR/airootfs/etc/vconsole.conf" <<'EOF'
KEYMAP=us
EOF

    ln -sf /usr/lib/systemd/system/NetworkManager.service \
        "$PROFILE_DIR/airootfs/etc/systemd/system/multi-user.target.wants/NetworkManager.service"
    ln -sf /usr/lib/systemd/system/dhcpcd.service \
        "$PROFILE_DIR/airootfs/etc/systemd/system/multi-user.target.wants/dhcpcd.service"

    # Create bash profile for welcome message
    cat > "$PROFILE_DIR/airootfs/root/.bash_profile" <<'EOF'
#!/bin/bash

# Run only in interactive shells
[[ $- != *i* ]] && return

# Clear screen and show welcome
clear
cat << 'WELCOME'

███████╗███████╗███╗   ███╗██████╗ ██╗   ██╗███╗   ██╗███████╗
██╔════╝██╔════╝████╗ ████║██╔══██╗██║   ██║████╗  ██║██╔════╝
███████╗█████╗  ██╔████╔██║██║  ██║██║   ██║██╔██╗ ██║█████╗
╚════██║██╔══╝  ██║╚██╔╝██║██║  ██║██║   ██║██║╚██╗██║██╔══╝
███████║███████╗██║ ╚═╝ ██║██████╔╝╚██████╔╝██║ ╚████║███████╗
╚══════╝╚══════╝╚═╝     ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝

WELCOME

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Welcome to SENDUNE Live Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  To install SENDUNE, run:"
echo ""
echo "    sendune-installer"
echo ""
echo "  Or manually:"
echo "    cd /root/SENDUNE_installer && python -m SENDUNE_installer"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
EOF
    chmod +x "$PROFILE_DIR/airootfs/root/.bash_profile"

    # Inject installer
    info "Injecting SENDUNE installer..."
    cp -r "$INSTALLER_DIR" "$PROFILE_DIR/airootfs/root/SENDUNE_installer"
    find "$PROFILE_DIR/airootfs/root/SENDUNE_installer" -type f -name "*.sh" -exec chmod +x {} \;

    # Build Python wheel if setup.py or pyproject.toml exists
    info "Setting up SENDUNE installer package..."
    if [ -f "$INSTALLER_DIR/setup.py" ] || [ -f "$INSTALLER_DIR/pyproject.toml" ]; then
        info "Building Python wheel package..."

        # Build wheel in temporary directory
        WHEEL_DIR=$(mktemp -d)
        cd "$INSTALLER_DIR"
        python -m pip install --upgrade pip wheel setuptools 2>/dev/null || true
        if python -m pip wheel . --no-deps -w "$WHEEL_DIR" 2>/dev/null; then
            # Copy wheel to ISO
            mkdir -p "$PROFILE_DIR/airootfs/tmp/sendune_wheels"
            cp "$WHEEL_DIR"/*.whl "$PROFILE_DIR/airootfs/tmp/sendune_wheels/" 2>/dev/null || true
            success "Wheel package built successfully"
        else
            warn "Wheel build failed, will install from source"
        fi
        rm -rf "$WHEEL_DIR"
        cd - >/dev/null
    fi

    # Create installer launcher script
    info "Creating sendune-installer command..."
    mkdir -p "$PROFILE_DIR/airootfs/usr/local/bin"

    if [ -f "$INSTALLER_DIR/setup.py" ] || [ -f "$INSTALLER_DIR/pyproject.toml" ]; then
        cat > "$PROFILE_DIR/airootfs/usr/local/bin/sendune-installer" <<'INSTALLER_SCRIPT'
#!/bin/bash
# SENDUNE Installer Wrapper
cd /root/SENDUNE_installer

# Try to install from wheel first, then fallback to source
if [ -d /tmp/sendune_wheels ] && [ -n "$(ls -A /tmp/sendune_wheels/*.whl 2>/dev/null)" ]; then
    echo "Installing SENDUNE from wheel package..."
    pip install --user /tmp/sendune_wheels/*.whl 2>/dev/null || {
        echo "Wheel installation failed, running from source..."
        python -m SENDUNE_installer "$@"
        exit $?
    }
    # Run the installed command
    sendune-runner "$@"
else
    # Run from source
    python -m SENDUNE_installer "$@"
fi
INSTALLER_SCRIPT
    else
        cat > "$PROFILE_DIR/airootfs/usr/local/bin/sendune-installer" <<'SIMPLE_SCRIPT'
#!/bin/bash
cd /root/SENDUNE_installer && python -m SENDUNE_installer "$@"
SIMPLE_SCRIPT
    fi

    chmod +x "$PROFILE_DIR/airootfs/usr/local/bin/sendune-installer"
    success "sendune-installer command created"

    # Copy and process splash image from installer directory in live environment
    WALLPAPER_PATH="$PROFILE_DIR/airootfs/root/SENDUNE_installer/assets/sendune_wallpaper.png"
    if [ -f "$WALLPAPER_PATH" ]; then
        info "Processing SENDUNE splash image for boot menu..."
        mkdir -p "$PROFILE_DIR/syslinux"

        # Check if ImageMagick is available
        if command -v convert &> /dev/null; then
            info "Converting image to syslinux format (640x480, 16 colors)..."
            if convert "$WALLPAPER_PATH" -resize 640x480 -colors 16 "$PROFILE_DIR/syslinux/splash.png" 2>/dev/null; then
                success "Image converted successfully"
            else
                warn "Conversion failed, copying original image"
                cp "$WALLPAPER_PATH" "$PROFILE_DIR/syslinux/splash.png"
            fi
        else
            warn "ImageMagick not found, copying image without conversion"
            cp "$WALLPAPER_PATH" "$PROFILE_DIR/syslinux/splash.png"
        fi

        # Verify splash image was created
        if [ -f "$PROFILE_DIR/syslinux/splash.png" ]; then
            local size=$(du -h "$PROFILE_DIR/syslinux/splash.png" | cut -f1)
            success "Splash image ready: $size"
            # Add background to syslinux config
            sed -i '/MENU TITLE SENDUNE Live Environment/a MENU BACKGROUND splash.png' \
                "$PROFILE_DIR/syslinux/archiso.cfg"
        else
            error "Failed to create splash.png"
        fi
    else
        warn "sendune_wallpaper.png not found at: $WALLPAPER_PATH"
        info "Boot menu will use default styling"
        info "Make sure the file exists at: $INSTALLER_DIR/assets/sendune_wallpaper.png"
    fi

    # Build ISO
    info "Building ISO with mkarchiso..."
    sudo mkarchiso -v -w "$WORK_DIR" -o "$OUTPUT_DIR" "$PROFILE_DIR" \
        || error "mkarchiso failed"

    # Find and rename output ISO
    BUILT_ISO=$(find "$OUTPUT_DIR" -name "*.iso" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)

    if [ -n "$BUILT_ISO" ] && [ -f "$BUILT_ISO" ]; then
        if [ "$BUILT_ISO" != "$OUTPUT_ISO" ]; then
            mv "$BUILT_ISO" "$OUTPUT_ISO"
        fi
        success "ISO successfully built at: $OUTPUT_ISO"
        info "ISO size: $(du -h "$OUTPUT_ISO" | cut -f1)"
    else
        error "ISO file not found after build"
    fi

    # Cleanup
    if [ -n "$CLEAN" ]; then
        info "Cleaning up work directories..."
        rm -rf "$PROFILE_DIR" "$WORK_DIR"
    fi
}

# ---------- MAIN EXECUTION ----------
case "$OS_ID" in
    arch|manjaro|endeavouros)
        info "Running native Arch Linux build..."
        build_native_arch
        ;;
    ubuntu|debian|fedora|centos|rhel|opensuse|*)
        warn "Non-Arch Linux system detected. Using Docker for build..."
        build_with_docker
        ;;
esac

success "Build complete! 🎉"
success "Your SENDUNE ISO is ready to use!"
