#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .custom_classes import LogFile
from .dotfiles import install_external_dotfiles, write_bashrc
from .installer_functions import (
    CUSTOM_COMMANDS,
    DEFAULT_SERVICES,
    MOCK_MODE,
    MockInstaller,
    interactive_add_users,
    interactive_audio_setup,
    interactive_bootloader,
    interactive_cloud_integration,
    interactive_custom_commands,
    interactive_development_tools,
    interactive_desktop_environment,
    interactive_disk_format,
    interactive_find_mirrors,
    interactive_format_partition,
    interactive_graphics_drivers,
    interactive_locale_setup,
    interactive_login_manager,
    interactive_multimedia_tools,
    interactive_network_services,
    interactive_performance_tuning,
    interactive_security_hardening,
    interactive_services,
    interactive_specialized_environments,
    interactive_system_automation,
    interactive_system_health_monitoring,
    interactive_system_scoring,
    interactive_system_themes,
    interactive_system_utilities,
    interactive_timezone,
    interactive_wifi,
    input_with_pause,
    install_feature_updater,
    run_command,
    sync_live_system_time,
)
from .narchs_logos import RGB3DLogo

try:
    from archinstall.lib.args import arch_config_handler
    from archinstall.lib.installer import Installer
except Exception:
    Installer = None
    arch_config_handler = None


LOGDIR = Path("/var/log/SENDUNE_installer.log")
SENDUNE_OS_RELEASE = """NAME="SENDUNE Linux"
PRETTY_NAME="SENDUNE Linux"
ID=sendune
ID_LIKE=arch
BUILD_ID=rolling
ANSI_COLOR="38;2;23;147;209"
HOME_URL="https://github.com/Sage563/SENDUNE-ARCHINSTALLER"
SUPPORT_URL="https://github.com/Sage563/SENDUNE-ARCHINSTALLER/issues"
BUG_REPORT_URL="https://github.com/Sage563/SENDUNE-ARCHINSTALLER/issues"
LOGO=sendune-logo
VERSION_CODENAME="Innovation"
DOCUMENTATION_URL="https://github.com/Sage563/SENDUNE-ARCHINSTALLER/wiki"
"""

BASE_PACKAGES = [
    'base', 'linux', 'linux-firmware', 'vim', 'nano', 'sudo', 'git', 'bash-completion',
    'networkmanager', 'openssh', 'bluez', 'bluez-utils', 'pulseaudio', 'htop',
    'neofetch', 'zsh', 'curl', 'wget', 'docker', 'python', 'python-pip',
    'nodejs', 'npm', 'firefox', 'chromium', 'code', 'go', 'gcc', 'base-devel',
    'fdisk', 'gparted', 'ntfs-3g', 'exfatprogs', 'pciutils', 'usbutils', 'man-db',
    'man-pages', 'texinfo', 'unzip', 'unrar', 'zip', 'rsync', 'net-tools', 'neovim',
    'stow'
]

DESKTOP_PACKAGES = [
    'hyprland',
    'wayland',
    'swaybg',
    'mako',
    'foot',
    'wl-clipboard',
    'waybar',
    'wofi',
    'grim',
    'slurp',
    'polkit',
    'pipewire',
    'pipewire-pulse',
    'xdg-desktop-portal-hyprland',
    'thunar',
    'hyprpaper'
]


def logo_start():
    logo = [
        "  ███████╗███████╗███╗   ██╗██████╗ ██╗   ██╗███╗   ██╗███████╗",
        "  ██╔════╝██╔════╝████╗  ██║██╔══██╗██║   ██║████╗  ██║██╔════╝",
        "  ███████╗█████╗  ██╔██╗ ██║██║  ██║██║   ██║██╔██╗ ██║█████╗  ",
        "  ╚════██║██╔══╝  ██║╚██╗██║██║  ██║██║   ██║██║╚██╗██║██╔══╝  ",
        "  ███████║███████╗██║ ╚████║██████╔╝╚██████╔╝██║ ╚████║███████╗",
        "  ╚══════╝╚══════╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝",
        "                    S E N D U N E   I N S T A L L E R          ",
    ]
    logo_animation = RGB3DLogo(logo=logo, speed=0.05, bold=True)
    logo_animation.start()
    return logo_animation


