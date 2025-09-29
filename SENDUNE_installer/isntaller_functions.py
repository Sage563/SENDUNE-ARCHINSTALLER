import os
from pathlib import Path
from custom_classes import LogFile
from ..archinstall import SysInfo
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
        except:
            log.error("Wi-Fi setup failed or skipped.")
    else:
        log.info("No Wi-Fi networks found.")
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
