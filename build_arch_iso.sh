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

# === Unmount ISO ===
sudo umount "$WORK_DIR/mnt"

# === Repack ISO ===
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
  -eltorito-alt-boot -e EFI/archiso/efiboot.img -no-emul-boot \
  .

echo "✅ ISO created at $OUTPUT_ISO"

#chmod +x build_arch_iso.sh
#./build_arch_iso.sh archlinux-2024.08.01-x86_64.iso ./SENDUNE_installer ./SENDUNE_Arch.iso

#RUN :
# After booting Arch ISO
#cd /archinstall
#python3 -m SENDUNE_installer