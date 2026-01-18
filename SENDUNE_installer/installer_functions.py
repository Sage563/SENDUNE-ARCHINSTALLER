import os
import sys
import platform
import subprocess
from pathlib import Path
from .custom_classes import LogFile
from .narchs_logos import input_with_pause

# ===============================
# MOCK MODE FOR WINDOWS
# ===============================
MOCK_MODE = platform.system() == "Windows"

def run_command(command, log=None):
    """
    Executes a shell command.
    If MOCK_MODE is True (Windows), prints the command instead of running it.
    """
    if MOCK_MODE:
        msg = f"[MOCK] would run: {command}"
        print(msg)
        if log:
            log.info(msg)
        return 0
    else:
        # Use subprocess for safety and better handling
        try:
            # shell=True is needed for commands like "echo ... | command" or simple strings
            # For more complex/safe usage, we should split args, but for this migration we keep it simple.
            result = subprocess.run(command, shell=True, check=False)
            return result.returncode
        except Exception as e:
            if log:
                log.error(f"Command failed: {command} - {e}")
            return 1

# Try to import archinstall...
ARCHINSTALL_AVAILABLE = True
try:
    if MOCK_MODE:
        raise ImportError("Mocking archinstall on Windows")
        
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
    from archinstall.lib.models.device import DiskLayoutType, EncryptionType
    from archinstall.lib.disk.utils import disk_layouts
    from archinstall.lib.interactions.general_conf import PostInstallationAction, ask_post_installation
except Exception:
    ARCHINSTALL_AVAILABLE = False
    class User:
        def __init__(self, username, password, is_admin=False):
            self.username = username
            self.password = password
            self.is_admin = is_admin


def ensure_archinstall_available(log: LogFile = None):
    if not ARCHINSTALL_AVAILABLE and not MOCK_MODE:
        msg = (
            "archinstall package not available. Install it before running the installer.\n"
            "On an installed Arch system run: `sudo pacman -Sy archinstall`\n"
            "Or build the ISO with archinstall included so the live environment has it."
        )
        if log:
            log.error(msg)
        raise RuntimeError(msg)
    elif MOCK_MODE:
        if log: log.info("Running in MOCK MODE (archinstall not required)")

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
# New Feature Functions
# ===============================

def interactive_graphics_drivers(installer: 'Installer', log: LogFile, logo_animation):
    """Select and install graphics drivers."""
    print("\n=== Graphics Drivers ===")
    drivers = {
        '1': ('NVIDIA (proprietary)', ['nvidia', 'nvidia-utils', 'nvidia-settings']),
        '2': ('NVIDIA (open source)', ['nvidia-open', 'nvidia-utils']),
        '3': ('AMD/ATI', ['mesa', 'xf86-video-amdgpu', 'vulkan-radeon']),
        '4': ('Intel', ['mesa', 'xf86-video-intel', 'vulkan-intel']),
        '5': ('VMware', ['xf86-video-vmware', 'mesa']),
        '6': ('VirtualBox', ['virtualbox-guest-utils', 'virtualbox-guest-modules-arch']),
        '0': ('Skip', [])
    }
    
    print("Available graphics drivers:")
    for key, (name, _) in drivers.items():
        print(f"{key}. {name}")
    
    choice = input_with_pause("Select graphics driver (0 to skip): ", logo_animation).strip()
    if choice in drivers and choice != '0':
        name, packages = drivers[choice]
        if MOCK_MODE:
            log.info(f"[MOCK] Would install {name} drivers: {packages}")
            print(f"[MOCK] Graphics drivers selected: {name}")
        else:
            installer.add_additional_packages(packages)
            log.info(f"Graphics drivers installed: {name} - {packages}")

