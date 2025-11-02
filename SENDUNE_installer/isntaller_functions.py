import os
from pathlib import Path
from custom_classes import LogFile
from archinstall import SysInfo
from archinstall.lib.applications.application_handler import application_handler
from archinstall.lib.args import arch_config_handler
from archinstall.lib.authentication.authentication_handler import auth_handler
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.installer import Installer, accessibility_tools_in_use, run_custom_user_commands
from archinstall.lib.models import Bootloader
from archinstall.lib.models.users import User
from archinstall.lib.output import debug, error, info
from archinstall.lib.packages.packages import check_package_upgrade
from archinstall.lib.profile.profiles_handler import profile_handler
from archinstall.tui import Tui
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.lib.disk.utils import disk_layouts
from archinstall.lib.interactions.general_conf import PostInstallationAction, ask_post_installation

# ===============================
# NARCHS Full Configuration
# ===============================

DEFAULT_USER = User('narchs', 'Narchs123!', True)

BASE_PACKAGES = [
    'base', 'linux', 'linux-firmware', 'vim', 'sudo', 'git', 'bash-completion',
    'networkmanager', 'openssh', 'bluez', 'bluez-utils', 'pulseaudio', 'htop',
    'neofetch', 'zsh', 'curl', 'wget', 'docker', 'python', 'python-pip',
    'nodejs', 'npm', 'firefox', 'chromium', 'code'
]

DESKTOP_PACKAGES = ['xfce4', 'xfce4-goodies', 'lightdm', 'lightdm-gtk-greeter']
DEFAULT_SERVICES = ['NetworkManager', 'sshd', 'bluetooth', 'lightdm', 'docker']
CUSTOM_COMMANDS = ['/usr/local/bin/narchs-setup.sh', '/usr/local/bin/narchs-dotfiles.sh', '/usr/local/bin/narchs-zsh.sh']

# ===============================
# Helper Functions
# ===============================


# ===========================
# Interactive Step Menus
# ===========================
def interactive_disk_format(installer: Installer, log: LogFile):
    print("\n=== Disk Formatting ===")
    choice = input("Do you want to format all partitions? (y/n): ").lower()
    if choice == 'y':
        for part in installer.disk_config.partitions:
            fs_type = getattr(part, 'fs_type', 'ext4')
            log.info(f"Formatting {part.path} as {fs_type}...")
            installer.format_partition(part.path, fs_type)
            print(f"{part.path} formatted as {fs_type}")
    else:
        print("Skipping disk formatting.")
        log.info("Disk formatting skipped.")
    input("Press Enter to continue...")

def add_user(installer, log: LogFile):
    print("\n=== Add New User ===")
    username = input("Enter username: ").strip()
    password = input(f"Enter password for {username}: ").strip()
    is_admin = input("Should this user have sudo/admin rights? (y/n): ").lower() == 'y'

    if username and password:
        new_user = User(username, password, is_admin)
        installer.create_users([new_user])  # Add this user
        print(f"User '{username}' added successfully.")
        log.info(f"User added: {username}, admin: {is_admin}")
    else:
        print("Invalid username or password. Skipping.")
        log.warn("User creation skipped due to invalid input.")

def interactive_add_users(installer : Installer, log: LogFile):

    rootusers = input("Make defualt users(y)  / or make your own users(n) (y / n)")
    if rootusers == "y":
        users = DEFAULT_USER
        installer.create_users(users)
        print("Defualt Users Installed")
        log.info("Defualt Users Added users are narchs , Narchs123!")
    while True:
        add_user(installer, log)
        cont = input("Add another user? (y/n): ").lower()
        if cont != 'y':
            break

def interactive_packages(installer: Installer, log: LogFile):
    print("\n=== Package Installation ===")
    choice = input("Install base packages (b), desktop packages (d), or both (a)? [b/d/a]: ").lower()
    if choice in ['b','a']:
        installer.add_additional_packages(BASE_PACKAGES)
        log.info("Base packages installed.")
    if choice in ['d','a']:
        installer.add_additional_packages(DESKTOP_PACKAGES)
        log.info("Desktop packages installed.")
    input("Press Enter to continue...")

def interactive_services(installer: Installer, log: LogFile):
    print("\n=== Services Setup ===")
    for svc in DEFAULT_SERVICES:
        enable = input(f"Enable service {svc}? (y/n): ").lower()
        if enable == 'y':
            installer.enable_service([svc])
            log.info(f"Service enabled: {svc}")
        else:
            log.info(f"Service skipped: {svc}")
    input("Press Enter to continue...")

def interactive_timezone(installer: Installer, log: LogFile):
    tz = input("Set timezone (default America/New_York): ").strip()
    if not tz:
        tz = "America/New_York"
    installer.set_timezone(tz)
    installer.activate_time_synchronization()
    print(f"Timezone set to {tz}")
    log.info(f"Timezone set to {tz}")
    input("Press Enter to continue...")

