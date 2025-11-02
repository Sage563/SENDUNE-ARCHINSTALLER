#!/usr/bin/env python3
import sys
import os
import time
from pathlib import Path
from narchs_logos import RGB3DLogo, input_with_pause
from custom_classes import LogFile
from isntaller_functions import (
    interactive_add_users,
    interactive_bootloader,
    interactive_custom_commands,
    interactive_disk_format,
    interactive_find_mirrors,
    interactive_format_partition,
    interactive_packages,
    interactive_services,
    interactive_timezone,
    interactive_wifi,
    install_feature_updater
    
)
from archinstall.lib.installer import Installer
from archinstall.lib.args import arch_config_handler

# =========================
# Configs
# =========================
LOGDIR = Path("/var/log/SENDUNE_installer.log")

BASE_PACKAGES = [
    'base', 'linux', 'linux-firmware', 'vim', 'sudo', 'git', 'bash-completion',
    'networkmanager', 'openssh', 'bluez', 'bluez-utils', 'pulseaudio', 'htop',
    'neofetch', 'zsh', 'curl', 'wget', 'docker', 'python', 'python-pip',
    'nodejs', 'npm', 'firefox', 'chromium', 'code'
]

DESKTOP_PACKAGES = ['xfce4', 'xfce4-goodies', 'lightdm', 'lightdm-gtk-greeter']
DEFAULT_SERVICES = ['NetworkManager', 'sshd', 'bluetooth', 'lightdm', 'docker']
CUSTOM_COMMANDS = ['/usr/local/bin/narchs-setup.sh',
                   '/usr/local/bin/narchs-dotfiles.sh',
                   '/usr/local/bin/narchs-zsh.sh']

DESKTOP_PACKAGES = [
    "hyperland",      # the compositor / window manager
    "wayland",        # needed for Wayland
    "swaybg",         # wallpaper manager
    "mako",           # notifications
    "foot",           # terminal emulator
    "wl-clipboard",   # clipboard support
    "waybar",         # status bar
    "wofi",           # application launcher
    "grim", "slurp",  # screenshot tools
    "polkit",         # authentication
    "pipewire",       # audio
    "pipewire-pulse", # pulseaudio compatibility
]


# =========================
# Logo
# =========================
def logo_start():
    logo = [
        "   ███████╗███████╗███╗   ██╗██████╗ ██    ██ ██╗   ██╗███╗   ██╗███████╗",
        "   ██╔════╝██╔════╝████╗  ██║██╔══██╗██║   ██║██║   ██║████╗  ██║██╔════╝",
        "   ███████╗█████╗  ██╔██╗ ██║██║  ██║██║   ██║██║   ██║██╔██╗ ██║█████╗  ",
        "   ╚════██║██╔══╝  ██║╚██╗██║██║  ██║██║   ██║██║   ██║██║╚██╗██║██╔══╝  ",
        "   ███████║███████╗██║ ╚████║██████╔╝╚██████╔╝╚██████╔╝██║ ╚████║███████╗",
        "   ╚══════╝╚══════╝╚═╝  ╚═══╝╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝"
    ]
    logo_animation = RGB3DLogo(logo)
    logo_animation.start()
    return logo_animation.stop

# =========================
# Mount point
# =========================
def get_mount_point() -> Path:
    disk_config = arch_config_handler.config.disk_config
    if disk_config and disk_config.mountpoint:
        return Path(disk_config.mountpoint)
    user_input = input("Enter mount point for installation (default /mnt): ").strip() or "/mnt"
    mountpoint = Path(user_input)
    mountpoint.mkdir(parents=True, exist_ok=True)
    return mountpoint

# =========================
# Define installer
# =========================
def define_installer(mount_point, log: LogFile) -> Installer:
    installer = Installer(
        mount_point=mount_point,
        base_packages=BASE_PACKAGES,
        desktop_packages=DESKTOP_PACKAGES,
        default_services=DEFAULT_SERVICES,
        custom_commands=CUSTOM_COMMANDS,
        log=log
    )
    return installer

# =========================
# Main installation steps
# =========================
def full_installation(installer: Installer, log: LogFile):
    interactive_find_mirrors(installer, log)
    interactive_disk_format(installer, log)
    interactive_format_partition(installer, log)

    # Mount partitions
    installer.mount_partitions()
    log.info(f"Mounted partitions at {installer.mount_point}")

    # Install base Linux system
    installer.add_additional_packages(installer.base_packages)
    installer.add_additional_packages(DESKTOP_PACKAGES)

    installer.write_fstab()

    log.info("Base Linux system installed.")

    interactive_add_users(installer, log)
    interactive_wifi(installer, log)
    interactive_packages(installer, log)
    interactive_services(installer, log)
    interactive_timezone(installer, log)
    interactive_bootloader(installer, log)
    grub_file = installer.mount_point / "etc" / "default" / "grub"
    with grub_file.open("a") as f:
        f.write('\nGRUB_DISTRIBUTOR="SENDUNE"\n')

    interactive_custom_commands(installer, log)

    # Verify Linux kernel installed
    kernel_path = installer.mount_point / "boot" / "vmlinuz-linux"
    if kernel_path.exists():
        log.info("Linux kernel successfully installed.")
    else:
        log.error("Linux kernel missing! Installation may have failed.Re install on disk \ format")
        print("Linux kernel missing! Installation may have failed.Re install on disk \ format")

    for svc in ["NetworkManager", "sshd", "bluetooth", "pipewire"]:
        installer.enable_service([svc])
    os.system(f"arch-chroot {installer.mount_point} grub-mkconfig -o /boot/grub/grub.cfg")
    os_release = installer.mount_point / "etc" / "os-release"
    with os_release.open("w") as f:
        f.write("""NAME="SENDUNE"
    PRETTY_NAME="SENDUNE Linux"
    ID=sendune
    ID_LIKE=arch
    BUILD_ID=2.0.25
    """)
    install_feature_updater(installer, log ,repo_url= "https://github.com/Sage563/updater-theme-sendune-installer" ,branch="main")
    



# =========================
# Entry point
# =========================
def starting_Sendune() -> None:
    print("Starting SENDUNE Installer...")
    mount_point = get_mount_point()
    print(f"Installer will use: {mount_point} as mount point.")

    # Start animated logo
    stop_logo = logo_start()

    # Initialize log
    log = LogFile(LOGDIR)
    log.info("Installer started.")

    try:
        installer = define_installer(mount_point, log)
        full_installation(installer, log)
    except Exception as e:
        log.error(f"Installation failed: {e}")
        print(f"Installation failed: {e}")
    finally:
        log.info("Installer finished.")
        log.info("Exiting installer.")
        log.close()
        stop_logo()
        print(f"Log file at {LOGDIR}")

if __name__ == "__main__":
    starting_Sendune()