def interactive_development_tools(installer: 'Installer', log: LogFile, logo_animation):
    """Select development tools and IDEs."""
    print("\n=== Development Tools ===")
    dev_tools = {
        '1': ('Basic Development', ['base-devel', 'gcc', 'make', 'cmake', 'git', 'python', 'python-pip']),
        '2': ('Web Development', ['nodejs', 'npm', 'yarn', 'php', 'composer', 'ruby', 'rails']),
        '3': ('Java Development', ['jdk-openjdk', 'maven', 'gradle']),
        '4': ('C/C++ Development', ['clang', 'llvm', 'gdb', 'valgrind']),
        '5': ('Python Development', ['python', 'python-pip', 'python-setuptools', 'python-virtualenv', 'jupyter']),
        '6': ('Databases', ['postgresql', 'mysql', 'sqlite', 'mongodb', 'redis']),
        '7': ('IDEs', ['code', 'vim', 'neovim', 'emacs', 'vscode']),
        '8': ('Containers', ['docker', 'docker-compose', 'podman']),
        '0': ('Skip', [])
    }
    
    print("Available development tool categories:")
    for key, (name, _) in dev_tools.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas (e.g., 1,3,5)")
    
    choices = input_with_pause("Select development tools (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()  # Use set to avoid duplicates
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in dev_tools and choice != '0':
            name, packages = dev_tools[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install development tools: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Development tools selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Development tools installed: {selected_names} - {list(selected_packages)}")

def interactive_security_hardening(installer: 'Installer', log: LogFile, logo_animation):
    """Configure security hardening options."""
    print("\n=== Security Hardening ===")
    security_options = {
        '1': ('Firewall (ufw)', ['ufw']),
        '2': ('AppArmor', ['apparmor']),
        '3': ('SELinux', ['selinux'] if not MOCK_MODE else []),
        '4': ('Fail2Ban', ['fail2ban']),
        '5': ('ClamAV Antivirus', ['clamav']),
        '6': ('Password Quality', ['libpwquality', 'pam_pwquality']),
        '7': ('Audit Framework', ['audit']),
        '0': ('Skip', [])
    }
    
    print("Available security features:")
    for key, (name, _) in security_options.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select security features (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in security_options and choice != '0':
            name, packages = security_options[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install security features: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Security features selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Security features installed: {selected_names} - {list(selected_packages)}")
            
            # Enable services for selected security features
            service_map = {
                '1': ['ufw'],  # ufw
                '2': ['apparmor'],  # AppArmor
                '4': ['fail2ban'],  # Fail2Ban
                '5': ['clamav-daemon'],  # ClamAV
                '7': ['auditd']  # Audit
            }
            for choice in choices:
                if choice.strip() in service_map:
                    installer.enable_service(service_map[choice.strip()])

def interactive_desktop_environment(installer: 'Installer', log: LogFile, logo_animation):
    """Choose desktop environment."""
    print("\n=== Desktop Environment ===")
    desktops = {
        '1': ('Hyprland (Wayland)', ['hyprland', 'wayland', 'swaybg', 'mako', 'foot', 'wl-clipboard', 'waybar', 'wofi', 'grim', 'slurp', 'polkit', 'pipewire', 'pipewire-pulse', 'xdg-desktop-portal-hyprland', 'thunar', 'hyprpaper']),
        '2': ('GNOME', ['gnome', 'gdm']),
        '3': ('KDE Plasma', ['plasma', 'sddm']),
        '4': ('XFCE', ['xfce4', 'xfce4-goodies', 'lightdm', 'lightdm-gtk-greeter']),
        '5': ('LXQt', ['lxqt', 'sddm']),
        '6': ('Cinnamon', ['cinnamon', 'lightdm', 'lightdm-gtk-greeter']),
        '7': ('MATE', ['mate', 'lightdm', 'lightdm-gtk-greeter']),
        '8': ('i3 (tiling)', ['i3', 'i3status', 'i3lock', 'dmenu', 'rxvt-unicode', 'lightdm', 'lightdm-gtk-greeter']),
        '9': ('Awesome WM', ['awesome', 'lightdm', 'lightdm-gtk-greeter']),
        '10': ('Minimal (no DE)', []),
        '0': ('Skip/Keep current', [])
    }
    
    print("Available desktop environments:")
    for key, (name, _) in desktops.items():
        print(f"{key}. {name}")
    
    choice = input_with_pause("Select desktop environment (0 to skip): ", logo_animation).strip()
    if choice in desktops and choice != '0':
        name, packages = desktops[choice]
        if MOCK_MODE:
            log.info(f"[MOCK] Would install desktop environment: {name} - {packages}")
            print(f"[MOCK] Desktop environment selected: {name}")
        else:
            # Remove existing desktop packages and add new ones
            global DESKTOP_PACKAGES
            DESKTOP_PACKAGES = packages
            installer.add_additional_packages(packages)
            log.info(f"Desktop environment installed: {name} - {packages}")
            
            # Update services based on DE choice
            if choice == '1':  # Hyprland
                installer.enable_service(['pipewire'])
            elif choice == '2':  # GNOME
                installer.enable_service(['gdm'])
            elif choice == '3':  # KDE
                installer.enable_service(['sddm'])
            elif choice in ['4', '6', '7', '8', '9']:  # LightDM based
                installer.enable_service(['lightdm'])

def interactive_locale_setup(installer: 'Installer', log: LogFile, logo_animation):
    """Configure system locale and language."""
    print("\n=== Locale and Language Setup ===")
    
    # Common locales
    locales = {
        '1': ('en_US.UTF-8', 'English (US)'),
        '2': ('en_GB.UTF-8', 'English (UK)'),
        '3': ('es_ES.UTF-8', 'Spanish (Spain)'),
        '4': ('fr_FR.UTF-8', 'French (France)'),
        '5': ('de_DE.UTF-8', 'German (Germany)'),
        '6': ('it_IT.UTF-8', 'Italian (Italy)'),
        '7': ('pt_BR.UTF-8', 'Portuguese (Brazil)'),
        '8': ('ru_RU.UTF-8', 'Russian'),
        '9': ('ja_JP.UTF-8', 'Japanese'),
        '10': ('zh_CN.UTF-8', 'Chinese (Simplified)'),
        '11': ('ko_KR.UTF-8', 'Korean'),
        '12': ('ar_SA.UTF-8', 'Arabic (Saudi Arabia)'),
        '13': ('hi_IN.UTF-8', 'Hindi (India)'),
        '0': ('Skip', '')
    }
    
    print("Available locales:")
    for key, (locale, name) in locales.items():
        print(f"{key}. {name} ({locale})")
    
    choice = input_with_pause("Select system locale (0 to skip): ", logo_animation).strip()
    if choice in locales and choice != '0':
        locale_code, name = locales[choice]
        if MOCK_MODE:
            log.info(f"[MOCK] Would set locale to: {locale_code} ({name})")
            print(f"[MOCK] Locale selected: {name}")
        else:
            # Generate locale
            run_command(f"echo '{locale_code} UTF-8' >> /etc/locale.gen", log)
            run_command("locale-gen", log)
            run_command(f"echo 'LANG={locale_code}' > /etc/locale.conf", log)
            log.info(f"Locale set to: {locale_code} ({name})")

def interactive_login_manager(installer: 'Installer', log: LogFile, logo_animation):
    """Choose and configure login manager/display manager."""
    print("\n=== Login Manager (Display Manager) ===")
    managers = {
        '1': ('LightDM', ['lightdm', 'lightdm-gtk-greeter']),
        '2': ('GDM (GNOME)', ['gdm']),
        '3': ('SDDM (KDE)', ['sddm']),
        '4': ('LXDM', ['lxdm']),
        '5': ('XDM', ['xorg-xdm']),
        '6': ('No Display Manager (Console only)', []),
        '0': ('Skip', [])
    }
    
    print("Available login managers:")
    for key, (name, _) in managers.items():
        print(f"{key}. {name}")
    
    choice = input_with_pause("Select login manager (0 to skip): ", logo_animation).strip()
    if choice in managers and choice != '0':
        name, packages = managers[choice]
        if MOCK_MODE:
            log.info(f"[MOCK] Would install login manager: {name} - {packages}")
            print(f"[MOCK] Login manager selected: {name}")
        else:
            installer.add_additional_packages(packages)
            log.info(f"Login manager installed: {name} - {packages}")
            
            # Enable the appropriate service
            service_map = {
                '1': ['lightdm'],
                '2': ['gdm'],
                '3': ['sddm'],
                '4': ['lxdm'],
                '5': ['xdm']
            }
            if choice in service_map:
                installer.enable_service(service_map[choice])

def interactive_system_themes(installer: 'Installer', log: LogFile, logo_animation):
    """Select system themes, icons, and fonts."""
    print("\n=== System Themes and Appearance ===")
    themes = {
        '1': ('Arc Theme', ['arc-gtk-theme']),
        '2': ('Adwaita (GNOME default)', []),
        '3': ('Breeze (KDE)', ['breeze-gtk']),
        '4': ('Numix Theme', ['numix-gtk-theme', 'numix-icon-theme']),
        '5': ('Papirus Icons', ['papirus-icon-theme']),
        '6': ('Additional Fonts', ['ttf-dejavu', 'ttf-liberation', 'ttf-ubuntu-font-family', 'noto-fonts', 'noto-fonts-emoji']),
        '7': ('Microsoft Fonts', ['ttf-ms-fonts']),
        '8': ('Monospace Fonts', ['ttf-fira-code', 'ttf-jetbrains-mono', 'ttf-sourcecodepro']),
        '0': ('Skip', [])
    }
    
    print("Available themes and fonts:")
    for key, (name, _) in themes.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select themes/fonts (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in themes and choice != '0':
            name, packages = themes[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install themes/fonts: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Themes/fonts selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Themes/fonts installed: {selected_names} - {list(selected_packages)}")

def interactive_system_utilities(installer: 'Installer', log: LogFile, logo_animation):
    """Select system utilities and tools."""
    print("\n=== System Utilities ===")
    utilities = {
        '1': ('Archive Tools', ['zip', 'unzip', 'p7zip', 'rar', 'unrar']),
        '2': ('File Managers', ['thunar', 'pcmanfm', 'dolphin', 'nautilus']),
        '3': ('Terminal Emulators', ['alacritty', 'kitty', 'terminator', 'tilix']),
        '4': ('Text Editors', ['gedit', 'kate', 'mousepad', 'leafpad']),
        '5': ('System Monitors', ['htop', 'nvtop', 'bashtop', 'gotop']),
        '6': ('Disk Tools', ['gparted', 'gnome-disk-utility', 'baobab']),
        '7': ('Network Tools', ['wireshark-qt', 'nmap', 'traceroute', 'net-tools', 'inetutils']),
        '8': ('Development Utils', ['git', 'curl', 'wget', 'rsync', 'openssh']),
        '9': ('Power Management', ['tlp', 'powertop', 'acpi', 'acpid']),
        '10': ('Bluetooth Tools', ['blueman', 'bluez-tools']),
        '0': ('Skip', [])
    }
    
    print("Available system utilities:")
    for key, (name, _) in utilities.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select utilities (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in utilities and choice != '0':
            name, packages = utilities[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install utilities: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Utilities selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Utilities installed: {selected_names} - {list(selected_packages)}")
            
            # Enable services for selected utilities
            service_map = {
                '9': ['tlp', 'acpid'],  # Power management
                '10': ['bluetooth']  # Bluetooth
            }
            for choice in choices:
                if choice.strip() in service_map:
                    installer.enable_service(service_map[choice.strip()])

def interactive_network_services(installer: 'Installer', log: LogFile, logo_animation):
    """Configure network services and sharing."""
    print("\n=== Network Services ===")
    services = {
        '1': ('Samba (File Sharing)', ['samba']),
        '2': ('NFS (Network File System)', ['nfs-utils']),
        '3': ('OpenVPN', ['openvpn']),
        '4': ('WireGuard', ['wireguard-tools']),
        '5': ('Avahi (Zeroconf)', ['avahi', 'nss-mdns']),
        '6': ('NetworkManager VPN', ['networkmanager-openvpn', 'networkmanager-vpnc']),
        '7': ('SSH Server', ['openssh']),
        '8': ('FTP Server', ['vsftpd']),
        '9': ('Web Server (Apache)', ['apache']),
        '10': ('Web Server (Nginx)', ['nginx']),
        '0': ('Skip', [])
    }
    
    print("Available network services:")
    for key, (name, _) in services.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select network services (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in services and choice != '0':
            name, packages = services[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install network services: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Network services selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Network services installed: {selected_names} - {list(selected_packages)}")
            
            # Enable services for selected network services
            service_map = {
                '1': ['smbd', 'nmbd'],  # Samba
                '5': ['avahi-daemon'],  # Avahi
                '7': ['sshd'],  # SSH
                '8': ['vsftpd'],  # FTP
                '9': ['httpd'],  # Apache
                '10': ['nginx']  # Nginx
            }
            for choice in choices:
                if choice.strip() in service_map:
                    installer.enable_service(service_map[choice.strip()])

def interactive_system_automation(installer: 'Installer', log: LogFile, logo_animation):
    """Configure system automation and maintenance."""
    print("\n=== System Automation ===")
    automation = {
        '1': ('Cron (Task Scheduler)', ['cronie']),
        '2': ('Anacron (Periodic Tasks)', ['anacron']),
        '3': ('Logrotate', ['logrotate']),
        '4': ('Automatic Updates', ['pacman-contrib']),  # For paccache timer
        '5': ('Backup Scripts', ['rsync', 'borgbackup']),
        '6': ('System Monitoring', ['prometheus', 'grafana']),
        '7': ('Fail2Ban', ['fail2ban']),
        '8': ('UFW Firewall', ['ufw']),
        '9': ('ClamAV Antivirus', ['clamav']),
        '10': ('AIDE (Intrusion Detection)', ['aide']),
        '0': ('Skip', [])
    }
    
    print("Available automation and maintenance tools:")
    for key, (name, _) in automation.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select automation tools (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in automation and choice != '0':
            name, packages = automation[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install automation tools: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Automation tools selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Automation tools installed: {selected_names} - {list(selected_packages)}")
            
            # Enable services for selected automation tools
            service_map = {
                '1': ['cronie'],  # Cron
                '7': ['fail2ban'],  # Fail2Ban
                '8': ['ufw'],  # UFW
                '9': ['clamav-daemon']  # ClamAV
            }
            for choice in choices:
                if choice.strip() in service_map:
                    installer.enable_service(service_map[choice.strip()])

def interactive_multimedia_tools(installer: 'Installer', log: LogFile, logo_animation):
    """Select multimedia tools and codecs."""
    print("\n=== Multimedia Tools ===")
    multimedia = {
        '1': ('Audio Codecs', ['gst-plugins-base', 'gst-plugins-good', 'gst-plugins-bad', 'gst-plugins-ugly']),
        '2': ('Video Codecs', ['ffmpeg', 'libva-mesa-driver', 'libva-intel-driver']),
        '3': ('Audio Players', ['vlc', 'audacious', 'rhythmbox', 'clementine']),
        '4': ('Video Players', ['mpv', 'smplayer', 'totem']),
        '5': ('Music Production', ['audacity', 'lmms', 'ardour']),
        '6': ('Image Editors', ['gimp', 'krita', 'inkscape']),
        '7': ('3D Graphics', ['blender', 'freecad']),
        '8': ('Screen Recording', ['obs-studio', 'simplescreenrecorder']),
        '9': ('CD/DVD Tools', ['asunder', 'brasero', 'k3b']),
        '10': ('Streaming', ['streamlink', 'youtube-dl']),
        '0': ('Skip', [])
    }
    
    print("Available multimedia tools:")
    for key, (name, _) in multimedia.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select multimedia tools (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in multimedia and choice != '0':
            name, packages = multimedia[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install multimedia tools: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Multimedia tools selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Multimedia tools installed: {selected_names} - {list(selected_packages)}")

def interactive_ai_assistant(installer: 'Installer', log: LogFile, logo_animation):
    """AI-powered installation assistant with intelligent recommendations."""
    print("\n🤖 === AI Installation Assistant ===")
    print("Let me help you create the perfect system configuration!")
    
    # Hardware detection
    print("\n🔍 Detecting your hardware...")
    hardware_info = detect_hardware()
    
    # Usage profile selection
    profiles = {
        '1': ('Gaming PC', 'gaming'),
        '2': ('Developer Workstation', 'development'),
        '3': ('Creative Studio', 'creative'),
        '4': ('Office/Productivity', 'office'),
        '5': ('Media Center', 'media'),
        '6': ('Server/NAS', 'server'),
        '7': ('Minimal System', 'minimal'),
        '8': ('Privacy-Focused', 'privacy'),
        '9': ('Educational', 'educational'),
        '10': ('Custom (Manual Selection)', 'custom')
    }
    
    print("\n🎯 Choose your primary use case:")
    for key, (name, _) in profiles.items():
        print(f"{key}. {name}")
    
    choice = input_with_pause("Select profile (1-10): ", logo_animation).strip()
    if choice in profiles:
        profile_name, profile_type = profiles[choice]
        if profile_type != 'custom':
            recommendations = get_ai_recommendations(profile_type, hardware_info)
            apply_recommendations(installer, recommendations, log, logo_animation)
        else:
            print("Proceeding with manual configuration...")
    else:
        print("Invalid choice, proceeding with manual configuration...")

def detect_hardware():
    """Detect system hardware for intelligent recommendations."""
    hardware = {
        'cpu': 'unknown',
        'gpu': 'unknown',
        'ram': 'unknown',
        'storage': 'unknown',
        'display': 'unknown'
    }
    
    try:
        # CPU detection
        with open('/proc/cpuinfo', 'r') as f:
            cpu_info = f.read()
            if 'Intel' in cpu_info:
                hardware['cpu'] = 'intel'
            elif 'AMD' in cpu_info:
                hardware['cpu'] = 'amd'
        
        # GPU detection (simplified)
        try:
            result = run_command("lspci | grep VGA")
            if 'NVIDIA' in result:
                hardware['gpu'] = 'nvidia'
            elif 'AMD' in result or 'ATI' in result:
                hardware['gpu'] = 'amd'
            elif 'Intel' in result:
                hardware['gpu'] = 'intel'
        except:
            pass
            
        # RAM detection
        with open('/proc/meminfo', 'r') as f:
            mem_info = f.read()
            for line in mem_info.split('\n'):
                if line.startswith('MemTotal:'):
                    ram_kb = int(line.split()[1])
                    ram_gb = ram_kb // (1024 * 1024)
                    hardware['ram'] = f"{ram_gb}GB"
                    break
                    
    except Exception as e:
        print(f"Hardware detection limited: {e}")
    
    return hardware

def get_ai_recommendations(profile_type, hardware):
    """Generate intelligent recommendations based on profile and hardware."""
    recommendations = {
        'desktop': 'hyprland',
        'packages': [],
        'services': [],
        'optimizations': []
    }
    
    if profile_type == 'gaming':
        recommendations['desktop'] = 'plasma'
        recommendations['packages'] = [
            'steam', 'lutris', 'wine', 'proton-ge-custom', 'mangohud', 'gamemode',
            'vulkan-icd-loader', 'lib32-vulkan-icd-loader', 'vkd3d', 'lib32-vkd3d',
            'discord', 'obs-studio', 'feral-gamemode'
        ]
        recommendations['services'] = ['gamemoded']
        recommendations['optimizations'] = ['gaming_performance', 'nvidia_optimizations' if hardware['gpu'] == 'nvidia' else 'amd_optimizations']
        
    elif profile_type == 'development':
        recommendations['desktop'] = 'gnome'
        recommendations['packages'] = [
            'code', 'git', 'docker', 'docker-compose', 'python', 'nodejs', 'npm',
            'go', 'rust', 'jdk-openjdk', 'maven', 'gradle', 'postgresql', 'mongodb',
            'redis', 'mysql', 'sqlitebrowser', 'postman', 'insomnia', 'dbeaver'
        ]
        recommendations['services'] = ['docker']
        recommendations['optimizations'] = ['developer_tools', 'container_runtime']
        
    elif profile_type == 'creative':
        recommendations['desktop'] = 'gnome'
        recommendations['packages'] = [
            'gimp', 'krita', 'inkscape', 'blender', 'audacity', 'lmms', 'ardour',
            'kdenlive', 'openshot', 'shotcut', 'darktable', 'rawtherapee',
            'scribus', 'libreoffice-fresh', 'fontforge', 'mypaint'
        ]
        recommendations['optimizations'] = ['creative_performance', 'multimedia_codecs']
        
    elif profile_type == 'office':
        recommendations['desktop'] = 'gnome'
        recommendations['packages'] = [
            'libreoffice-fresh', 'thunderbird', 'firefox', 'chromium', 'evince',
            'okular', 'masterpdfeditor-free', 'calibre', 'thunar', 'vlc',
            'keepassxc', 'nextcloud-client', 'zoom', 'teams'
        ]
        recommendations['optimizations'] = ['office_productivity']
        
    elif profile_type == 'media':
        recommendations['desktop'] = 'kde'
        recommendations['packages'] = [
            'vlc', 'mpv', 'kodi', 'plex-media-server', 'emby-server', 'jellyfin',
            'handbrake', 'makemkv', 'stremio', 'spotify', 'youtube-dl'
        ]
        recommendations['services'] = ['plexmediaserver', 'emby-server']
        recommendations['optimizations'] = ['multimedia_performance']
        
    elif profile_type == 'server':
        recommendations['desktop'] = 'none'
        recommendations['packages'] = [
            'openssh', 'ufw', 'fail2ban', 'docker', 'docker-compose', 'nginx',
            'apache', 'mariadb', 'postgresql', 'php', 'python', 'nodejs',
            'cockpit', 'webmin', 'samba', 'nfs-utils', 'rsync', 'borgbackup'
        ]
        recommendations['services'] = ['sshd', 'ufw', 'fail2ban', 'docker']
        recommendations['optimizations'] = ['server_security', 'server_performance']
        
    elif profile_type == 'minimal':
        recommendations['desktop'] = 'none'
        recommendations['packages'] = [
            'vim', 'git', 'curl', 'wget', 'htop', 'neofetch', 'alacritty'
        ]
        recommendations['optimizations'] = ['minimal_resources']
        
    elif profile_type == 'privacy':
        recommendations['desktop'] = 'gnome'
        recommendations['packages'] = [
            'tor', 'tor-browser', 'protonvpn', 'mullvad-vpn', 'keepassxc',
            'veracrypt', 'bleachbit', 'firejail', 'apparmor', 'ufw', 'clamav',
            'rkhunter', 'lynis', ' onionshare', 'torbrowser-launcher'
        ]
        recommendations['services'] = ['tor', 'ufw', 'apparmor', 'clamav-daemon']
        recommendations['optimizations'] = ['privacy_hardening', 'security_focused']
        
    elif profile_type == 'educational':
        recommendations['desktop'] = 'gnome'
        recommendations['packages'] = [
            'geogebra', 'maxima', 'octave', 'r', 'jupyter-notebook', 'python-jupyterlab',
            'libreoffice-fresh', 'gimp', 'audacity', 'stellarium', 'kstars',
            'anki', 'calibre', 'thunderbird', 'firefox'
        ]
        recommendations['optimizations'] = ['educational_tools']
    
    return recommendations

def apply_recommendations(installer, recommendations, log, logo_animation):
    """Apply AI-generated recommendations to the installation."""
    print(f"\n🎯 Applying {recommendations.get('profile', 'custom')} recommendations...")
    
    # Set desktop environment
    if 'desktop' in recommendations and recommendations['desktop'] != 'none':
        desktop_map = {
            'hyprland': ['hyprland', 'wayland', 'swaybg', 'mako', 'foot', 'wl-clipboard',
                        'waybar', 'wofi', 'grim', 'slurp', 'polkit', 'pipewire',
                        'pipewire-pulse', 'xdg-desktop-portal-hyprland', 'hyprpaper'],
            'gnome': ['gnome', 'gnome-extra', 'gdm'],
            'kde': ['plasma', 'plasma-wayland-session', 'sddm', 'konsole', 'dolphin'],
            'xfce': ['xfce4', 'xfce4-goodies', 'lightdm', 'lightdm-gtk-greeter'],
            'plasma': ['plasma', 'plasma-wayland-session', 'sddm', 'konsole', 'dolphin']
        }
        
        if recommendations['desktop'] in desktop_map:
            installer.add_additional_packages(desktop_map[recommendations['desktop']])
            log.info(f"AI recommended desktop: {recommendations['desktop']}")
    
    # Add recommended packages
    if 'packages' in recommendations:
        installer.add_additional_packages(recommendations['packages'])
        log.info(f"AI recommended packages: {recommendations['packages']}")
    
    # Enable recommended services
    if 'services' in recommendations:
        for service in recommendations['services']:
            installer.enable_service([service])
        log.info(f"AI recommended services: {recommendations['services']}")
    
    # Apply optimizations
    if 'optimizations' in recommendations:
        apply_optimizations(installer, recommendations['optimizations'], log)
    
    print("✅ AI recommendations applied successfully!")

def apply_optimizations(installer, optimizations, log):
    """Apply system optimizations based on recommendations."""
    for opt in optimizations:
        if opt == 'gaming_performance':
            installer.add_additional_packages(['gamemode', 'mangohud', 'proton-ge-custom'])
            installer.enable_service(['gamemoded'])
            log.info("Applied gaming performance optimizations")
            
        elif opt == 'nvidia_optimizations':
            installer.add_additional_packages(['nvidia', 'nvidia-utils', 'lib32-nvidia-utils', 'nvidia-settings'])
            log.info("Applied NVIDIA optimizations")
            
        elif opt == 'amd_optimizations':
            installer.add_additional_packages(['mesa', 'lib32-mesa', 'vulkan-radeon', 'lib32-vulkan-radeon'])
            log.info("Applied AMD optimizations")
            
        elif opt == 'developer_tools':
            installer.add_additional_packages(['base-devel', 'git', 'python', 'nodejs', 'go', 'rust'])
            log.info("Applied developer tools")
            
        elif opt == 'container_runtime':
            installer.add_additional_packages(['docker', 'docker-compose', 'podman'])
            installer.enable_service(['docker'])
            log.info("Applied container runtime")
            
        elif opt == 'creative_performance':
            installer.add_additional_packages(['ffmpeg', 'libva-mesa-driver', 'intel-media-driver'])
            log.info("Applied creative performance optimizations")
            
        elif opt == 'multimedia_codecs':
            installer.add_additional_packages(['gst-plugins-base', 'gst-plugins-good', 'gst-plugins-bad', 'gst-plugins-ugly'])
            log.info("Applied multimedia codecs")
            
        elif opt == 'office_productivity':
            installer.add_additional_packages(['libreoffice-fresh', 'hunspell', 'hyphen'])
            log.info("Applied office productivity tools")
            
        elif opt == 'multimedia_performance':
            installer.add_additional_packages(['ffmpeg', 'mpv', 'vlc', 'intel-media-driver'])
            log.info("Applied multimedia performance")
            
        elif opt == 'server_security':
            installer.add_additional_packages(['ufw', 'fail2ban', 'apparmor'])
            installer.enable_service(['ufw', 'fail2ban', 'apparmor'])
            log.info("Applied server security")
            
        elif opt == 'server_performance':
            installer.add_additional_packages(['nginx', 'mariadb', 'postgresql'])
            log.info("Applied server performance")
            
        elif opt == 'minimal_resources':
            # Minimal setup - don't add extra packages
            log.info("Applied minimal resource configuration")
            
        elif opt == 'privacy_hardening':
            installer.add_additional_packages(['tor', 'tor-browser', 'keepassxc', 'veracrypt'])
            installer.enable_service(['tor'])
            log.info("Applied privacy hardening")
            
        elif opt == 'security_focused':
            installer.add_additional_packages(['apparmor', 'ufw', 'clamav', 'rkhunter'])
            installer.enable_service(['apparmor', 'ufw', 'clamav-daemon'])
            log.info("Applied security focused configuration")
            
        elif opt == 'educational_tools':
            installer.add_additional_packages(['geogebra', 'maxima', 'octave', 'jupyter-notebook'])
            log.info("Applied educational tools")

def interactive_performance_tuning(installer: 'Installer', log: LogFile, logo_animation):
    """Advanced performance tuning options."""
    print("\n⚡ === Performance Tuning ===")
    
    tuning_options = {
        '1': ('CPU Governor Optimization', 'cpu_governor'),
        '2': ('I/O Scheduler Tuning', 'io_scheduler'),
        '3': ('Memory Management', 'memory_tuning'),
        '4': ('Network Optimization', 'network_tuning'),
        '5': ('Storage Optimization', 'storage_tuning'),
        '6': ('Gaming Performance', 'gaming_tuning'),
        '7': ('Battery Optimization', 'battery_saving'),
        '8': ('Thermal Management', 'thermal_control'),
        '0': ('Skip', 'skip')
    }
    
    print("Advanced performance tuning options:")
    for key, (name, _) in tuning_options.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select tuning options (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_tunings = []

    for choice in choices:
        choice = choice.strip()
        if choice in tuning_options and choice != '0':
            name, tuning_type = tuning_options[choice]
            selected_tunings.append(tuning_type)
        elif choice == '0':
            break

    if selected_tunings:
        apply_performance_tunings(installer, selected_tunings, log)

def apply_performance_tunings(installer, tunings, log):
    """Apply selected performance tunings."""
    for tuning in tunings:
        if tuning == 'cpu_governor':
            installer.add_additional_packages(['cpupower'])
            log.info("Added CPU governor optimization tools")
            
        elif tuning == 'io_scheduler':
            # I/O scheduler is kernel parameter, add tools for monitoring
            installer.add_additional_packages(['iotop', 'sysstat'])
            log.info("Added I/O monitoring tools")
            
        elif tuning == 'memory_tuning':
            installer.add_additional_packages(['earlyoom', 'zram-generator'])
            installer.enable_service(['earlyoom', 'zramd'])
            log.info("Applied memory management optimizations")
            
        elif tuning == 'network_tuning':
            installer.add_additional_packages(['ethtool', 'iperf3', 'net-tools'])
            log.info("Added network tuning tools")
            
        elif tuning == 'storage_tuning':
            installer.add_additional_packages(['hdparm', 'smartmontools', 'fio'])
            log.info("Added storage tuning tools")
            
        elif tuning == 'gaming_tuning':
            installer.add_additional_packages(['gamemode', 'mangohud', 'feral-gamemode'])
            installer.enable_service(['gamemoded'])
            log.info("Applied gaming performance tuning")
            
        elif tuning == 'battery_saving':
            installer.add_additional_packages(['tlp', 'powertop'])
            installer.enable_service(['tlp'])
            log.info("Applied battery optimization")
            
        elif tuning == 'thermal_control':
            installer.add_additional_packages(['lm_sensors', 'thermald'])
            installer.enable_service(['thermald'])
            log.info("Applied thermal management")

def interactive_cloud_integration(installer: 'Installer', log: LogFile, logo_animation):
    """Cloud platform integration and deployment options."""
    print("\n☁️ === Cloud Integration ===")
    
    cloud_options = {
        '1': ('AWS CLI & Tools', 'aws'),
        '2': ('Azure CLI & Tools', 'azure'),
        '3': ('Google Cloud SDK', 'gcp'),
        '4': ('Docker & Kubernetes', 'kubernetes'),
        '5': ('Terraform', 'terraform'),
        '6': ('Ansible', 'ansible'),
        '7': ('Pulumi', 'pulumi'),
        '8': ('Cloud-Init Support', 'cloud_init'),
        '0': ('Skip', 'skip')
    }
    
    print("Cloud platform integration:")
    for key, (name, _) in cloud_options.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select cloud integrations (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_cloud = []

    for choice in choices:
        choice = choice.strip()
        if choice in cloud_options and choice != '0':
            name, cloud_type = cloud_options[choice]
            selected_cloud.append(cloud_type)
        elif choice == '0':
            break

    if selected_cloud:
        apply_cloud_integration(installer, selected_cloud, log)

def apply_cloud_integration(installer, clouds, log):
    """Apply selected cloud integrations."""
    for cloud in clouds:
        if cloud == 'aws':
            installer.add_additional_packages(['aws-cli-v2', 'aws-vault'])
            log.info("Added AWS CLI and tools")
            
        elif cloud == 'azure':
            installer.add_additional_packages(['azure-cli', 'azure-functions-core-tools'])
            log.info("Added Azure CLI and tools")
            
        elif cloud == 'gcp':
            installer.add_additional_packages(['google-cloud-sdk'])
            log.info("Added Google Cloud SDK")
            
        elif cloud == 'kubernetes':
            installer.add_additional_packages(['kubectl', 'kubelet', 'kubeadm', 'kubernetes-cni', 'docker'])
            installer.enable_service(['docker'])
            log.info("Added Kubernetes tools")
            
        elif cloud == 'terraform':
            installer.add_additional_packages(['terraform'])
            log.info("Added Terraform")
            
        elif cloud == 'ansible':
            installer.add_additional_packages(['ansible', 'ansible-core'])
            log.info("Added Ansible")
            
        elif cloud == 'pulumi':
            installer.add_additional_packages(['pulumi'])
            log.info("Added Pulumi")
            
        elif cloud == 'cloud_init':
            installer.add_additional_packages(['cloud-init'])
            log.info("Added Cloud-Init support")

def interactive_specialized_environments(installer: 'Installer', log: LogFile, logo_animation):
    """Specialized environment setups."""
    print("\n🔬 === Specialized Environments ===")
    
    env_options = {
        '1': ('AI/ML Development Stack', 'ai_ml'),
        '2': ('Data Science Environment', 'data_science'),
        '3': ('Game Development', 'game_dev'),
        '4': ('Audio Production Studio', 'audio_production'),
        '5': ('Video Editing Suite', 'video_editing'),
        '6': ('3D Animation/Rendering', '3d_animation'),
        '7': ('Web Development Stack', 'web_dev'),
        '8': ('Mobile Development', 'mobile_dev'),
        '9': ('IoT Development', 'iot_dev'),
        '10': ('Embedded Systems', 'embedded'),
        '0': ('Skip', 'skip')
    }
    
    print("Specialized development environments:")
    for key, (name, _) in env_options.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select environments (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_envs = []

    for choice in choices:
        choice = choice.strip()
        if choice in env_options and choice != '0':
            name, env_type = env_options[choice]
            selected_envs.append(env_type)
        elif choice == '0':
            break

    if selected_envs:
        apply_specialized_environments(installer, selected_envs, log)

def apply_specialized_environments(installer, environments, log):
    """Apply selected specialized environments."""
    for env in environments:
        if env == 'ai_ml':
            installer.add_additional_packages([
                'python', 'python-pytorch', 'python-tensorflow', 'python-jupyterlab',
                'python-scikit-learn', 'python-pandas', 'python-numpy', 'python-matplotlib',
                'python-opencv', 'cudnn', 'cuda', 'nvidia-docker'
            ])
            log.info("Added AI/ML development stack")
            
        elif env == 'data_science':
            installer.add_additional_packages([
                'r', 'rstudio-desktop', 'python-jupyterlab', 'python-pandas',
                'python-numpy', 'python-scipy', 'python-matplotlib', 'python-seaborn',
                'postgresql', 'mongodb', 'redis', 'sqlite'
            ])
            log.info("Added data science environment")
            
        elif env == 'game_dev':
            installer.add_additional_packages([
                'godot', 'unityhub', 'blender', 'krita', 'audacity', 'lmms',
                'python', 'love', 'renpy', 'tiled', 'aseprite'
            ])
            log.info("Added game development tools")
            
        elif env == 'audio_production':
            installer.add_additional_packages([
                'ardour', 'audacity', 'lmms', 'hydrogen', 'calf', 'lsp-plugins',
                'jack2', 'qjackctl', 'pulseaudio-jack', 'realtime-privileges'
            ])
            log.info("Added audio production studio")
            
        elif env == 'video_editing':
            installer.add_additional_packages([
                'kdenlive', 'shotcut', 'openshot', 'blender', 'natron',
                'ffmpeg', 'handbrake', 'obs-studio', 'simplescreenrecorder'
            ])
            log.info("Added video editing suite")
            
        elif env == '3d_animation':
            installer.add_additional_packages([
                'blender', 'krita', 'inkscape', 'gimp', 'synfigstudio',
                'natron', 'opentoonz', 'pencil2d'
            ])
            log.info("Added 3D animation/rendering tools")
            
        elif env == 'web_dev':
            installer.add_additional_packages([
                'code', 'firefox', 'chromium', 'nodejs', 'npm', 'yarn',
                'python', 'php', 'apache', 'nginx', 'mariadb', 'postgresql',
                'docker', 'docker-compose', 'postman', 'insomnia'
            ])
            log.info("Added web development stack")
            
        elif env == 'mobile_dev':
            installer.add_additional_packages([
                'android-studio', 'android-tools', 'android-udev',
                'flutter', 'dart', 'react-native', 'ionic', 'cordova',
                'scrcpy', 'android-file-transfer'
            ])
            log.info("Added mobile development tools")
            
        elif env == 'iot_dev':
            installer.add_additional_packages([
                'arduino', 'arduino-cli', 'platformio', 'mosquitto',
                'nodejs', 'python', 'wiringpi', 'raspberrypi-firmware',
                'bluez', 'bluez-tools'
            ])
            log.info("Added IoT development tools")
            
        elif env == 'embedded':
            installer.add_additional_packages([
                'gcc-arm-none-eabi', 'openocd', 'qemu', 'gdb', 'minicom',
                'picocom', 'stm32cubemx', 'segger-jlink', 'platformio'
            ])
            log.info("Added embedded systems development tools")

def interactive_system_health_monitoring(installer: 'Installer', log: LogFile, logo_animation):
    """System health monitoring and maintenance setup."""
    print("\n🏥 === System Health Monitoring ===")
    
    monitoring_options = {
        '1': ('System Monitoring (htop, nvtop)', 'system_monitor'),
        '2': ('Hardware Monitoring (lm-sensors)', 'hardware_monitor'),
        '3': ('Network Monitoring (vnstat, nload)', 'network_monitor'),
        '4': ('Storage Monitoring (smartmontools)', 'storage_monitor'),
        '5': ('Security Monitoring (rkhunter, chkrootkit)', 'security_monitor'),
        '6': ('Performance Monitoring (perf, sysstat)', 'performance_monitor'),
        '7': ('Log Monitoring (logwatch, swatch)', 'log_monitor'),
        '8': ('Automated Maintenance (cron jobs)', 'automated_maintenance'),
        '0': ('Skip', 'skip')
    }
    
    print("System health monitoring options:")
    for key, (name, _) in monitoring_options.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select monitoring options (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_monitoring = []

    for choice in choices:
        choice = choice.strip()
        if choice in monitoring_options and choice != '0':
            name, monitor_type = monitoring_options[choice]
            selected_monitoring.append(monitor_type)
        elif choice == '0':
            break

    if selected_monitoring:
        apply_system_monitoring(installer, selected_monitoring, log)

def apply_system_monitoring(installer, monitoring, log):
    """Apply selected system monitoring."""
    for monitor in monitoring:
        if monitor == 'system_monitor':
            installer.add_additional_packages(['htop', 'nvtop', 'bashtop', 'gotop'])
            log.info("Added system monitoring tools")
            
        elif monitor == 'hardware_monitor':
            installer.add_additional_packages(['lm_sensors', 'psensor', 'hardinfo'])
            log.info("Added hardware monitoring")
            
        elif monitor == 'network_monitor':
            installer.add_additional_packages(['vnstat', 'nload', 'iftop', 'iptraf-ng'])
            installer.enable_service(['vnstat'])
            log.info("Added network monitoring")
            
        elif monitor == 'storage_monitor':
            installer.add_additional_packages(['smartmontools', 'gsmartcontrol', 'hdparm'])
            log.info("Added storage monitoring")
            
        elif monitor == 'security_monitor':
            installer.add_additional_packages(['rkhunter', 'chkrootkit', 'lynis', 'tiger'])
            log.info("Added security monitoring")
            
        elif monitor == 'performance_monitor':
            installer.add_additional_packages(['perf', 'sysstat', 'iotop', 'latencytop'])
            log.info("Added performance monitoring")
            
        elif monitor == 'log_monitor':
            installer.add_additional_packages(['logwatch', 'swatch', 'multitail'])
            log.info("Added log monitoring")
            
        elif monitor == 'automated_maintenance':
            installer.add_additional_packages(['cronie', 'anacron', 'logrotate'])
            installer.enable_service(['cronie'])
            log.info("Added automated maintenance")

def calculate_system_score(installer, log):
    """Calculate and display a system configuration score with recommendations."""
    print("\n📊 === System Configuration Score ===")
    
    score = 0
    max_score = 100
    recommendations = []
    
    # Check desktop environment
    if hasattr(installer, 'desktop_packages') and installer.desktop_packages:
        score += 15
        print("✅ Desktop Environment: Configured (+15 points)")
    else:
        recommendations.append("Consider adding a desktop environment for better usability")
        print("⚠️  Desktop Environment: Not configured (0 points)")
    
    # Check graphics drivers
    graphics_packages = [pkg for pkg in installer.additional_packages if any(gpu in pkg.lower() for gpu in ['nvidia', 'amd', 'intel', 'mesa', 'vulkan'])]
    if graphics_packages:
        score += 15
        print("✅ Graphics Drivers: Configured (+15 points)")
    else:
        recommendations.append("Install graphics drivers for optimal display performance")
        print("⚠️  Graphics Drivers: Not configured (0 points)")
    
    # Check development tools
    dev_tools = [pkg for pkg in installer.additional_packages if any(dev in pkg.lower() for dev in ['gcc', 'python', 'nodejs', 'git', 'code', 'vim'])]
    if len(dev_tools) >= 3:
        score += 15
        print("✅ Development Tools: Well configured (+15 points)")
    elif len(dev_tools) >= 1:
        score += 10
        print("✅ Development Tools: Basic setup (+10 points)")
    else:
        recommendations.append("Consider installing development tools for software development")
        print("⚠️  Development Tools: Not configured (0 points)")
    
    # Check security features
    security_tools = [pkg for pkg in installer.additional_packages if any(sec in pkg.lower() for sec in ['ufw', 'fail2ban', 'apparmor', 'clamav', 'firejail'])]
    if len(security_tools) >= 3:
        score += 15
        print("✅ Security Features: Comprehensive (+15 points)")
    elif len(security_tools) >= 1:
        score += 10
        print("✅ Security Features: Basic setup (+10 points)")
    else:
        recommendations.append("Consider adding security tools for better system protection")
        print("⚠️  Security Features: Not configured (0 points)")
    
    # Check system utilities
    system_utils = [pkg for pkg in installer.additional_packages if any(util in pkg.lower() for util in ['htop', 'neofetch', 'tlp', 'lm_sensors', 'smartmontools'])]
    if len(system_utils) >= 3:
        score += 10
        print("✅ System Utilities: Well configured (+10 points)")
    elif len(system_utils) >= 1:
        score += 5
        print("✅ System Utilities: Basic setup (+5 points)")
    else:
        recommendations.append("Consider installing system monitoring utilities")
        print("⚠️  System Utilities: Not configured (0 points)")
    
    # Check network services
    network_services = [pkg for pkg in installer.additional_packages if any(net in pkg.lower() for net in ['openssh', 'networkmanager', 'bluez', 'samba', 'nfs'])]
    if len(network_services) >= 3:
        score += 10
        print("✅ Network Services: Well configured (+10 points)")
    elif len(network_services) >= 1:
        score += 5
        print("✅ Network Services: Basic setup (+5 points)")
    else:
        recommendations.append("Consider configuring network services for connectivity")
        print("⚠️  Network Services: Not configured (0 points)")
    
    # Check multimedia support
    multimedia = [pkg for pkg in installer.additional_packages if any(media in pkg.lower() for media in ['vlc', 'mpv', 'gimp', 'ffmpeg', 'pulseaudio'])]
    if len(multimedia) >= 3:
        score += 10
        print("✅ Multimedia Support: Well configured (+10 points)")
    elif len(multimedia) >= 1:
        score += 5
        print("✅ Multimedia Support: Basic setup (+5 points)")
    else:
        recommendations.append("Consider installing multimedia tools for media playback and editing")
        print("⚠️  Multimedia Support: Not configured (0 points)")
    
    # Check office/productivity
    office = [pkg for pkg in installer.additional_packages if any(off in pkg.lower() for off in ['libreoffice', 'thunderbird', 'firefox', 'evince'])]
    if len(office) >= 3:
        score += 10
        print("✅ Office/Productivity: Well configured (+10 points)")
    elif len(office) >= 1:
        score += 5
        print("✅ Office/Productivity: Basic setup (+5 points)")
    else:
        recommendations.append("Consider installing office and productivity applications")
        print("⚠️  Office/Productivity: Not configured (0 points)")
    
    # Calculate grade
    percentage = (score / max_score) * 100
    
    print(f"\n🏆 Final Score: {score}/{max_score} ({percentage:.1f}%)")
    
    if percentage >= 90:
        print("🎉 Excellent! Your system is optimally configured!")
        grade = "A+"
    elif percentage >= 80:
        print("✅ Great! Your system is well-configured with minor improvements possible.")
        grade = "A"
    elif percentage >= 70:
        print("👍 Good! Your system has a solid foundation.")
        grade = "B"
    elif percentage >= 60:
        print("⚠️  Fair. Consider adding more features for better functionality.")
        grade = "C"
    else:
        print("🔧 Basic. Your system needs more configuration for optimal use.")
        grade = "D"
    
    print(f"Grade: {grade}")
    
    if recommendations:
        print("\n💡 Recommendations for improvement:")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    
    log.info(f"System configuration score: {score}/{max_score} ({percentage:.1f}%) - Grade: {grade}")
    
    return score, grade

def interactive_system_scoring(installer: 'Installer', log: LogFile, logo_animation):
    """Display system configuration scoring and recommendations."""
    print("\n🎯 === Configuration Analysis ===")
    print("Let me analyze your current configuration and provide feedback...")
    
    # Wait a moment for dramatic effect
    import time
    time.sleep(1)
    
    score, grade = calculate_system_score(installer, log)
    
    print("\n" + "="*50)
    print("📋 Configuration Summary:")
    print(f"   • Total Packages: {len(installer.additional_packages)}")
    print(f"   • Services Enabled: {len([s for s in installer.services if s])}")
    print(f"   • Desktop Environment: {'Configured' if hasattr(installer, 'desktop_packages') and installer.desktop_packages else 'Not configured'}")
    print(f"   • Configuration Score: {grade} ({score}/100)")
    print("="*50)
    
    # Ask if user wants to improve score
    if score < 90:
        improve = input_with_pause(f"\nWould you like suggestions to improve your score? (y/n): ", logo_animation).strip().lower()
        if improve == 'y':
            print("\n🔧 Suggested improvements:")
            if score < 60:
                print("   • Add a desktop environment for better usability")
                print("   • Install graphics drivers for optimal performance")
                print("   • Configure basic security features")
                print("   • Add essential system utilities")
            elif score < 80:
                print("   • Consider adding development tools if you code")
                print("   • Install multimedia applications for media support")
                print("   • Add office productivity software")
                print("   • Configure network services")
            else:
                print("   • Fine-tune your existing configuration")
                print("   • Consider specialized tools for your use case")
                print("   • Add monitoring and maintenance tools")
    
    print("\n✅ Analysis complete! Proceeding with installation...")
    """Accessibility and usability enhancements."""
    print("\n♿ === Accessibility Features ===")
    
    accessibility_options = {
        '1': ('Screen Reader (Orca)', 'screen_reader'),
        '2': ('Braille Support', 'braille'),
        '3': ('High Contrast Themes', 'high_contrast'),
        '4': ('Large Text/Cursors', 'large_text'),
        '5': ('Keyboard Navigation', 'keyboard_nav'),
        '6': ('Voice Control', 'voice_control'),
        '7': ('Gesture Recognition', 'gestures'),
        '8': ('Alternative Input Methods', 'alt_input'),
        '0': ('Skip', 'skip')
    }
    
    print("Accessibility features:")
    for key, (name, _) in accessibility_options.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select accessibility features (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_accessibility = []

    for choice in choices:
        choice = choice.strip()
        if choice in accessibility_options and choice != '0':
            name, access_type = accessibility_options[choice]
            selected_accessibility.append(access_type)
        elif choice == '0':
            break

    if selected_accessibility:
        apply_accessibility_features(installer, selected_accessibility, log)

def apply_accessibility_features(installer, accessibility, log):
    """Apply selected accessibility features."""
    for access in accessibility:
        if access == 'screen_reader':
            installer.add_additional_packages(['orca', 'speech-dispatcher', 'espeak-ng'])
            log.info("Added screen reader support")
            
        elif access == 'braille':
            installer.add_additional_packages(['brltty', 'brltty-udev'])
            installer.enable_service(['brltty'])
            log.info("Added Braille support")
            
        elif access == 'high_contrast':
            installer.add_additional_packages(['gnome-themes-extra', 'gtk-engine-murrine'])
            log.info("Added high contrast themes")
            
        elif access == 'large_text':
            # Large text is handled through desktop environment settings
            log.info("Large text support enabled (configure in desktop settings)")
            
        elif access == 'keyboard_nav':
            installer.add_additional_packages(['mousetweaks', 'caribou', 'onboard'])
            log.info("Added keyboard navigation tools")
            
        elif access == 'voice_control':
            installer.add_additional_packages(['simon', 'julius', 'cmusphinx'])
            log.info("Added voice control support")
            
        elif access == 'gestures':
            installer.add_additional_packages(['touchegg', 'fusuma'])
            installer.enable_service(['touchegg'])
            log.info("Added gesture recognition")
            
        elif access == 'alt_input':
            installer.add_additional_packages(['dasher', 'cellwriter', 'florence'])
            log.info("Added alternative input methods")
    """Select office and productivity software."""
    print("\n=== Office and Productivity ===")
    office = {
        '1': ('LibreOffice Suite', ['libreoffice-fresh']),
        '2': ('Email Clients', ['thunderbird', 'evolution', 'geary']),
        '3': ('Web Browsers', ['firefox', 'chromium', 'opera']),
        '4': ('PDF Tools', ['evince', 'okular', 'masterpdfeditor-free']),
        '5': ('Note Taking', ['cherrytree', 'zim', 'joplin']),
        '6': ('Calendars', ['gnome-calendar', 'korganizer']),
        '7': ('Calculators', ['galculator', 'speedcrunch', 'qalculate-gtk']),
        '8': ('Document Scanners', ['simple-scan', 'skanlite']),
        '9': ('OCR Tools', ['tesseract', 'gocr']),
        '10': ('Project Management', ['projectlibre', 'planner']),
        '0': ('Skip', [])
    }
    
    print("Available office and productivity tools:")
    for key, (name, _) in office.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select office tools (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in office and choice != '0':
            name, packages = office[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install office tools: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Office tools selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Office tools installed: {selected_names} - {list(selected_packages)}")
    """Additional system features and software."""
    print("\n=== Additional Features ===")
    features = {
        '1': ('Gaming', ['steam', 'lutris', 'wine', 'gamemode', 'mangohud']),
        '2': ('Multimedia', ['vlc', 'mpv', 'audacity', 'gimp', 'inkscape', 'blender']),
        '3': ('Office', ['libreoffice-fresh', 'thunderbird', 'firefox']),
        '4': ('Communication', ['discord', 'telegram-desktop', 'zoom', 'skypeforlinux']),
        '5': ('Virtualization', ['qemu', 'virt-manager', 'virtualbox', 'vagrant']),
        '6': ('System Monitoring', ['htop', 'nvtop', 'neofetch', 'screenfetch', 'conky']),
        '7': ('Backup Tools', ['timeshift', 'deja-dup', 'borgbackup']),
        '8': ('Printing', ['cups', 'cups-pdf', 'system-config-printer']),
        '9': ('Bluetooth Advanced', ['bluez', 'bluez-utils', 'blueman', 'pulseaudio-bluetooth']),
        '10': ('Accessibility', ['orca', 'brltty', 'espeak-ng']),
        '0': ('Skip', [])
    }
    
    print("Additional software categories:")
    for key, (name, _) in features.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select additional features (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_packages = set()
    selected_names = []

    for choice in choices:
        choice = choice.strip()
        if choice in features and choice != '0':
            name, packages = features[choice]
            selected_packages.update(packages)
            selected_names.append(name)
        elif choice == '0':
            break

    if selected_packages:
        if MOCK_MODE:
            log.info(f"[MOCK] Would install additional features: {selected_names} - {list(selected_packages)}")
            print(f"[MOCK] Additional features selected: {', '.join(selected_names)}")
        else:
            installer.add_additional_packages(list(selected_packages))
            log.info(f"Additional features installed: {selected_names} - {list(selected_packages)}")
            
            # Enable services for selected features
            service_map = {
                '5': ['libvirtd'],  # Virtualization
                '8': ['cups']  # Printing
            }
            for choice in choices:
                if choice.strip() in service_map:
                    installer.enable_service(service_map[choice.strip()])


# ===========================
# Interactive Step Menus
# ===========================
def interactive_disk_format(installer: 'Installer', log: LogFile, logo_animation):
    print("\n=== Disk Formatting ===")
    choice = input_with_pause("Do you want to format all partitions? (y/n): ", logo_animation).lower()
    if choice == 'y':
        # Mock logic or real logic
        if MOCK_MODE:
             log.info("[MOCK] Formatting all partitions...")
             print("[MOCK] Formatted all partitions.")
        elif installer and hasattr(installer, 'disk_config') and installer.disk_config:
            for part in installer.disk_config.partitions:
                fs_type = getattr(part, 'fs_type', 'ext4')
                log.info(f"Formatting {part.path} as {fs_type}...")
                installer.format_partition(part.path, fs_type)
                print(f"{part.path} formatted as {fs_type}")
        else:
             print("No disk config available to format.")
    else:
        print("Skipping disk formatting.")
        log.info("Disk formatting skipped.")
    input_with_pause("Press Enter to continue...", logo_animation)

def add_user(installer, log: LogFile, logo_animation):
    print("\n=== Add New User ===")
    username = input_with_pause("Enter username: ", logo_animation).strip()
    password = input_with_pause(f"Enter password for {username}: ", logo_animation).strip()
    is_admin = input_with_pause("Should this user have sudo/admin rights? (y/n): ", logo_animation).lower() == 'y'

    if username and password:
        if not ARCHINSTALL_AVAILABLE and not MOCK_MODE:
            log.error("Cannot create user: archinstall not available.")
            raise RuntimeError("archinstall not available")
        
        if MOCK_MODE:
            log.info(f"[MOCK] Creating user {username}, admin={is_admin}")
            print(f"[MOCK] User '{username}' added successfully.")
        else:
            new_user = User(username, password, is_admin)
            installer.create_users([new_user])  # Add this user
            print(f"User '{username}' added successfully.")
            log.info(f"User added: {username}, admin: {is_admin}")
    else:
        print("Invalid username or password. Skipping.")
        log.warn("User creation skipped due to invalid input.")

def interactive_add_users(installer : 'Installer', log: LogFile, logo_animation):
    rootusers = input_with_pause("Make default users(y)  / or make your own users(n) (y / n)", logo_animation)
    if rootusers == "y":
        if not ARCHINSTALL_AVAILABLE and not MOCK_MODE:
            log.error("Cannot add default users: archinstall not available.")
            raise RuntimeError("archinstall not available")
        
        if MOCK_MODE:
            log.info("[MOCK] Adding default user narchs")
            print("Default Users Installed")
        else:
            # Check if DEFAULT_USER is a list or single object, assuming single based on original code
            # Original code said: users = DEFAULT_USER; installer.create_users(users)
            # define_installer typically expects a list for users?
            # It seems installer.create_users takes a list.
            installer.create_users([DEFAULT_USER])
            print("Default Users Installed")
            log.info("Default Users Added users are narchs , Narchs123!")
            
    while True:
        add_user(installer, log, logo_animation)
        cont = input_with_pause("Add another user? (y/n): ", logo_animation).lower()
        if cont != 'y':
            break

def interactive_packages(installer: 'Installer', log: LogFile, logo_animation):
    print("\n=== Package Installation ===")
    choice = input_with_pause("Install base packages (b), desktop packages (d), or both (a)? [b/d/a]: ", logo_animation).lower()
    
    if MOCK_MODE:
        if choice in ['b','a']:
            log.info("[MOCK] Base packages installed.")
        if choice in ['d','a']:
            log.info("[MOCK] Desktop packages installed.")
        input_with_pause("Press Enter to continue...", logo_animation)
        return

    if choice in ['b','a']:
        if not ARCHINSTALL_AVAILABLE:
            log.error("Cannot install packages: archinstall not available.")
            raise RuntimeError("archinstall not available")
        installer.add_additional_packages(BASE_PACKAGES)
        log.info("Base packages installed.")
    if choice in ['d','a']:
        installer.add_additional_packages(DESKTOP_PACKAGES)
        log.info("Desktop packages installed.")
    input_with_pause("Press Enter to continue...", logo_animation)

def interactive_services(installer: 'Installer', log: LogFile, logo_animation):
    print("\n=== Services Setup ===")
    for svc in DEFAULT_SERVICES:
        enable = input_with_pause(f"Enable service {svc}? (y/n): ", logo_animation).lower()
        if enable == 'y':
            if MOCK_MODE:
                log.info(f"[MOCK] Service enabled: {svc}")
            else:
                installer.enable_service([svc])
                log.info(f"Service enabled: {svc}")
        else:
            log.info(f"Service skipped: {svc}")
    input_with_pause("Press Enter to continue...", logo_animation)

def interactive_timezone(installer: 'Installer', log: LogFile, logo_animation):
    tz = input_with_pause("Set timezone (default America/New_York): ", logo_animation).strip()
    if not tz:
        tz = "America/New_York"
    
    if MOCK_MODE:
        log.info(f"[MOCK] Timezone set to {tz}")
        print(f"Timezone set to {tz}")
    else:
        installer.set_timezone(tz)
        installer.activate_time_synchronization()
        print(f"Timezone set to {tz}")
        log.info(f"Timezone set to {tz}")
    input_with_pause("Press Enter to continue...", logo_animation)

def interactive_wifi(installer: 'Installer', log: LogFile, logo_animation):
    run_command("nmcli radio wifi on", log)
    
    if MOCK_MODE:
        networks = ["Mock-WiFi-1", "Mock-WiFi-2"]
    else:
        networks = [n for n in os.popen("nmcli -t -f SSID dev wifi list").read().splitlines() if n]
        
    if networks:
        print("\nAvailable Wi-Fi networks:")
        for i, ssid in enumerate(networks,1):
            print(f"{i}. {ssid}")
        choice = input_with_pause("Select Wi-Fi number to connect (0 to skip): ", logo_animation)
        try:
            choice = int(choice)
            if 1 <= choice <= len(networks):
                ssid = networks[choice-1]
                password = input_with_pause(f"Enter password for {ssid}: ", logo_animation)
                cmd = f"nmcli device wifi connect '{ssid}' password '{password}'"
                run_command(cmd, log)
                log.info(f"Connected to Wi-Fi network: {ssid}")
            else:
                log.info("Wi-Fi setup skipped by user.")
                print("Skipping Wi-Fi setup.")
        except:
            log.error("Wi-Fi setup failed or skipped.")
            print("WIFI REQUIRES REBOOT TO TAKE EFFECT")
            
    else:
        log.info("No Wi-Fi networks found.")
        print("WIFI REQUIRED , REBOOT TO TAKE EFFECT")
    input_with_pause("Press Enter to continue...", logo_animation)

def interactive_bootloader(installer: 'Installer', log: LogFile, logo_animation):
    print("\n=== Bootloader Setup ===")
    bootloaders = ["Grub", "SystemdBoot", "Skip"]
    for i, b in enumerate(bootloaders,1):
        print(f"{i}. {b}")
    choice = input_with_pause("Select bootloader: ", logo_animation)
    try:
        choice = int(choice)
        if MOCK_MODE:
            if choice == 1: log.info("[MOCK] Bootloader installed: GRUB")
            elif choice == 2: log.info("[MOCK] Bootloader installed: SystemdBoot")
            else: log.info("[MOCK] Bootloader setup skipped.")
        else:
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
    input_with_pause("Press Enter to continue...", logo_animation)

def interactive_custom_commands(installer: 'Installer', log: LogFile, logo_animation):
    print("\n=== Run Custom NARCHS Scripts ===")
    for cmd in CUSTOM_COMMANDS:
        run = input_with_pause(f"Run {cmd}? (y/n): ", logo_animation).lower()
        if run == 'y':
            run_command(cmd, log)
            log.info(f"Ran custom command: {cmd}")
        else:
            log.info(f"Skipped custom command: {cmd}")
    input_with_pause("Press Enter to continue...", logo_animation)

def interactive_format_partition(installer: 'Installer', log: LogFile, logo_animation):
    print("\n=== Format Partition ===")
    
    if MOCK_MODE:
        # Mock Partitions
        log.info("[MOCK] Showing mock partitions")
        print("Available partitions (MOCK):")
        print("1. /dev/sda1 (current fs: ext4)")
        print("2. /dev/sda2 (current fs: fat32)")
        
        choice = input_with_pause("Select partition number to format (0 to skip): ", logo_animation)
        if choice != '0':
            fs_type = input_with_pause(f"Enter filesystem type (default ext4): ", logo_animation).strip() or "ext4"
            print(f"[MOCK] Partition formatted as {fs_type}")
        return

    disk_config = installer.disk_config
    if not disk_config or not hasattr(disk_config, 'partitions') or not disk_config.partitions:
        print("No partitions found in disk configuration.")
        log.warn("No partitions found for formatting.")
        return

    print("Available partitions:")
    for idx, part in enumerate(disk_config.partitions, 1):
        fs_type = getattr(part, 'fs_type', 'ext4')
        print(f"{idx}. {part.path} (current fs: {fs_type})")

    choice = input_with_pause("Select partition number to format (0 to skip): ", logo_animation)
    try:
        choice = int(choice)
        if choice == 0:
            print("Skipping partition formatting.")
            log.info("Partition formatting skipped.")
            return
        if 1 <= choice <= len(disk_config.partitions):
            part = disk_config.partitions[choice-1]
            fs_type = input_with_pause(f"Enter filesystem type for {part.path} (default ext4): ", logo_animation).strip()
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
    input_with_pause("Press Enter to continue...", logo_animation)

def interactive_find_mirrors(installer: 'Installer', log: LogFile, logo_animation):
    print("\n=== Find Fastest Mirrors ===")
    choice = input_with_pause("Do you want to search for the fastest mirrors? (y/n): ", logo_animation).lower()
    if choice != 'y':
        print("Skipping mirror check.")
        log.info("Mirror check skipped by user.")
        return

    try:
        print("Ranking mirrors by speed...")
        run_command("reflector --latest 10 --sort rate --save /etc/pacman.d/mirrorlist", log)
        print("Mirrorlist updated with fastest mirrors.")
        log.info("Fastest mirrors configured.")
    except Exception as e:
        log.error(f"Failed to update mirrors: {e}")
    input_with_pause("Press Enter to continue...", logo_animation)

def setup_login_ui(installer: 'Installer', log: LogFile):
    """Install and enable a GTK-based login UI (LightDM + GTK greeter)."""
    log.info("Installing LightDM and GTK greeter (lightdm + lightdm-gtk-greeter)")
    try:
        if MOCK_MODE:
             log.info("[MOCK] LightDM and GTK greeter installed and enabled.")
             return

        if not ARCHINSTALL_AVAILABLE:
            log.error("Cannot setup LightDM: archinstall not available.")
            raise RuntimeError("archinstall not available")
        installer.add_additional_packages(['lightdm', 'lightdm-gtk-greeter'])
        # enable the service (installer API in this project expects a list)
        installer.enable_service(['lightdm'])
        log.info("LightDM and GTK greeter installed and enabled.")
    except Exception as e:
        log.error(f"Failed to install/enable LightDM: {e}")
        raise

def install_feature_updater(installer: 'Installer', log: LogFile, repo_url: str, branch: str = 'main'):
    """Install a startup updater that fetches latest feature archive from GitHub."""
    
    script_path = '/usr/local/bin/narchs_feature_updater.sh'
    service_path = '/etc/systemd/system/narchs-feature-updater.service'
    timer_path = '/etc/systemd/system/narchs-feature-updater.timer'

    log.info(f"Installing feature updater script to {script_path}")
    
    if MOCK_MODE:
        log.info("[MOCK] Not in root check skipped")
    elif os.geteuid() != 0:
        log.info("Not in root")
        raise PermissionError("Must be run as root.")
    
    log.info("Confirmed running as root (or MOCK).")


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

    if MOCK_MODE:
        log.info(f"[MOCK] Written updater script to {script_path}")
        log.info(f"[MOCK] Written systemd service to {service_path}")
        log.info(f"[MOCK] Written systemd timer to {timer_path}")
        log.info("[MOCK] Helper commands (systemctl enable/start) would run here.")
        return

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

        # write a systemd timer
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
        run_command('systemctl daemon-reload', log)
        run_command('systemctl enable narchs-feature-updater.service', log)
        run_command('systemctl enable --now narchs-feature-updater.timer', log)
        log.info('Feature updater service and timer enabled.')

    except Exception as e:
        log.error(f"Failed to install feature updater: {e}")
        raise


    """Run the feature updater script once immediately."""
    script_path = '/usr/local/bin/narchs_feature_updater.sh'
    if os.path.exists(script_path) and os.access(script_path, os.X_OK):
        log.info('Running feature updater once...')
        ret = run_command(script_path, log)
        if ret != 0:
            log.error(f'Feature updater script returned non-zero exit code: {ret}')
        else:
            log.info('Feature updater completed successfully.')
    else:
        log.warn('Feature updater script not present or not executable.')

def interactive_company_integrations(installer: 'Installer', log: LogFile, logo_animation):
    """Integrate with popular companies and services."""
    print("\n🤝 === Company Integrations & Partnerships ===")
    print("SENDUNE Linux partners with leading technology companies!")
    
    integrations = {
        '1': ('Microsoft Integration', 'microsoft'),
        '2': ('Google Workspace', 'google'),
        '3': ('AWS Tools & Services', 'aws'),
        '4': ('Azure Cloud Integration', 'azure'),
        '5': ('GitHub Integration', 'github'),
        '6': ('Docker & Container Tools', 'docker'),
        '7': ('Steam Gaming Platform', 'steam'),
        '8': ('NVIDIA AI & Gaming', 'nvidia_ai'),
        '9': ('AMD ROCm Integration', 'amd_rocm'),
        '10': ('Enterprise Features', 'enterprise'),
        '0': ('Skip', 'skip')
    }
    
    print("Available company integrations:")
    for key, (name, _) in integrations.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select integrations (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_integrations = []

    for choice in choices:
        choice = choice.strip()
        if choice in integrations and choice != '0':
            name, integration_type = integrations[choice]
            selected_integrations.append(integration_type)
        elif choice == '0':
            break

    if selected_integrations:
        apply_company_integrations(installer, selected_integrations, log)

def apply_company_integrations(installer, integrations, log):
    """Apply selected company integrations."""
    for integration in integrations:
        if integration == 'microsoft':
            installer.add_additional_packages([
                'powershell', 'dotnet-sdk', 'microsoft-edge-stable-bin',
                'visual-studio-code-bin', 'teams', 'onedrive'
            ])
            log.info("Added Microsoft integration tools")
            
        elif integration == 'google':
            installer.add_additional_packages([
                'google-chrome', 'chromium', 'google-cloud-sdk',
                'android-studio', 'flutter', 'dart'
            ])
            log.info("Added Google Workspace and development tools")
            
        elif integration == 'aws':
            installer.add_additional_packages([
                'aws-cli-v2', 'aws-vault', 'terraform', 'docker',
                'kubernetes', 'kubectl', 'helm'
            ])
            log.info("Added AWS cloud tools and services")
            
        elif integration == 'azure':
            installer.add_additional_packages([
                'azure-cli', 'azure-functions-core-tools',
                'powershell', 'dotnet-sdk', 'terraform'
            ])
            log.info("Added Azure cloud integration")
            
        elif integration == 'github':
            installer.add_additional_packages([
                'github-cli', 'git', 'gh', 'act', 'docker'
            ])
            log.info("Added GitHub integration and tools")
            
        elif integration == 'docker':
            installer.add_additional_packages([
                'docker', 'docker-compose', 'docker-buildx',
                'podman', 'buildah', 'skopeo', 'kubernetes', 'kubectl'
            ])
            installer.enable_service(['docker'])
            log.info("Added comprehensive container ecosystem")
            
        elif integration == 'steam':
            installer.add_additional_packages([
                'steam', 'lutris', 'wine', 'proton-ge-custom',
                'mangohud', 'gamemode', 'vulkan-icd-loader'
            ])
            installer.enable_service(['gamemoded'])
            log.info("Added Steam gaming platform and tools")
            
        elif integration == 'nvidia_ai':
            installer.add_additional_packages([
                'cuda', 'cudnn', 'tensorrt', 'nvidia-docker',
                'python-pytorch-cuda', 'python-tensorflow-cuda'
            ])
            log.info("Added NVIDIA AI and deep learning tools")
            
        elif integration == 'amd_rocm':
            installer.add_additional_packages([
                'rocm-hip-sdk', 'rocm-opencl-sdk', 'miopen',
                'rocblas', 'hipsparse', 'rccl'
            ])
            log.info("Added AMD ROCm for AI and computing")
            
        elif integration == 'enterprise':
            installer.add_additional_packages([
                'ansible', 'terraform', 'packer', 'vagrant',
                'openvpn', 'wireguard-tools', 'cockpit',
                'prometheus', 'grafana', 'zabbix-agent'
            ])
            installer.enable_service(['cockpit'])
            log.info("Added enterprise-grade tools and monitoring")

def interactive_ai_powered_features(installer: 'Installer', log: LogFile, logo_animation):
    """Advanced AI-powered features and automation."""
    print("\n🧠 === AI-Powered Features ===")
    print("Experience the future of Linux with SENDUNE's AI capabilities!")
    
    ai_features = {
        '1': ('AI System Optimizer', 'ai_optimizer'),
        '2': ('Smart Package Recommendations', 'smart_recommendations'),
        '3': ('Automated Security Analysis', 'security_ai'),
        '4': ('Performance Prediction', 'performance_prediction'),
        '5': ('Intelligent Backup System', 'intelligent_backup'),
        '6': ('Voice Assistant Integration', 'voice_assistant'),
        '7': ('Smart Resource Management', 'resource_management'),
        '8': ('AI-Powered Troubleshooting', 'ai_troubleshooting'),
        '9': ('Predictive Maintenance', 'predictive_maintenance'),
        '10': ('Custom AI Models', 'custom_ai'),
        '0': ('Skip', 'skip')
    }
    
    print("AI-powered features:")
    for key, (name, _) in ai_features.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select AI features (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_ai = []

    for choice in choices:
        choice = choice.strip()
        if choice in ai_features and choice != '0':
            name, ai_type = ai_features[choice]
            selected_ai.append(ai_type)
        elif choice == '0':
            break

    if selected_ai:
        apply_ai_features(installer, selected_ai, log)

def apply_ai_features(installer, ai_features, log):
    """Apply selected AI-powered features."""
    for ai in ai_features:
        if ai == 'ai_optimizer':
            installer.add_additional_packages([
                'python', 'python-pytorch', 'python-scikit-learn',
                'python-pandas', 'python-numpy', 'auto-cpufreq'
            ])
            log.info("Added AI system optimization tools")
            
        elif ai == 'smart_recommendations':
            installer.add_additional_packages([
                'python', 'python-pandas', 'python-scikit-learn',
                'python-nltk', 'mlocate'
            ])
            log.info("Added smart package recommendation system")
            
        elif ai == 'security_ai':
            installer.add_additional_packages([
                'python', 'python-scikit-learn', 'fail2ban',
                'rkhunter', 'chkrootkit', 'lynis'
            ])
            installer.enable_service(['fail2ban'])
            log.info("Added AI-powered security analysis")
            
        elif ai == 'performance_prediction':
            installer.add_additional_packages([
                'python', 'python-pandas', 'python-matplotlib',
                'sysstat', 'iotop', 'perf'
            ])
            log.info("Added performance prediction and monitoring")
            
        elif ai == 'intelligent_backup':
            installer.add_additional_packages([
                'borgbackup', 'restic', 'duplicati',
                'python', 'python-schedule'
            ])
            log.info("Added intelligent backup system")
            
        elif ai == 'voice_assistant':
            installer.add_additional_packages([
                'mycroft-core', 'python-pyaudio', 'espeak-ng',
                'pulseaudio', 'sox'
            ])
            log.info("Added voice assistant integration")
            
        elif ai == 'resource_management':
            installer.add_additional_packages([
                'earlyoom', 'nohang', 'zram-generator',
                'irqbalance', 'numad'
            ])
            installer.enable_service(['earlyoom', 'irqbalance'])
            log.info("Added smart resource management")
            
        elif ai == 'ai_troubleshooting':
            installer.add_additional_packages([
                'python', 'python-psutil', 'python-systemd',
                'journalctl', 'systemd-analyze'
            ])
            log.info("Added AI-powered troubleshooting tools")
            
        elif ai == 'predictive_maintenance':
            installer.add_additional_packages([
                'smartmontools', 'python', 'python-schedule',
                'mlocate', 'logrotate'
            ])
            log.info("Added predictive maintenance system")
            
        elif ai == 'custom_ai':
            installer.add_additional_packages([
                'python', 'python-pytorch', 'python-tensorflow',
                'jupyter-notebook', 'python-jupyterlab'
            ])
            log.info("Added tools for custom AI model development")

def interactive_enterprise_features(installer: 'Installer', log: LogFile, logo_animation):
    """Enterprise-grade features and integrations."""
    print("\n🏢 === Enterprise Features ===")
    print("Professional-grade tools for business and enterprise use!")
    
    enterprise_features = {
        '1': ('Active Directory Integration', 'active_directory'),
        '2': ('LDAP Authentication', 'ldap'),
        '3': ('Samba File Server', 'samba_server'),
        '4': ('NFS Server', 'nfs_server'),
        '5': ('VPN Server (OpenVPN)', 'openvpn_server'),
        '6': ('Remote Desktop (XRDP)', 'remote_desktop'),
        '7': ('Monitoring Stack (Prometheus/Grafana)', 'monitoring_stack'),
        '8': ('Log Management (ELK Stack)', 'log_management'),
        '9': ('Backup Solutions', 'enterprise_backup'),
        '10': ('Compliance Tools', 'compliance'),
        '0': ('Skip', 'skip')
    }
    
    print("Enterprise features:")
    for key, (name, _) in enterprise_features.items():
        print(f"{key}. {name}")
    print("You can enter multiple choices separated by commas")
    
    choices = input_with_pause("Select enterprise features (comma-separated, 0 to skip): ", logo_animation).strip().split(',')
    selected_enterprise = []

    for choice in choices:
        choice = choice.strip()
        if choice in enterprise_features and choice != '0':
            name, enterprise_type = enterprise_features[choice]
            selected_enterprise.append(enterprise_type)
        elif choice == '0':
            break

    if selected_enterprise:
        apply_enterprise_features(installer, selected_enterprise, log)

def apply_enterprise_features(installer, enterprise_features, log):
    """Apply selected enterprise features."""
    for enterprise in enterprise_features:
        if enterprise == 'active_directory':
            installer.add_additional_packages([
                'sssd', 'realmd', 'adcli', 'samba', 'krb5'
            ])
            log.info("Added Active Directory integration")
            
        elif enterprise == 'ldap':
            installer.add_additional_packages([
                'openldap', 'nss-pam-ldapd', 'sssd'
            ])
            log.info("Added LDAP authentication support")
            
        elif enterprise == 'samba_server':
            installer.add_additional_packages([
                'samba', 'wsdd', 'cups', 'avahi'
            ])
            installer.enable_service(['smbd', 'nmbd', 'avahi-daemon'])
            log.info("Added Samba file server")
            
        elif enterprise == 'nfs_server':
            installer.add_additional_packages([
                'nfs-utils', 'rpcbind'
            ])
            installer.enable_service(['nfs-server', 'rpcbind'])
            log.info("Added NFS server")
            
        elif enterprise == 'openvpn_server':
            installer.add_additional_packages([
                'openvpn', 'easy-rsa', 'iptables'
            ])
            log.info("Added OpenVPN server capabilities")
            
        elif enterprise == 'remote_desktop':
            installer.add_additional_packages([
                'xrdp', 'xorgxrdp', 'tigervnc'
            ])
            installer.enable_service(['xrdp'])
            log.info("Added remote desktop support")
            
        elif enterprise == 'monitoring_stack':
            installer.add_additional_packages([
                'prometheus', 'grafana', 'node-exporter',
                'prometheus-node-exporter', 'alertmanager'
            ])
            installer.enable_service(['prometheus', 'grafana'])
            log.info("Added monitoring stack (Prometheus/Grafana)")
            
        elif enterprise == 'log_management':
            installer.add_additional_packages([
                'elasticsearch', 'logstash', 'kibana',
                'filebeat', 'rsyslog'
            ])
            log.info("Added ELK stack for log management")
            
        elif enterprise == 'enterprise_backup':
            installer.add_additional_packages([
                'bacula', 'bareos', 'rsync', 'borgbackup',
                'restic', 'duplicati'
            ])
            log.info("Added enterprise backup solutions")
            
        elif enterprise == 'compliance':
            installer.add_additional_packages([
                'audit', 'openscap', 'scap-workbench',
                'lynis', 'tiger', 'chkrootkit'
            ])
            installer.enable_service(['auditd'])
            log.info("Added compliance and security auditing tools")
