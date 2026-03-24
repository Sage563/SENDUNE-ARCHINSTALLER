#!/usr/bin/env bash
# =============================================
# SENDUNE ISO Builder
# Supports native Arch builds and Docker-based builds for WSL/other distros.
# AND THIS does require Internet connection to pull packages and dependencies during the build process.
# =============================================
set -euo pipefail
IFS=$'\n\t'

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ROOT="${SCRIPT_DIR}/.build-archiso"
PROFILE_DIR="${BUILD_ROOT}/profile"
WORK_DIR="${BUILD_ROOT}/work"

INSTALLER_DIR=""
OUTPUT_ISO="${SCRIPT_DIR}/out-iso/SENDUNE.iso"
ISO_NAME="SENDUNE"
CLEAN=0
VERBOSE=0

usage() {
    cat <<'EOF'
Usage:
  ./build_arch_iso.sh <installer_dir> [options]

Options:
  -o, --output FILE   Output ISO path (default: ./out-iso/SENDUNE.iso)
  -n, --name NAME     ISO name/label (default: SENDUNE)
  -c, --clean         Remove previous build artifacts before building
  -v, --verbose       Enable verbose mkarchiso output
  -h, --help          Show this help message

Examples:
  ./build_arch_iso.sh SENDUNE_installer
  ./build_arch_iso.sh SENDUNE_installer -o ~/Downloads/sendune.iso
  ./build_arch_iso.sh SENDUNE_installer -n MyDistro --clean
EOF
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        printf '%s' "${ID:-unknown}"
        return
    fi
    if [[ -f /etc/arch-release ]]; then
        printf '%s' "arch"
        return
    fi
    printf '%s' "unknown"
}

is_wsl() {
    grep -qi microsoft /proc/version 2>/dev/null
}

abs_path() {
    local target="$1"
    local parent
    mkdir -p "$(dirname "$target")"
    parent="$(cd "$(dirname "$target")" && pwd)"
    printf '%s/%s\n' "$parent" "$(basename "$target")"
}

docker_cmd() {
    if docker info >/dev/null 2>&1; then
        printf '%s\n' "docker"
        return
    fi
    if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
        printf '%s\n' "sudo docker"
        return
    fi
    return 1
}

parse_args() {
    [[ $# -gt 0 ]] || {
        usage
        exit 1
    }

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -o|--output)
                [[ $# -ge 2 ]] || error "Missing value for $1"
                OUTPUT_ISO="$2"
                shift 2
                ;;
            -n|--name)
                [[ $# -ge 2 ]] || error "Missing value for $1"
                ISO_NAME="$2"
                shift 2
                ;;
            -c|--clean)
                CLEAN=1
                shift
                ;;
            -v|--verbose)
                VERBOSE=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            --)
                shift
                break
                ;;
            -*)
                error "Unknown option: $1"
                ;;
            *)
                if [[ -z "$INSTALLER_DIR" ]]; then
                    INSTALLER_DIR="$1"
                else
                    error "Unexpected argument: $1"
                fi
                shift
                ;;
        esac
    done

    [[ -n "$INSTALLER_DIR" ]] || error "Missing required argument: installer_dir"
    [[ -d "$INSTALLER_DIR" ]] || error "Installer directory not found: $INSTALLER_DIR"

    INSTALLER_DIR="$(cd "$INSTALLER_DIR" && pwd)"
    OUTPUT_ISO="$(abs_path "$OUTPUT_ISO")"
}

prepare_build_root() {
    if [[ "$CLEAN" -eq 1 ]]; then
        info "Cleaning previous build artifacts..."
        rm -rf "$BUILD_ROOT"
    fi

    mkdir -p "$PROFILE_DIR" "$WORK_DIR" "$(dirname "$OUTPUT_ISO")"
}

