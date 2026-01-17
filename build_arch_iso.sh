#!/usr/bin/env bash
set -e

# =========================================================
# SENDUNE Arch ISO Builder
# Builds a custom Arch Linux ISO with SENDUNE installer
# =========================================================

# ---------- Colors ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------- Logging ----------
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
}

success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

# ---------- OS Check ----------
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "This script must be run on Linux."
    exit 1
fi

# ---------- Dependency Check ----------
check_dependencies() {
    local deps=("rsync" "sudo" "mount" "umount" "xorriso" "chroot")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            error "Required tool '$dep' not found."
            exit 1
        fi
    done
    log "All dependencies found."
}

# ---------- Usage ----------
usage() {
    echo "Usage: $0 <SOURCE_ISO> <SENDUNE_DIR> <OUTPUT_ISO> [WORK_DIR]"
    echo
    echo "Arguments:"
    echo "  SOURCE_ISO   Path to the original Arch Linux ISO"
    echo "  SENDUNE_DIR  Path to the SENDUNE installer directory"
    echo "  OUTPUT_ISO   Path for the output custom ISO"
    echo "  WORK_DIR     Working directory (default: ./iso_work)"
    echo
    echo "Example:"
    echo "  $0 archlinux-x86_64.iso ./SENDUNE_installer ./SENDUNE_Arch.iso"
    exit 1
}

# ---------- Config ----------
SOURCE_ISO="$1"
SENDUNE_DIR="$2"
OUTPUT_ISO="$3"
WORK_DIR="${4:-./iso_work}"

# ---------- Validate Arguments ----------
[[ $# -lt 3 ]] && usage

[[ ! -f "$SOURCE_ISO" ]] && error "Source ISO not found." && exit 1
[[ ! -d "$SENDUNE_DIR" ]] && error "SENDUNE directory not found." && exit 1

check_dependencies

log "Starting SENDUNE ISO build"
log "Source ISO : $SOURCE_ISO"
log "SENDUNE Dir: $SENDUNE_DIR"
log "Output ISO : $OUTPUT_ISO"
log "Work Dir   : $WORK_DIR"

# ---------- Prepare Directories ----------
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR/mnt" "$WORK_DIR/extract"

cleanup() {
    log "Cleaning up..."
    sudo umount "$WORK_DIR/mnt" 2>/dev/null || true
    for fs in dev sys proc run; do
        sudo umount "$WORK_DIR/extract/$fs" 2>/dev/null || true
    done
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

# ---------- Mount ISO ----------
log "Mounting ISO..."
sudo mount -o loop "$SOURCE_ISO" "$WORK_DIR/mnt"

# ---------- Copy ISO ----------
log "Copying ISO contents..."
rsync -a --exclude=archinstall/SENDUNE_installer \
    "$WORK_DIR/mnt/" "$WORK_DIR/extract/"

# ---------- Add SENDUNE ----------
log "Adding SENDUNE installer..."
mkdir -p "$WORK_DIR/extract/archinstall"
cp -r "$SENDUNE_DIR" "$WORK_DIR/extract/archinstall/"

# ---------- Clone Archinstall ----------
if command -v git >/dev/null 2>&1; then
    log "Cloning archinstall source..."
    git clone https://github.com/archlinux/archinstall.git \
        "$WORK_DIR/extract/root/archinstall-git" || true
fi

# ---------- Prepare Chroot ----------
log "Preparing chroot environment..."
for fs in dev sys proc run; do
    sudo mount --bind "/$fs" "$WORK_DIR/extract/$fs" || true
done
sudo cp -L /etc/resolv.conf "$WORK_DIR/extract/etc/resolv.conf" || true

# ---------- Archinstall Installer Script ----------
cat > "$WORK_DIR/extract/tmp/sendune_install_archinstall.sh" <<'EOF'
#!/usr/bin/env bash
set -e

echo "[sendune] Installing archinstall (best-effort)"

if command -v pacman >/dev/null; then
    pacman -Sy --noconfirm python python-pip git base-devel || true
    pacman -Sy --noconfirm archinstall || true
fi

if command -v pip3 >/dev/null; then
    pip3 install --upgrade pip setuptools wheel || true
    pip3 install archinstall pydantic || true
fi
EOF

chmod +x "$WORK_DIR/extract/tmp/sendune_install_archinstall.sh"

if command -v arch-chroot >/dev/null 2>&1; then
    sudo arch-chroot "$WORK_DIR/extract" /tmp/sendune_install_archinstall.sh || true
else
    sudo chroot "$WORK_DIR/extract" /bin/bash /tmp/sendune_install_archinstall.sh || true
fi

# ---------- Cleanup Chroot ----------
for fs in dev sys proc run; do
    sudo umount "$WORK_DIR/extract/$fs" || true
done
rm -f "$WORK_DIR/extract/tmp/sendune_install_archinstall.sh"

# ---------- Unmount ISO ----------
sudo umount "$WORK_DIR/mnt"

# ---------- Build ISO ----------
log "Repacking ISO..."
cd "$WORK_DIR/extract"

xorriso -as mkisofs \
    -iso-level 3 \
    -full-iso9660-filenames \
    -volid "SENDUNE_ARCH" \
    -output "$OUTPUT_ISO" \
    -eltorito-boot isolinux/isolinux.bin \
    -eltorito-catalog isolinux/boot.cat \
    -no-emul-boot -boot-load-size 4 -boot-info-table \
    -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
    -eltorito-alt-boot \
    -e EFI/archiso/efiboot.img -no-emul-boot \
    .

success "ISO created at $OUTPUT_ISO"

echo
echo "=== Next Steps ==="
echo "1. Boot the ISO"
echo "2. Run: python3 -m SENDUNE_installer"
echo
