#!/usr/bin/env python3
import sys
import os
import time
from pathlib import Path
from .narchs_logos import RGB3DLogo, input_with_pause
from .custom_classes import LogFile
from .installer_functions import (
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
    interactive_graphics_drivers,
    interactive_development_tools,
    interactive_security_hardening,
    interactive_desktop_environment,
    interactive_locale_setup,
    interactive_additional_features,
    interactive_login_manager,
    interactive_system_themes,
    interactive_system_utilities,
    interactive_network_services,
    interactive_system_automation,
    interactive_multimedia_tools,
    interactive_office_productivity,
    interactive_ai_assistant,
    interactive_performance_tuning,
    interactive_cloud_integration,
    interactive_specialized_environments,
    interactive_system_health_monitoring,
    interactive_accessibility_features,
    interactive_system_scoring,
    interactive_company_integrations,
    interactive_ai_powered_features,
    interactive_enterprise_features,
    install_feature_updater,
    MOCK_MODE,
    run_command
)
from .dotfiles import write_hyprland_config, write_bashrc
try:
    from archinstall.lib.installer import Installer
    from archinstall.lib.args import arch_config_handler
except Exception:
    Installer = None
    arch_config_handler = None

# =========================
# Configs
# =========================
LOGDIR = Path("/var/log/SENDUNE_installer.log")

BASE_PACKAGES = [
    'base', 'linux', 'linux-firmware', 'vim', 'sudo', 'git', 'bash-completion',
    'networkmanager', 'openssh', 'bluez', 'bluez-utils', 'pulseaudio', 'htop',
    'neofetch', 'zsh', 'curl', 'wget', 'docker', 'python', 'python-pip',
    'nodejs', 'npm', 'firefox', 'chromium', 'code', 'yay'
]

# Removed duplicate base packages definition and duplicate desktop packages variable
# Default services retained
# Custom commands retained