def interactive_wifi(installer: Installer, log: LogFile):
    os.system("nmcli radio wifi on")
    networks = [n for n in os.popen("nmcli -t -f SSID dev wifi list").read().splitlines() if n]
    if networks:
        print("\nAvailable Wi-Fi networks:")
        for i, ssid in enumerate(networks,1):
            print(f"{i}. {ssid}")
        choice = input("Select Wi-Fi number to connect (0 to skip): ")
        try:
            choice = int(choice)
            if 1 <= choice <= len(networks):
                ssid = networks[choice-1]
                password = input(f"Enter password for {ssid}: ")
                os.system(f"nmcli device wifi connect '{ssid}' password '{password}'")
                log.info(f"Connected to Wi-Fi network: {ssid}")
            else:
                log.info("Wi-Fi setup skipped by user.")
                print("Skipping Wi-Fi setup.")
                print("WIFI REQUIRES REBOOT TO TAKE EFFECT if not wifi no LINUX KERNEL")
        except:
            log.error("Wi-Fi setup failed or skipped.")
            print("WIFI REQUIRES REBOOT TO TAKE EFFECT if not wifi no LINUX KERNEL")
            
    else:
        log.info("No Wi-Fi networks found.")
        print("WIFI REQUIRED , REBOOT TO TAKE EFFECT if not no wifi, no LINUX KERNEL")
    input("Press Enter to continue...")

def interactive_bootloader(installer: Installer, log: LogFile):
    print("\n=== Bootloader Setup ===")
    bootloaders = ["Grub", "SystemdBoot", "Skip"]
    for i, b in enumerate(bootloaders,1):
        print(f"{i}. {b}")
    choice = input("Select bootloader: ")
    try:
        choice = int(choice)
        if choice == 1:
            installer.add_bootloader('grub', arch_config_handler.config.uki)
            log.info("Bootloader installed: GRUB")
        elif choice == 2:
            installer.add_bootloader('systemd-boot', arch_config_handler.config.uki)
            log.info("Bootloader installed: SystemdBoot")
        else:
            print("Skipping bootloader setup.")
            log.info("Bootloader setup skipped.")
    except:
        print("Invalid choice, skipping bootloader setup.")
        log.error("Bootloader setup failed or skipped.")
    input("Press Enter to continue...")

def interactive_custom_commands(installer: Installer, log: LogFile):
    print("\n=== Run Custom NARCHS Scripts ===")
    for cmd in CUSTOM_COMMANDS:
        run = input(f"Run {cmd}? (y/n): ").lower()
        if run == 'y':
            os.system(cmd)
            log.info(f"Ran custom command: {cmd}")
        else:
            log.info(f"Skipped custom command: {cmd}")
    input("Press Enter to continue...")

def interactive_format_partition(installer: Installer, log: LogFile):
    print("\n=== Format Partition ===")
    disk_config = installer.disk_config
    if not disk_config or not hasattr(disk_config, 'partitions') or not disk_config.partitions:
        print("No partitions found in disk configuration.")
        log.warn("No partitions found for formatting.")
        return

    print("Available partitions:")
    for idx, part in enumerate(disk_config.partitions, 1):
        fs_type = getattr(part, 'fs_type', 'ext4')
        print(f"{idx}. {part.path} (current fs: {fs_type})")

    choice = input("Select partition number to format (0 to skip): ")
    try:
        choice = int(choice)
        if choice == 0:
            print("Skipping partition formatting.")
            log.info("Partition formatting skipped.")
            return
        if 1 <= choice <= len(disk_config.partitions):
            part = disk_config.partitions[choice-1]
            fs_type = input(f"Enter filesystem type for {part.path} (default ext4): ").strip()
            if not fs_type:
                fs_type = "ext4"
            installer.format_partition(part.path, fs_type)
            print(f"{part.path} formatted successfully.")
            log.info(f"Partition formatted: {part.path} as {fs_type}")
        else:
            print("Invalid partition number, skipping.")
            log.warn("Invalid partition number for formatting.")
    except ValueError:
        print("Invalid input, skipping formatting.")
        log.error("Invalid input for partition formatting.")
    input("Press Enter to continue...")

def interactive_find_mirrors(installer: Installer, log: LogFile):
    print("\n=== Find Fastest Mirrors ===")
    choice = input("Do you want to search for the fastest mirrors? (y/n): ").lower()
    if choice != 'y':
        print("Skipping mirror check.")
        log.info("Mirror check skipped by user.")
        return

    try:
        print("Ranking mirrors by speed...")
        os.system("reflector --latest 10 --sort rate --save /etc/pacman.d/mirrorlist")
        print("Mirrorlist updated with fastest mirrors.")
        log.info("Fastest mirrors configured.")
    except Exception as e:
        log.error(f"Failed to update mirrors: {e}")
    input("Press Enter to continue...")