write_common_profile() {
    rm -rf "$PROFILE_DIR"
    mkdir -p \
        "$PROFILE_DIR/airootfs/etc/systemd/system/multi-user.target.wants" \
        "$PROFILE_DIR/airootfs/root" \
        "$PROFILE_DIR/airootfs/usr/local/bin" \
        "$PROFILE_DIR/syslinux" \
        "$PROFILE_DIR/efiboot/loader/entries"

    cat > "$PROFILE_DIR/profiledef.sh" <<EOF
#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="${ISO_NAME,,}"
iso_label="${ISO_NAME^^}"
iso_publisher="SENDUNE <https://github.com/Sage563/SENDUNE-ARCHINSTALLER>"
iso_application="SENDUNE Live System"
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

    cat > "$PROFILE_DIR/packages.x86_64" <<'EOF'
base
linux
linux-firmware
arch-install-scripts
archinstall
bash-completion
base-devel
curl
dhcpcd
dosfstools
e2fsprogs
efibootmgr
efivar
exfatprogs
git
go
gptfdisk
hdparm
iwd
less
lshw
man-db
man-pages
memtest86+
nano
networkmanager
ntfs-3g
pacman
pciutils
python
python-pip
python-setuptools
python-wheel
rsync
squashfs-tools
sudo
syslinux
systemd
usbutils
vim
wget
xz
EOF

    cat > "$PROFILE_DIR/pacman.conf" <<'EOF'
[options]
HoldPkg = pacman glibc
Architecture = auto
CheckSpace
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Optional

[core]
Include = /etc/pacman.d/mirrorlist

[extra]
Include = /etc/pacman.d/mirrorlist
EOF

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

LABEL memtest
MENU LABEL Memory Test (memtest86+)
LINUX /%INSTALL_DIR%/boot/memtest86+/memtest.bin
EOF

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

    cat > "$PROFILE_DIR/airootfs/etc/hostname" <<'EOF'
sendune
EOF

    cat > "$PROFILE_DIR/airootfs/etc/hosts" <<'EOF'
127.0.0.1 localhost
::1 localhost
127.0.1.1 sendune.localdomain sendune
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

    cat > "$PROFILE_DIR/airootfs/root/.bash_profile" <<'EOF'
#!/bin/bash

[[ $- != *i* ]] && return

clear
cat <<'WELCOME'

SENDUNE Live Environment

WELCOME

echo
echo "Run 'sendune-installer' to start the installer."
echo

# Auto-start the installer once when logging into the live ISO shell.
if [[ -z "${SENDUNE_INSTALLER_STARTED:-}" ]]; then
    export SENDUNE_INSTALLER_STARTED=1
    exec sendune-installer
fi
EOF
    chmod +x "$PROFILE_DIR/airootfs/root/.bash_profile"

    info "Copying installer into ISO profile..."
    cp -R "$INSTALLER_DIR" "$PROFILE_DIR/airootfs/root/SENDUNE_installer"

    cat > "$PROFILE_DIR/airootfs/usr/local/bin/sendune-installer" <<'EOF'
#!/bin/bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required to run SENDUNE." >&2
    exit 1
fi

export PYTHONPATH="/root${PYTHONPATH:+:$PYTHONPATH}"
cd /root

if python3 -c "import SENDUNE_installer" >/dev/null 2>&1; then
    exec python3 -m SENDUNE_installer "$@"
else
    echo "SENDUNE_installer module is missing from /root/SENDUNE_installer" >&2
    exit 1
fi
EOF
    chmod +x "$PROFILE_DIR/airootfs/usr/local/bin/sendune-installer"

    cat > "$PROFILE_DIR/airootfs/usr/local/bin/sendune_installer" <<'EOF'
#!/bin/bash
set -euo pipefail
exec /usr/local/bin/sendune-installer "$@"
EOF
    chmod +x "$PROFILE_DIR/airootfs/usr/local/bin/sendune_installer"

    cat > "$PROFILE_DIR/airootfs/root/customize_airootfs.sh" <<'EOF'
#!/bin/bash
set -euo pipefail

useradd -m -s /bin/bash aurbuilder || true
echo 'aurbuilder ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/aurbuilder
chmod 440 /etc/sudoers.d/aurbuilder

su - aurbuilder -c 'rm -rf ~/yay && git clone https://aur.archlinux.org/yay.git ~/yay'
su - aurbuilder -c 'cd ~/yay && makepkg -si --noconfirm'

rm -f /etc/sudoers.d/aurbuilder
EOF
    chmod +x "$PROFILE_DIR/airootfs/root/customize_airootfs.sh"

    if [[ -f "$PROFILE_DIR/airootfs/root/SENDUNE_installer/assets/sendune_wallpaper.png" ]]; then
        local wallpaper="$PROFILE_DIR/airootfs/root/SENDUNE_installer/assets/sendune_wallpaper.png"
        local splash="$PROFILE_DIR/syslinux/splash.png"
        if command -v convert >/dev/null 2>&1; then
            info "Generating syslinux splash image..."
            if ! convert "$wallpaper" -resize 640x480 -colors 16 "$splash" 2>/dev/null; then
                warn "Image conversion failed; using the original wallpaper."
                cp "$wallpaper" "$splash"
            fi
        else
            warn "ImageMagick not found; using the original wallpaper."
            cp "$wallpaper" "$splash"
        fi

        if ! grep -q "MENU BACKGROUND splash.png" "$PROFILE_DIR/syslinux/archiso.cfg"; then
            sed -i '/MENU TITLE SENDUNE Live Environment/a MENU BACKGROUND splash.png' \
                "$PROFILE_DIR/syslinux/archiso.cfg"
        fi
    else
        warn "Wallpaper not found at assets/sendune_wallpaper.png; boot menu will use default background."
    fi
}

