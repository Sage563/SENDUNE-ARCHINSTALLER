#!/bin/bash
set -e

# === Config ===
SOURCE_ISO="$1"           # e.g., archlinux-2024.08.01-x86_64.iso
SENDUNE_DIR="$2"          # e.g., ./SENDUNE_installer
OUTPUT_ISO="$3"           # e.g., ./SENDUNE_Arch.iso
WORK_DIR="./iso_work"

# === Prepare working directories ===
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR/mnt" "$WORK_DIR/extract"

# === Mount original ISO ===
sudo mount -o loop "$SOURCE_ISO" "$WORK_DIR/mnt"

# === Copy ISO contents ===
rsync -a --exclude=archinstall/SENDUNE_installer "$WORK_DIR/mnt/" "$WORK_DIR/extract/"

# === Add SENDUNE installer ===
mkdir -p "$WORK_DIR/extract/archinstall"
cp -r "$SENDUNE_DIR" "$WORK_DIR/extract/archinstall/"

# === Attempt to install `archinstall` into the ISO filesystem ===
# This chroots into the extracted ISO and runs pacman to install archinstall
# Requires network and root; this step is best-effort and will be skipped
# if `pacman` is not available on the build host.
echo "Attempting to install archinstall into ISO filesystem (best-effort)..."
# Bind mount necessary pseudo-filesystems into the extracted ISO so chrooted
# package installation tools can work. We keep this best-effort and continue
# even if parts fail.
sudo mount --bind /dev "$WORK_DIR/extract/dev" || true
sudo mount --bind /sys "$WORK_DIR/extract/sys" || true
sudo mount --bind /proc "$WORK_DIR/extract/proc" || true
sudo mount --bind /run "$WORK_DIR/extract/run" || true
sudo cp -L /etc/resolv.conf "$WORK_DIR/extract/etc/resolv.conf" || true

# Create a small installer script inside the extracted tree that will detect
# the package manager available inside the chroot and try to install
# `archinstall` using the appropriate method (native package or pip).
cat > "$WORK_DIR/extract/tmp/sendune_install_archinstall.sh" <<'SH'
#!/usr/bin/env bash
set -e
echo "[sendune] running archinstall installer inside chroot"
if command -v pacman >/dev/null 2>&1; then
  echo "[sendune] detected pacman -> installing archinstall via pacman"
  pacman -Sy --noconfirm archinstall || true
  if command -v pip >/dev/null 2>&1; then
    pip install --upgrade pip setuptools wheel || true
    pip install archinstall || true
  fi
  exit 0
fi
if command -v apt-get >/dev/null 2>&1; then
  echo "[sendune] detected apt -> installing pip and archinstall via pip"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update || true
  apt-get install -y python3-pip python3-venv || true
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --upgrade pip setuptools wheel || true
    pip3 install archinstall || true
  fi
  exit 0
fi
if command -v dnf >/dev/null 2>&1; then
  echo "[sendune] detected dnf -> installing pip and archinstall via pip"
  dnf install -y python3-pip || true
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --upgrade pip setuptools wheel || true
    pip3 install archinstall || true
  fi
  exit 0
fi
if command -v zypper >/dev/null 2>&1; then
  echo "[sendune] detected zypper -> installing pip and archinstall via pip"
  zypper refresh || true
  zypper install -y python3-pip || true
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --upgrade pip setuptools wheel || true
    pip3 install archinstall || true
  fi
  exit 0
fi
# Fallback: try pip if available
if command -v pip3 >/dev/null 2>&1; then
  echo "[sendune] no package manager detected, using pip3"
  pip3 install --upgrade pip setuptools wheel || true
  pip3 install archinstall || true
else
  echo "[sendune] no supported package manager or pip found in chroot; skipping"
fi
SH

sudo chmod +x "$WORK_DIR/extract/tmp/sendune_install_archinstall.sh" || true

# Execute the installer script inside the chroot. Prefer `arch-chroot` when
# available (it sets up some extra mounts on Arch hosts), otherwise use a
# plain `chroot` invocation. Keep failures non-fatal (best-effort).
if command -v arch-chroot >/dev/null 2>&1; then
  sudo arch-chroot "$WORK_DIR/extract" /tmp/sendune_install_archinstall.sh || true
else
  sudo chroot "$WORK_DIR/extract" /bin/bash -c "/tmp/sendune_install_archinstall.sh" || true
fi

# Cleanup binds
sudo umount "$WORK_DIR/extract/dev" || true
sudo umount "$WORK_DIR/extract/sys" || true
sudo umount "$WORK_DIR/extract/proc" || true
sudo umount "$WORK_DIR/extract/run" || true

# Remove the temporary installer script
sudo rm -f "$WORK_DIR/extract/tmp/sendune_install_archinstall.sh" || true

# === Unmount ISO ===
sudo umount "$WORK_DIR/mnt"

# === Repack ISO ===
cd "$WORK_DIR/extract"
xorriso_check() {
  if command -v xorriso >/dev/null 2>&1; then
    return 0
  fi
  echo "xorriso not found — attempting to install xorriso (best-effort)"
  if command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm xorriso syslinux || true
    return 0
  fi
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update || true
    sudo apt-get install -y xorriso syslinux || true
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y xorriso syslinux || true
    return 0
  fi
  if command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y xorriso syslinux || true
    return 0
  fi
  if command -v apk >/dev/null 2>&1; then
    sudo apk add xorriso syslinux || true
    return 0
  fi
  echo "Could not auto-install xorriso; please install it manually and re-run the script."
  return 1
}

# Ensure xorriso (and isolinux/syslinux files) exist on the host
xorriso_check || echo "Proceeding without xorriso — repack may fail"
xorriso -as mkisofs \
  -iso-level 3 \
  -full-iso9660-filenames \
  -volid "SENDUNE_ARCH" \
  -output "$OUTPUT_ISO" \
  -eltorito-boot isolinux/isolinux.bin \
  -eltorito-catalog isolinux/boot.cat \
  -no-emul-boot -boot-load-size 4 -boot-info-table \
  -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
  -eltorito-alt-boot -e EFI/archiso/efiboot.img -no-emul-boot \
  .

echo "✅ ISO created at $OUTPUT_ISO"

#chmod +x build_arch_iso.sh
#curl https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso >> archlinux-2024.08.01-x86_64.iso
#sudo ./build_arch_iso.sh archlinux-2024.08.01-x86_64.iso ./SENDUNE_installer ./SENDUNE_Arch.iso

#RUN :
# After booting Arch ISO
#cd /archinstall
#python3 -m SENDUNE_installer