def get_mount_point(logo_animation) -> Path:
    disk_config = None
    if MOCK_MODE:
        return Path("MOCK_MOUNT_POINT")

    if 'arch_config_handler' in globals() and arch_config_handler:
        try:
            disk_config = getattr(arch_config_handler, 'config', None)
            if disk_config:
                disk_config = getattr(disk_config, 'disk_config', None)
        except Exception:
            disk_config = None
    if disk_config and getattr(disk_config, 'mountpoint', None):
        return Path(disk_config.mountpoint)
    user_input = input_with_pause("Enter mount point for installation (default /mnt): ", logo_animation).strip() or "/mnt"
    try:
        mountpoint = Path(user_input)
        mountpoint.mkdir(parents=True, exist_ok=True)
        return mountpoint
    except Exception as e:
        print(f"Error creating mount point: {e}")
        return Path("/mnt")


def unique_items(items):
    seen = set()
    ordered = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def package_is_available(package: str) -> bool:
    result = subprocess.run(
        ['pacman', '-Si', package],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False
    )
    return result.returncode == 0


def filter_installable_packages(packages, log: LogFile):
    installable = []
    skipped = []
    for package in unique_items(packages):
        if package_is_available(package):
            installable.append(package)
        else:
            skipped.append(package)

    if skipped:
        log.warn(f"Skipping unavailable packages: {', '.join(skipped)}")
        print("Skipping unavailable packages: " + ", ".join(skipped))

    return installable


def arch_chroot(installer, command: str, log: LogFile):
    result = subprocess.run(
        ['arch-chroot', str(installer.mount_point), '/bin/bash', '-lc', command],
        check=False
    )
    if result.returncode != 0:
        log.warn(f"arch-chroot command failed: {command}")
    return result.returncode


def define_installer(mount_point, log: LogFile):
    installer = Installer(
        mount_point=mount_point,
        base_packages=BASE_PACKAGES,
        desktop_packages=DESKTOP_PACKAGES,
        default_services=DEFAULT_SERVICES,
        custom_commands=CUSTOM_COMMANDS,
        log=log
    )
    installer.additional_packages = []
    installer.services = []
    installer.users = []
    installer.desktop_packages = list(DESKTOP_PACKAGES)
    installer.selected_locale = 'en_US.UTF-8'
    installer.selected_timezone = 'America/New_York'
    installer.selected_keymap = 'us'

    original_add_packages = installer.add_additional_packages
    original_enable_service = installer.enable_service
    original_create_users = installer.create_users

    def tracked_add_additional_packages(packages):
        normalized = packages if isinstance(packages, list) else [packages]
        for package in normalized:
            if package not in installer.additional_packages:
                installer.additional_packages.append(package)
        return original_add_packages(packages)

    def tracked_enable_service(services):
        normalized = services if isinstance(services, list) else [services]
        for service in normalized:
            if service not in installer.services:
                installer.services.append(service)
        return original_enable_service(services)

    def tracked_create_users(users):
        normalized = users if isinstance(users, list) else [users]
        for user in normalized:
            if not any(existing.username == user.username for existing in installer.users):
                installer.users.append(user)
        return original_create_users(users)

    installer.add_additional_packages = tracked_add_additional_packages
    installer.enable_service = tracked_enable_service
    installer.create_users = tracked_create_users
    return installer


def install_target_system(installer, log: LogFile):
    mount_point = Path(installer.mount_point)
    packages = filter_installable_packages(
        BASE_PACKAGES + getattr(installer, 'desktop_packages', []) + getattr(installer, 'additional_packages', []),
        log
    )
    if not packages:
        raise RuntimeError("No installable packages were selected for the target system.")

    result = subprocess.run(['pacstrap', '-K', str(mount_point), *packages], check=False)
    if result.returncode != 0:
        raise RuntimeError("pacstrap failed while installing the target system")

    subprocess.run(
        ['bash', '-lc', f'genfstab -U {mount_point} >> {mount_point}/etc/fstab'],
        check=True
    )
    log.info("Base Arch system installed successfully.")