def setup_login_ui(installer: Installer, log: LogFile):
    """Install and enable a GTK-based login UI (LightDM + GTK greeter).

    This will install the required packages and enable the LightDM service.
    """
    log.info("Installing LightDM and GTK greeter (lightdm + lightdm-gtk-greeter)")
    try:
        installer.add_additional_packages(['lightdm', 'lightdm-gtk-greeter'])
        # enable the service (installer API in this project expects a list)
        installer.enable_service(['lightdm'])
        log.info("LightDM and GTK greeter installed and enabled.")
    except Exception as e:
        log.error(f"Failed to install/enable LightDM: {e}")
        raise

def install_feature_updater(installer: Installer, log: LogFile, repo_url: str, branch: str = 'main'):
    """Install a startup updater that fetches latest feature archive from GitHub.

    repo_url should be the HTTPS GitHub repo root, e.g.
      https://github.com/owner/repo

    The updater will download ${repo_url}/archive/${branch}.tar.gz,
    extract it to a temp dir, then run either install_features.py or features.py
    if present. A systemd oneshot service is installed and enabled so it runs
    at every boot (and it can be triggered once immediately).
    """
    script_path = '/usr/local/bin/narchs_feature_updater.sh'
    service_path = '/etc/systemd/system/narchs-feature-updater.service'

    log.info(f"Installing feature updater script to {script_path}")
    if os.geteuid() != 0:
        log.info("Not in root")
        raise PermissionError("Must be run as root.")
    log.info("Confirmed running as root.")


    updater_script = f"""#!/usr/bin/env bash
set -euo pipefail
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
REPO_URL="{repo_url}"
BRANCH="{branch}"
ARCHIVE_URL="$REPO_URL/archive/$BRANCH.tar.gz"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found, attempting to use wget"
  if command -v wget >/dev/null 2>&1; then
    wget -q -O "$TMPDIR/features.tar.gz" "$ARCHIVE_URL"
  else
    echo "Neither curl nor wget available" >&2
    exit 1
  fi
else
  curl -fsSL "$ARCHIVE_URL" -o "$TMPDIR/features.tar.gz"
fi

mkdir -p "$TMPDIR/extracted"
tar -xzf "$TMPDIR/features.tar.gz" -C "$TMPDIR/extracted"
# find the extracted repo directory
DIR=$(find "$TMPDIR/extracted" -maxdepth 1 -mindepth 1 -type d | head -n1)
if [ -z "$DIR" ]; then
  echo "Failed to find extracted directory" >&2
  exit 1
fi

# Prefer install_features.py then features.py
if [ -f "$DIR/install_features.py" ]; then
  python3 "$DIR/install_features.py" || exit 1
elif [ -f "$DIR/features.py" ]; then
  python3 "$DIR/features.py" || exit 1
else
  echo "No feature installer script found in archive" >&2
  exit 1
fi
"""

    try:
        # write the updater script
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(updater_script)
        os.chmod(script_path, 0o755)
        log.info("Updater script written and made executable.")
        # write the systemd service (oneshot)
        service_unit = f"""[Unit]
Description=Narchs feature updater
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart={script_path}
User=root

[Install]
WantedBy=multi-user.target
"""
        with open(service_path, 'w', encoding='utf-8') as f:
            f.write(service_unit)
        log.info(f"Systemd unit written to {service_path}")

        # write a systemd timer so the updater runs periodically (daily) and
        # shortly after boot. This gives both immediate boot runs and periodic
        # updates.
        timer_path = '/etc/systemd/system/narchs-feature-updater.timer'
        timer_unit = f"""[Unit]
Description=Run Narchs feature updater daily and on boot

[Timer]
OnBootSec=2min
OnUnitActiveSec=1d
Persistent=true

[Install]
WantedBy=timers.target
"""
        with open(timer_path, 'w', encoding='utf-8') as f:
            f.write(timer_unit)
        log.info(f"Systemd timer written to {timer_path}")

        # reload systemd and enable the service and timer
        os.system('systemctl daemon-reload')
        # enable the service so it is pulled in at boot
        os.system('systemctl enable narchs-feature-updater.service')
        # enable and start the timer which will trigger the service periodically
        os.system('systemctl enable --now narchs-feature-updater.timer')
        log.info('Feature updater service and timer enabled.')

    except Exception as e:
        log.error(f"Failed to install feature updater: {e}")
        raise


    """Run the feature updater script once immediately."""
    script_path = '/usr/local/bin/narchs_feature_updater.sh'
    if os.path.exists(script_path) and os.access(script_path, os.X_OK):
        log.info('Running feature updater once...')
        ret = os.system(script_path)
        if ret != 0:
            log.error(f'Feature updater script returned non-zero exit code: {ret}')
        else:
            log.info('Feature updater completed successfully.')
    else:
        log.warn('Feature updater script not present or not executable.')