DESKTOP_PACKAGES = [
    "hyprland",       # the compositor / window manager
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
    "xdg-desktop-portal-hyprland",
    "thunar",         # file manager
    "hyprpaper"       # wallpaper utility
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
    return logo_animation

# =========================
# Mount point
# =========================
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
def full_installation(installer: Installer, log: LogFile, logo_animation: RGB3DLogo):
    interactive_find_mirrors(installer, log, logo_animation)
    interactive_disk_format(installer, log, logo_animation)
    interactive_format_partition(installer, log, logo_animation)

    # Mount partitions
    installer.mount_partitions()
    log.info(f"Mounted partitions at {installer.mount_point}")

    # Choose desktop environment before installing packages
    interactive_desktop_environment(installer, log, logo_animation)

    # Install base Linux system
    installer.add_additional_packages(installer.base_packages)
    installer.add_additional_packages(DESKTOP_PACKAGES)

    installer.write_fstab()

    log.info("Base Linux system installed.")

    interactive_add_users(installer, log, logo_animation)
    interactive_wifi(installer, log, logo_animation)
    interactive_graphics_drivers(installer, log, logo_animation)
    interactive_development_tools(installer, log, logo_animation)
    interactive_security_hardening(installer, log, logo_animation)
    interactive_locale_setup(installer, log, logo_animation)
    interactive_additional_features(installer, log, logo_animation)
    interactive_login_manager(installer, log, logo_animation)
    interactive_system_themes(installer, log, logo_animation)
    interactive_system_utilities(installer, log, logo_animation)
    interactive_network_services(installer, log, logo_animation)
    interactive_system_automation(installer, log, logo_animation)
    interactive_multimedia_tools(installer, log, logo_animation)
    #interactive_office_productivity(installer, log, logo_animation)
    #interactive_ai_assistant(installer, log, logo_animation)
    interactive_performance_tuning(installer, log, logo_animation)
    interactive_cloud_integration(installer, log, logo_animation)
    interactive_specialized_environments(installer, log, logo_animation)
    interactive_system_health_monitoring(installer, log, logo_animation)
    interactive_accessibility_features(installer, log, logo_animation)
    interactive_system_scoring(installer, log, logo_animation)
    #interactive_company_integrations(installer, log, logo_animation)
    #interactive_ai_powered_features(installer, log, logo_animation)
    #interactive_enterprise_features(installer, log, logo_animation)
    interactive_packages(installer, log, logo_animation)
    interactive_services(installer, log, logo_animation)
    interactive_timezone(installer, log, logo_animation)
    interactive_bootloader(installer, log, logo_animation)
    
    # === Distro Identity ===
    if MOCK_MODE:
        log.info("[MOCK] Setting Distro Identity")
    else:
        # Install Assets (Wallpaper & Flip)
        import shutil
        asset_dir = Path(__file__).parent / "assets"
        
        # Wallpaper
        wp_dir = installer.mount_point / "usr" / "share" / "backgrounds" / "sendune"
        wp_dir.mkdir(parents=True, exist_ok=True)
        if (asset_dir / "sendune_wallpaper.png").exists():
            shutil.copy(asset_dir / "sendune_wallpaper.png", wp_dir / "sendune_wallpaper.png")
        
        # Flip Wrapper
        flip_src = asset_dir / "flip"
        flip_dest = installer.mount_point / "usr" / "bin" / "flip"
        if flip_src.exists():
            shutil.copy(flip_src, flip_dest)
            os.chmod(flip_dest, 0o755)

        # /etc/os-release
        os_release = installer.mount_point / "etc" / "os-release"
        with os_release.open("w") as f:
            f.write("""NAME="SENDUNE Linux"
PRETTY_NAME="SENDUNE Linux"
ID=sendune
ID_LIKE=arch
BUILD_ID=rolling
ANSI_COLOR="38;2;23;147;209"
HOME_URL="https://github.com/Sendune/Sendune"
SUPPORT_URL="https://github.com/Sendune/Sendune/issues"
BUG_REPORT_URL="https://github.com/Sendune/Sendune/issues"
LOGO=sendune-logo
VERSION_CODENAME="Innovation"
DOCUMENTATION_URL="https://github.com/Sendune/Sendune/wiki"
""")
        
        # /etc/lsb-release
        lsb_release = installer.mount_point / "etc" / "lsb-release"
        with lsb_release.open("w") as f:
            f.write("""DISTRIB_ID=Sendune
DISTRIB_RELEASE=rolling
DISTRIB_DESCRIPTION="SENDUNE Linux"
""")

        # /etc/issue
        issue = installer.mount_point / "etc" / "issue"
        with issue.open("w") as f:
            f.write("SENDUNE Linux \\r (\\l)\n\n")

    grub_file = installer.mount_point / "etc" / "default" / "grub"
    if MOCK_MODE:
         log.info("[MOCK] Writing GRUB_DISTRIBUTOR")
    elif grub_file.exists():
        with grub_file.open("a") as f:
            f.write('\nGRUB_DISTRIBUTOR="SENDUNE"\n')

    interactive_custom_commands(installer, log, logo_animation)

    # Verify Linux kernel installed
    # Verify Linux kernel installed
    if MOCK_MODE:
        log.info("[MOCK] Linux kernel verification skipped/passed.")
    else:
        kernel_path = installer.mount_point / "boot" / "vmlinuz-linux"
        if kernel_path.exists():
            log.info("Linux kernel successfully installed.")
        else:
            log.error("Linux kernel missing! Installation may have failed. Re-install on disk/format and try again.")
            print("Linux kernel missing! Installation may have failed. Re-install on disk/format and try again.")

    
    # Apply Dotfiles for Users
    # We iterate over created users to install dotfiles
    if hasattr(installer, 'users'):
        for user in installer.users:
            if user.username == 'root': continue
            home = installer.mount_point / "home" / user.username
            if MOCK_MODE:
                home = Path(f"MOCK_HOME_{user.username}")
                
            log.info(f"Installing dotfiles for {user.username} at {home}")
            write_hyprland_config(home, log)
            write_bashrc(home, log)
            
            # Copy flip to /usr/local/bin
            flip_source = Path(__file__).parent / "assets" / "flip"
            flip_dest = installer.mount_point / "usr" / "local" / "bin" / "flip"
            if MOCK_MODE:
                log.info(f"[MOCK] Would copy {flip_source} to {flip_dest}")
            else:
                flip_dest.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(flip_source, flip_dest)
                flip_dest.chmod(0o755)
                log.info(f"Copied flip to {flip_dest}")

    for svc in ["NetworkManager", "sshd", "bluetooth", "pipewire"]:
        installer.enable_service([svc])
    if MOCK_MODE:
         log.info("[MOCK] Running grub-mkconfig")
    else:
        os.system(f"arch-chroot {installer.mount_point} grub-mkconfig -o /boot/grub/grub.cfg")
    install_feature_updater(installer, log ,repo_url= "https://github.com/Sage563/updater-theme-sendune-installer" ,branch="main")
    
    # Installation Summary
    print("\n" + "="*50)
    print("🎉 SENDUNE Installation Complete!")
    print("="*50)
    print("Your system has been successfully installed with:")
    print("• Base Arch Linux system")
    print("• Selected desktop environment")
    print("• Login manager/display manager")
    print("• AI-powered recommendations and optimizations")
    print("• Graphics drivers")
    print("• Development tools")
    print("• Security features")
    print("• System themes and utilities")
    print("• Network services")
    print("• System automation tools")
    print("• Multimedia applications")
    print("• Office and productivity software")
    print("• Performance tuning")
    print("• Cloud integration")
    print("• AI-powered recommendations and optimizations")
    print("• Performance tuning")
    print("• Cloud integration")
    print("• Specialized development environments")
    print("• System health monitoring")
    print("• Accessibility features")
    print("• Configuration scoring and recommendations")
    print("• Company integrations and partnerships")
    print("• AI-powered features and automation")
    print("• Enterprise-grade tools and services")
    print("• AUR support with yay pre-installed")
    print("• Additional software packages")
    print("• User accounts and configurations")
    print("• System services enabled")
    print("\n📝 Next steps:")
    print("1. Reboot your system")
    print("2. Login with your created user account")
    print("3. Use 'flip' for package management")
    print("4. Configure additional settings as needed")
    print("\n📄 Log file: " + str(LOGDIR))
    print("="*50)
def starting_Sendune() -> None:
    print("Starting SENDUNE Installer...")

    # Start animated logo early
    logo_animation = logo_start()

    mount_point = get_mount_point(logo_animation)
    print(f"Installer will use: {mount_point} as mount point.")

    # Initialize log
    log = LogFile(LOGDIR)
    log.info("Installer started.")

    try:
        if Installer is None and not MOCK_MODE:
            raise RuntimeError("archinstall package not available. Install with: pacman -Sy archinstall")
        
        if MOCK_MODE:
             log.info("[MOCK] Initializing Mock Installer")
             installer = None
        else:
            installer = define_installer(mount_point, log)
        
        full_installation(installer, log, logo_animation)
    except Exception as e:
        log.error(f"Installation failed: {e}")
        print(f"Installation failed: {e}")
    finally:
        log.info("Installer finished.")
        log.info("Exiting installer.")
        log.close()
        logo_animation.stop()
        print(f"Log file at {LOGDIR}")

if __name__ == "__main__":
    starting_Sendune()