def configure_target_locale_and_timezone(installer, log: LogFile):
    mount_point = Path(installer.mount_point)
    locale = getattr(installer, 'selected_locale', 'en_US.UTF-8')
    timezone = getattr(installer, 'selected_timezone', 'America/New_York')
    keymap = getattr(installer, 'selected_keymap', 'us')

    locale_gen = mount_point / 'etc' / 'locale.gen'
    locale_lines = locale_gen.read_text(encoding='utf-8').splitlines() if locale_gen.exists() else []
    locale_entry = f'{locale} UTF-8'
    if locale_entry not in locale_lines:
        locale_lines.append(locale_entry)
    locale_gen.write_text('\n'.join(unique_items(locale_lines)) + '\n', encoding='utf-8')
    (mount_point / 'etc' / 'locale.conf').write_text(f'LANG={locale}\n', encoding='utf-8')
    arch_chroot(installer, 'locale-gen', log)

    localtime_path = mount_point / 'etc' / 'localtime'
    if localtime_path.exists() or localtime_path.is_symlink():
        localtime_path.unlink()
    os.symlink(f'/usr/share/zoneinfo/{timezone}', localtime_path)
    (mount_point / 'etc' / 'vconsole.conf').write_text(f'KEYMAP={keymap}\n', encoding='utf-8')
    arch_chroot(installer, 'hwclock --systohc', log)


def apply_sendune_branding(installer, log: LogFile):
    mount_point = Path(installer.mount_point)
    asset_dir = Path(__file__).parent / 'assets'

    wp_dir = mount_point / 'usr' / 'share' / 'backgrounds' / 'sendune'
    wp_dir.mkdir(parents=True, exist_ok=True)
    if (asset_dir / 'sendune_wallpaper.png').exists():
        shutil.copy(asset_dir / 'sendune_wallpaper.png', wp_dir / 'sendune_wallpaper.png')

    flip_src = asset_dir / 'flip'
    if flip_src.exists():
        for flip_dest in [mount_point / 'usr' / 'bin' / 'flip', mount_point / 'usr' / 'local' / 'bin' / 'flip']:
            flip_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(flip_src, flip_dest)
            flip_dest.chmod(0o755)

    for os_release_path in [mount_point / 'etc' / 'os-release', mount_point / 'usr' / 'lib' / 'os-release']:
        os_release_path.parent.mkdir(parents=True, exist_ok=True)
        os_release_path.write_text(SENDUNE_OS_RELEASE, encoding='utf-8')

    (mount_point / 'etc' / 'lsb-release').write_text(
        'DISTRIB_ID=Sendune\nDISTRIB_RELEASE=rolling\nDISTRIB_DESCRIPTION="SENDUNE Linux"\n',
        encoding='utf-8'
    )
    (mount_point / 'etc' / 'issue').write_text('SENDUNE Linux \\r (\\l)\n\n', encoding='utf-8')
    (mount_point / 'etc' / 'hostname').write_text('sendune\n', encoding='utf-8')
    (mount_point / 'etc' / 'hosts').write_text(
        '127.0.0.1 localhost\n::1 localhost\n127.0.1.1 sendune.localdomain sendune\n',
        encoding='utf-8'
    )

    grub_file = mount_point / 'etc' / 'default' / 'grub'
    if grub_file.exists():
        grub_content = grub_file.read_text(encoding='utf-8')
        if 'GRUB_DISTRIBUTOR=' in grub_content:
            lines = []
            for line in grub_content.splitlines():
                if line.startswith('GRUB_DISTRIBUTOR='):
                    lines.append('GRUB_DISTRIBUTOR="SENDUNE"')
                else:
                    lines.append(line)
            grub_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        else:
            with grub_file.open('a', encoding='utf-8') as f:
                f.write('\nGRUB_DISTRIBUTOR="SENDUNE"\n')
    log.info("Applied SENDUNE branding to installed system.")