find_built_iso() {
    find "$(dirname "$OUTPUT_ISO")" -maxdepth 1 -type f -name '*.iso' -printf '%T@ %p\n' \
        | sort -n \
        | tail -1 \
        | cut -d' ' -f2-
}

move_final_iso() {
    local built_iso="$1"
    [[ -n "$built_iso" && -f "$built_iso" ]] || error "ISO file was not produced."

    if [[ "$built_iso" != "$OUTPUT_ISO" ]]; then
        mv -f "$built_iso" "$OUTPUT_ISO"
    fi

    success "ISO successfully built at: $OUTPUT_ISO"
    info "ISO size: $(du -h "$OUTPUT_ISO" | awk '{print $1}')"
}

build_native_arch() {
    info "Running native Arch build..."
    command -v pacman >/dev/null 2>&1 || error "pacman is required for native Arch builds."

    sudo pacman -Syu --needed --noconfirm archiso git imagemagick || error "Failed to install native build dependencies."

    prepare_build_root
    write_common_profile

    rm -f "$(dirname "$OUTPUT_ISO")"/*.iso

    local mkarchiso_args=()
    [[ "$VERBOSE" -eq 1 ]] && mkarchiso_args+=(-v)
    mkarchiso_args+=(-w "$WORK_DIR" -o "$(dirname "$OUTPUT_ISO")" "$PROFILE_DIR")

    info "Building ISO with mkarchiso..."
    sudo mkarchiso "${mkarchiso_args[@]}"
    move_final_iso "$(find_built_iso)"
}

build_with_docker() {
    local docker
    docker="$(docker_cmd)" || error "Docker is required. On WSL, make sure Docker Desktop WSL integration is enabled or the Docker daemon is running."

    info "Running Docker-based build..."
    if is_wsl; then
        info "WSL detected; using Docker from inside WSL."
    fi

    prepare_build_root
    write_common_profile

    local docker_dir="${BUILD_ROOT}/docker"
    local output_dir
    output_dir="$(dirname "$OUTPUT_ISO")"

    rm -rf "$docker_dir"
    mkdir -p "$docker_dir" "$output_dir"
    rm -f "$output_dir"/*.iso

    cat > "$docker_dir/Dockerfile" <<'EOF'
FROM archlinux:latest

RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm archiso git imagemagick && \
    pacman -Scc --noconfirm

WORKDIR /workdir
CMD ["/bin/bash"]
EOF

    info "Building Docker image..."
    eval "$docker build -t sendune-iso-builder \"$docker_dir\""

    local container_work="${BUILD_ROOT}/docker-work"
    mkdir -p "$container_work"

    local mkarchiso_flags=""
    [[ "$VERBOSE" -eq 1 ]] && mkarchiso_flags="-v"

    info "Building ISO inside Docker..."
    eval "$docker run --rm --privileged \
        -v \"$PROFILE_DIR:/profile:ro\" \
        -v \"$container_work:/work\" \
        -v \"$output_dir:/output\" \
        sendune-iso-builder \
        bash -lc 'set -euo pipefail; mkarchiso $mkarchiso_flags -w /work -o /output /profile'"

    move_final_iso "$(find_built_iso)"
}

main() {
    parse_args "$@"

    local os_id
    os_id="$(detect_os)"
    info "Detected OS: $os_id"

    case "$os_id" in
        arch|manjaro|endeavouros)
            build_native_arch
            ;;
        *)
            warn "Non-Arch environment detected; switching to Docker build."
            build_with_docker
            ;;
    esac

    success "Build complete."
}

main "$@"
