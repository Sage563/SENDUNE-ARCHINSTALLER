#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# SENDUNE Arch ISO Builder
# Builds a custom Arch Linux ISO with SENDUNE installer preloaded
# Works on native Arch, WSL, and Docker environments
# ═══════════════════════════════════════════════════════════════════════════════

VERSION="2.0.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="iso_work"
RELENG_DIR="$WORK_DIR/releng"

# Defaults
INSTALLER_DIR=""
OUTPUT_FILE=""
ISO_NAME="SENDUNE"
CLEAN_BUILD=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ═══════════════════════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════════════════════
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} ${BOLD}$1${NC}"; }

# ═══════════════════════════════════════════════════════════════════════════════
# Help / Usage
# ═══════════════════════════════════════════════════════════════════════════════
show_help() {
    cat << EOF
${BOLD}SENDUNE Arch ISO Builder v${VERSION}${NC}

${BOLD}USAGE:${NC}
    $0 <installer_dir> [options]

${BOLD}ARGUMENTS:${NC}
    <installer_dir>     Path to SENDUNE_installer directory (required)

${BOLD}OPTIONS:${NC}
    -o, --output FILE   Output ISO file path (default: ./out-iso/SENDUNE.iso)
    -n, --name NAME     ISO name/label (default: SENDUNE)
    -c, --clean         Clean build (remove existing releng profile)
    -v, --verbose       Verbose output
    -h, --help          Show this help message

${BOLD}EXAMPLES:${NC}
    $0 SENDUNE_installer
    $0 SENDUNE_installer -o ~/Downloads/my-custom.iso
    $0 SENDUNE_installer --output /path/to/output.iso --name MyDistro
    $0 ./SENDUNE_installer -o ./build/SENDUNE.iso --clean

${BOLD}ENVIRONMENT:${NC}
    Automatically detects: Native Arch, WSL, Docker
    Uses Docker on non-Arch systems for compatibility

EOF
    exit 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# Argument Parsing
# ═══════════════════════════════════════════════════════════════════════════════
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -n|--name)
                ISO_NAME="$2"
                shift 2
                ;;
            -c|--clean)
                CLEAN_BUILD=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --docker-internal)
                # Internal flag for Docker builds
                shift
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                ;;
            *)
                if [[ -z "$INSTALLER_DIR" ]]; then
                    INSTALLER_DIR="$1"
                else
                    log_error "Unexpected argument: $1"
                    show_help
                fi
                shift
                ;;
        esac
    done

    # Set default output if not specified (uses out-iso directory)
    if [[ -z "$OUTPUT_FILE" ]]; then
        OUTPUT_FILE="./out-iso/${ISO_NAME}.iso"
    fi

    # Convert to absolute path
    if [[ "$OUTPUT_FILE" != /* ]]; then
        OUTPUT_FILE="$(pwd)/$OUTPUT_FILE"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════════
check_requirements() {
    log_step "Checking requirements..."
    
    if [[ -z "$INSTALLER_DIR" ]]; then
        log_error "Installer directory is required!"
        echo ""
        show_help
    fi
    
    if [[ ! -d "$INSTALLER_DIR" ]]; then
        log_error "Installer directory not found: $INSTALLER_DIR"
        exit 1
    fi
    
    if [[ ! -f "$INSTALLER_DIR/__main__.py" ]]; then
        log_error "__main__.py not found in $INSTALLER_DIR"
        exit 1
    fi

    log_info "Installer: $INSTALLER_DIR"
    log_info "Output:    $OUTPUT_FILE"
    log_info "ISO Name:  $ISO_NAME"
}

detect_environment() {
    if [[ -f /etc/arch-release ]]; then
        echo "arch"
    elif grep -qi microsoft /proc/version 2>/dev/null; then
        echo "wsl"
    else
        echo "other"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Docker Build (for non-Arch systems)
# ═══════════════════════════════════════════════════════════════════════════════
setup_docker_build() {
    log_step "Setting up Docker-based build..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    cat > Dockerfile << 'EOF'
FROM archlinux:latest
RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm archiso git base-devel && \
    pacman -Scc --noconfirm
WORKDIR /build
CMD ["/bin/bash"]
EOF
    
    log_info "Building Docker image..."
    docker build -t sendune-iso-builder .
    
    local output_dir=$(dirname "$OUTPUT_FILE")
    local output_name=$(basename "$OUTPUT_FILE")
    
    log_info "Running build in Docker container..."
    docker run --rm --privileged \
        -v "$(pwd):/build" \
        -v "$output_dir:/output" \
        sendune-iso-builder \
        /bin/bash -c "/build/build_arch_iso.sh $INSTALLER_DIR -o /output/$output_name --docker-internal"
    
    exit 0
}

install_archiso() {
    log_info "Installing archiso..."
    if ! sudo pacman -S --noconfirm archiso; then
        log_error "Failed to install archiso"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Profile Setup
# ═══════════════════════════════════════════════════════════════════════════════
download_releng() {
    log_step "Downloading official Arch releng profile..."
    
    mkdir -p "$WORK_DIR"
    
    if [[ -d "$RELENG_DIR" ]]; then
        if $CLEAN_BUILD; then
            log_warn "Clean build: removing existing releng..."
            rm -rf "$RELENG_DIR"
        else
            log_info "Using existing releng profile (use --clean to refresh)"
            return
        fi
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed."
        exit 1
    fi
    
    git clone --depth 1 https://gitlab.archlinux.org/archlinux/archiso.git "$WORK_DIR/archiso-tmp"
    cp -r "$WORK_DIR/archiso-tmp/configs/releng" "$RELENG_DIR"
    rm -rf "$WORK_DIR/archiso-tmp"
    
    log_info "Releng profile ready"
}

create_custom_profiledef() {
    log_step "Creating SENDUNE profile..."
    
    cat > "$RELENG_DIR/profiledef.sh" << PROFILEDEF
#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="$ISO_NAME"
iso_label="${ISO_NAME}_\$(date +%Y%m%d)"
iso_publisher="SENDUNE Project"
iso_application="$ISO_NAME Arch Linux Installer"
iso_version="$VERSION"
install_dir="arch"
buildmodes=('iso')
bootmodes=('bios.syslinux.mbr' 'bios.syslinux.eltorito' 'uefi-x64.systemd-boot.esp' 'uefi-x64.systemd-boot.eltorito')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/gshadow"]="0:0:400"
  ["/root"]="0:0:750"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/root/SENDUNE_installer"]="0:0:755"
  ["/root/SENDUNE_installer/run_installer.sh"]="0:0:755"
  ["/usr/local/bin/choose-mirror"]="0:0:755"
  ["/usr/local/bin/Installation_guide"]="0:0:755"
  ["/usr/local/bin/livecd-sound"]="0:0:755"
  ["/usr/local/bin/sendune"]="0:0:755"
)
PROFILEDEF
}

create_packages_file() {
    log_step "Creating minimal package list (~200MB ISO)..."
    
    cat > "$RELENG_DIR/packages.x86_64" << 'PACKAGES'
# Core (minimal)
base
linux
bash
coreutils
util-linux
pacman
sudo

# Networking
dhcpcd
iwd

# Installer dependencies
python
nano
dialog

# Disk tools
dosfstools
e2fsprogs
parted

# Bootloader
grub
efibootmgr
syslinux

# For uv build/install (faster than pip)
python-pip
python-uv
python-setuptools
PACKAGES
}

# ═══════════════════════════════════════════════════════════════════════════════
# Installer Injection
# ═══════════════════════════════════════════════════════════════════════════════
inject_installer() {
    log_step "Injecting SENDUNE installer..."
    
    local airootfs="$RELENG_DIR/airootfs"
    local installer_dest="$airootfs/root/SENDUNE_installer"
    local project_root="$airootfs/root/sendune-project"
    
    # Copy installer module
    mkdir -p "$installer_dest"
    cp -r "$INSTALLER_DIR"/* "$installer_dest/"
    
    # Copy project files for pip install
    mkdir -p "$project_root"
    cp -r "$INSTALLER_DIR" "$project_root/SENDUNE_installer"
    cp "pyproject.toml" "$project_root/" 2>/dev/null || true
    cp "setup.py" "$project_root/" 2>/dev/null || true
    
    # Create installer script that installs the package on first boot
    cat > "$airootfs/root/install-sendune.sh" << 'INSTALL_SCRIPT'
#!/bin/bash
# Install SENDUNE as a pip package so 'sendune' command works
cd /root/sendune-project
pip install --break-system-packages -e . 2>/dev/null || pip install -e .
echo "SENDUNE installed! Run 'sendune' to start the installer."
INSTALL_SCRIPT
    chmod +x "$airootfs/root/install-sendune.sh"
    
    # Create launcher script (fallback)
    cat > "$installer_dest/run_installer.sh" << 'LAUNCHER'
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Setup Python path
export PYTHONPATH="$PARENT_DIR:$PYTHONPATH"

# Clear screen and run installer
clear
cd "$PARENT_DIR"
exec python3 -m SENDUNE_installer
LAUNCHER
    chmod +x "$installer_dest/run_installer.sh"
    
    # Create global 'sendune' command
    mkdir -p "$airootfs/usr/local/bin"
    cat > "$airootfs/usr/local/bin/sendune" << 'SENDUNE_CMD'
#!/bin/bash
exec /root/SENDUNE_installer/run_installer.sh "$@"
SENDUNE_CMD
    chmod +x "$airootfs/usr/local/bin/sendune"
    
    # Auto-launch on tty1 login
    mkdir -p "$airootfs/root"
    cat > "$airootfs/root/.bash_profile" << 'BASHPROFILE'
# SENDUNE Auto-launch
if [[ -z $DISPLAY ]] && [[ $(tty) = /dev/tty1 ]]; then
    clear
    echo "Setting up SENDUNE..."
    
    # Build and install sendune package using uv (faster than pip)
    cd /root/sendune-project
    rm -rf dist
    uv build --no-build-isolation --wheel 2>/dev/null || python -m build --wheel
    uv pip install dist/*.whl --break-system-packages --system --no-build --no-deps 2>/dev/null || pip install --break-system-packages dist/*.whl
    cd /root
    
    echo "Starting SENDUNE Installer..."
    sleep 1
    
    # Run sendune
    exec sendune
fi
BASHPROFILE

    # Auto-login on tty1
    local getty_override="$airootfs/etc/systemd/system/getty@tty1.service.d"
    mkdir -p "$getty_override"
    cat > "$getty_override/autologin.conf" << 'AUTOLOGIN'
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -f -- \\u' --noclear --autologin root %I $TERM
AUTOLOGIN

    log_info "Installer injected with auto-launch"
}

inject_splash_screen() {
    log_step "Setting up splash screen..."
    
    local syslinux_dir="$RELENG_DIR/syslinux"
    local splash_src="$INSTALLER_DIR/assets/sendune_wallpaper.png"
    
    if [[ -f "$splash_src" ]]; then
        mkdir -p "$syslinux_dir"
        cp "$splash_src" "$syslinux_dir/splash.png"
        log_info "Splash screen: $splash_src → syslinux/splash.png"
    else
        log_warn "Splash screen not found: $splash_src"
    fi
}

setup_live_environment() {
    log_step "Configuring live environment..."
    
    local airootfs="$RELENG_DIR/airootfs"
    
    mkdir -p "$airootfs/root/.config"
    mkdir -p "$airootfs/etc"
    
    # Hostname
    echo "$ISO_NAME-LIVE" > "$airootfs/etc/hostname"
    
    # Hosts
    cat > "$airootfs/etc/hosts" << HOSTS
127.0.0.1   localhost
::1         localhost
127.0.1.1   $ISO_NAME-LIVE.localdomain $ISO_NAME-LIVE
HOSTS

    # Enable network services
    mkdir -p "$airootfs/etc/systemd/system/multi-user.target.wants"
    ln -sf /usr/lib/systemd/system/dhcpcd.service \
        "$airootfs/etc/systemd/system/multi-user.target.wants/dhcpcd.service" 2>/dev/null || true
    ln -sf /usr/lib/systemd/system/iwd.service \
        "$airootfs/etc/systemd/system/multi-user.target.wants/iwd.service" 2>/dev/null || true
    
    log_info "Live environment ready"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Build ISO
# ═══════════════════════════════════════════════════════════════════════════════
build_iso() {
    log_step "Building ISO with mkarchiso..."
    
    local output_dir=$(dirname "$OUTPUT_FILE")
    local output_name=$(basename "$OUTPUT_FILE")
    
    mkdir -p "$output_dir"
    
    if ! command -v mkarchiso &> /dev/null; then
        log_error "mkarchiso not found"
        exit 1
    fi
    
    # Clean previous artifacts
    sudo rm -rf "$WORK_DIR/work" "$WORK_DIR/out"
    
    # Build
    local mkarchiso_opts="-w $WORK_DIR/work -o $WORK_DIR/out"
    if $VERBOSE; then
        mkarchiso_opts="-v $mkarchiso_opts"
    fi
    
    sudo mkarchiso $mkarchiso_opts "$RELENG_DIR"
    
    # Find and move ISO
    local built_iso=$(find "$WORK_DIR/out" -name "*.iso" -type f | head -n 1)
    
    if [[ -z "$built_iso" ]]; then
        log_error "ISO not found after build!"
        exit 1
    fi
    
    sudo mv "$built_iso" "$OUTPUT_FILE"
    sudo chown $(id -u):$(id -g) "$OUTPUT_FILE"
    
    local iso_size=$(du -h "$OUTPUT_FILE" | cut -f1)
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}✓ BUILD COMPLETE!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "  ${BOLD}ISO:${NC}  $OUTPUT_FILE"
    echo -e "  ${BOLD}Size:${NC} $iso_size"
    echo -e "  ${BOLD}Name:${NC} $ISO_NAME"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}To test:${NC} qemu-system-x86_64 -cdrom $OUTPUT_FILE -m 2G"
    echo ""
}

cleanup() {
    log_info "Cleaning up build artifacts..."
    sudo rm -rf "$WORK_DIR/work" "$WORK_DIR/out"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════
main() {
    echo ""
    echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║           SENDUNE Arch ISO Builder v${VERSION}                  ║${NC}"
    echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    parse_args "$@"
    
    # Handle Docker-internal builds
    if [[ "${*}" == *"--docker-internal"* ]]; then
        check_requirements
    else
        check_requirements
        
        ENV=$(detect_environment)
        log_info "Environment: $ENV"
        
        case $ENV in
            arch)
                if ! command -v mkarchiso &> /dev/null; then
                    install_archiso
                fi
                ;;
            wsl|other)
                setup_docker_build
                ;;
        esac
    fi
    
    # Build process
    download_releng
    create_custom_profiledef
    create_packages_file
    inject_installer
    inject_splash_screen
    setup_live_environment
    build_iso
    cleanup
}

main "$@"