def enable_target_services(installer, log: LogFile):
    for service in unique_items(getattr(installer, 'services', [])):
        arch_chroot(installer, f'systemctl enable {service}', log)


def install_yay_in_target(installer, log: LogFile):
    if MOCK_MODE:
        log.info("[MOCK] Would build and install yay in the target system.")
        return

    log.info("Building yay inside the target system.")
    commands = [
        "useradd -m -s /bin/bash aurbuilder || true",
        "echo 'aurbuilder ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/aurbuilder",
        "chmod 440 /etc/sudoers.d/aurbuilder",
        "su - aurbuilder -c 'rm -rf ~/yay && git clone https://aur.archlinux.org/yay.git ~/yay'",
        "su - aurbuilder -c 'cd ~/yay && makepkg -si --noconfirm'",
        "rm -f /etc/sudoers.d/aurbuilder"
    ]
    for command in commands:
        result = arch_chroot(installer, command, log)
        if result != 0:
            raise RuntimeError("Failed to build/install yay in the target system")
    log.info("yay installed in the target system.")


def full_installation(installer, log: LogFile, logo_animation: RGB3DLogo):
    logo_animation.clear_content_area()
    interactive_find_mirrors(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_disk_format(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_format_partition(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_wifi(installer, log, logo_animation)
    sync_live_system_time(log)

    logo_animation.clear_content_area()
    interactive_desktop_environment(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_graphics_drivers(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_development_tools(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_security_hardening(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_locale_setup(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_login_manager(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_system_themes(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_system_utilities(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_network_services(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_system_automation(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_audio_setup(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_multimedia_tools(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_performance_tuning(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_cloud_integration(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_specialized_environments(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_system_health_monitoring(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_system_scoring(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_services(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_timezone(installer, log, logo_animation)

    installer.mount_partitions()
    log.info(f"Mounted partitions at {installer.mount_point}")

    print("\n Installing Arch base system and SENDUNE packages to target disk...")
    install_target_system(installer, log)
    configure_target_locale_and_timezone(installer, log)
    apply_sendune_branding(installer, log)
    install_yay_in_target(installer, log)

    logo_animation.clear_content_area()
    interactive_add_users(installer, log, logo_animation)
    for svc in ['NetworkManager', 'sshd', 'bluetooth', 'pipewire']:
        if svc not in installer.services:
            installer.services.append(svc)
    enable_target_services(installer, log)

    logo_animation.clear_content_area()
    interactive_bootloader(installer, log, logo_animation)
    logo_animation.clear_content_area()
    interactive_custom_commands(installer, log, logo_animation)

    kernel_path = installer.mount_point / 'boot' / 'vmlinuz-linux'
    if kernel_path.exists():
        log.info("Linux kernel successfully installed.")
    else:
        log.error("Linux kernel missing! Installation may have failed. Re-install on disk/format and try again.")
        print("Linux kernel missing! Installation may have failed. Re-install on disk/format and try again.")

    for user in getattr(installer, 'users', []):
        if user.username == 'root':
            continue
        home = installer.mount_point / 'home' / user.username
        if MOCK_MODE:
            home = Path(f"MOCK_HOME_{user.username}")
        log.info(f"Installing dotfiles for {user.username} at {home}")
        write_bashrc(home, log, installer.mount_point)
        install_external_dotfiles(home, log, installer.mount_point)

    arch_chroot(installer, 'grub-mkconfig -o /boot/grub/grub.cfg', log)
    install_feature_updater(
        installer,
        log,
        repo_url="https://github.com/Sage563/updater-theme-sendune-installer",
        branch="main"
    )

    print("\n" + "=" * 50)
    print(" SENDUNE Installation Complete!")
    print("=" * 50)
    print("Your system has been successfully installed with:")
    print("SENDUNE Linux on top of Arch Linux")
    print("Selected desktop environment")
    print("Login manager/display manager")
    print("\n Next steps:")
    print("1. Reboot your system")
    print("2. Login with your created user account")
    print("3. Use 'flip' for package management")
    print("4. Configure additional settings as needed")
    print("\n Log file: " + str(LOGDIR))
    print("=" * 50)


def show_welcome_screen():
    os.system('clear' if os.name != 'nt' else 'cls')
    print("\033[0m")
    print("\n\033[1;33mSystem Information:\033[0m")
    if MOCK_MODE:
        print("  Running in MOCK MODE (Windows development)")
        print("  No actual changes will be made")
    else:
        try:
            with open('/proc/cpuinfo', 'r', encoding='utf-8') as f:
                for line in f:
                    if 'model name' in line:
                        cpu = line.split(':', 1)[1].strip()
                        print(f"  CPU: {cpu}")
                        break
            with open('/proc/meminfo', 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_kb = int(line.split()[1])
                        mem_gb = mem_kb / (1024 * 1024)
                        print(f"  RAM: {mem_gb:.1f} GB")
                        break
        except Exception:
            print("  System info unavailable")

    print("\n\033[1;32mPress Enter to begin installation...\033[0m")
    input()


def starting_Sendune() -> None:
    if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except Exception:
            pass

    if Installer is None and not MOCK_MODE:
        print("\n\033[1;31m Error: archinstall core dependency is missing.\033[0m")
        print("This program cannot run without archinstall.")
        print("Please ensure the ISO was built correctly.")
        sys.exit(1)

    try:
        show_welcome_screen()
        print("Starting SENDUNE Installer...")
        logo_animation = logo_start()
        logo_animation.set_scroll_region(top=8)
        mount_point = get_mount_point(logo_animation)
        print(f"Installer will use: {mount_point} as mount point.")

        log = LogFile(LOGDIR)
        log.info("SENDUNE Installer started.")
        log.info(f"Mount point: {mount_point}")
        log.info(f"Mock mode: {MOCK_MODE}")

        try:
            if Installer is None and not MOCK_MODE:
                raise RuntimeError(
                    "archinstall package not available.\n"
                    "Install with: pacman -Sy archinstall\n"
                    "Or run the installer from the SENDUNE ISO."
                )

            if MOCK_MODE:
                log.info("[MOCK] Initializing Mock Installer")
                installer = MockInstaller(mount_point=mount_point, base_packages=BASE_PACKAGES)
                installer.desktop_packages = list(DESKTOP_PACKAGES)
                installer.selected_locale = 'en_US.UTF-8'
                installer.selected_timezone = 'America/New_York'
                installer.selected_keymap = 'us'
            else:
                installer = define_installer(mount_point, log)

            full_installation(installer, log, logo_animation)
        except KeyboardInterrupt:
            print("\n\nInstallation cancelled by user.")
            log.warn("Installation cancelled by user (Ctrl+C)")
        except Exception as e:
            log.error(f"Installation failed: {e}")
            print(f"\n\033[1;31m Installation failed: {e}\033[0m")
            print("\nOptions:")
            print("  1. Try again")
            print("  2. Exit to shell")
            choice = input_with_pause("Choice (1/2): ", logo_animation).strip()
            if choice == "1":
                starting_Sendune()
                return
        finally:
            log.info("Installer finished.")
            log.close()
            logo_animation.stop()
            print(f"\nLog file saved to: {LOGDIR}")
            print("\n" + "!" * 50)
            print("  INSTALLATION COMPLETE - REBOOT REQUIRED")
            print("!" * 50)
            reboot = input("\nWould you like to reboot now? (y/n): ").strip().lower()
            if reboot == 'y':
                print("Rebooting system...")
                if not MOCK_MODE:
                    os.system('reboot')
                else:
                    print("[MOCK] System would reboot now.")
            else:
                print("Please remember to reboot manually to enter your new system.")
    except Exception as e:
        print(f"\033[1;31mFatal error: {e}\033[0m")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    starting_Sendune()
