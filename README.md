# 🌐 SENDUNE Linux

**A Modern Arch-Based Linux Distribution**

SENDUNE Linux is a modern, user-friendly Linux distribution based on Arch Linux. It provides an easy-to-use installer with comprehensive software selection and system configuration options for both beginners and advanced users.

- **Easy Installation**: Guided installer with intelligent defaults
- **Comprehensive Software**: Extensive package selection for all use cases
- **Gaming Optimized**: Steam integration and gaming performance tuning
- **Developer Focused**: Complete development stacks for every programming language
- **Security First**: Built-in security features and automated hardening
- ![MADEWITH PYTHON](https://user-images.githubusercontent.com/74038190/212257472-08e52665-c503-4bd9-aa20-f5a4dae769b5.gif)

## Running on Windows (Mock Mode)

This installer includes a **Mock Mode** for development and testing on Windows.
In this mode, no actual system changes are made (no partitioning, no formatting, no package installation). Instead, the installer will print the commands it *would* have executed.

To run in Mock Mode on Windows:

1.  Make sure you have Python installed.
2.  Open a terminal (PowerShell or CMD) in the project directory.
3.  Run the installer module:

```powershell
    python -m SENDUNE_installer
```

You will see the logo and be guided through the prompts. All actions will be simulated.

## Making the ISO (Linux Only)

To build the custom Arch ISO, you must be on a Linux system with `arch-install-scripts` and `xorriso` installed.

1.  Download the latest Arch Linux ISO:

```sh
    curl -L -o archlinux-x86_64.iso https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso
```

2.  Make the script executable:

```sh
    chmod +x build_arch_iso.sh
```

3.  Run the build script:

```sh
    # Usage: ./build_arch_iso.sh <SOURCE_ISO> <INSTALLER_DIR> <OUTPUT_ISO>
    sudo ./build_arch_iso.sh archlinux-x86_64.iso ./SENDUNE_installer ./SENDUNE_Arch.iso
```

4.  Boot the resulting `SENDUNE_Arch.iso`.
5.  Inside the live environment, run:

```sh
    python3 -m SENDUNE_installer
```

## Building the ISO with Archinstall

The `build_arch_iso.sh` script now automatically downloads the latest `archinstall` source from GitHub and builds it using `uv` in the ISO environment. This ensures you have the most up-to-date version of `archinstall` along with all necessary development tools.

### Included Packages in the ISO:
- `gcc`
- `git` 
- `pkgconfig`
- `python`
- `python-pip`
- `python-uv`
- `python-setuptools`
- `python-pyparted`
- `python-pydantic`
- `yay` (AUR helper)
- `archinstall` (built from source)

This provides a complete development and installation environment right from the live ISO.

## Enhanced Installation Features

SENDUNE installer now includes comprehensive customization options:

### Desktop Environments
- **Hyprland** (Wayland compositor with modern features)
- **GNOME** (Full desktop environment)
- **KDE Plasma** (Feature-rich desktop)
- **XFCE** (Lightweight desktop)
- **LXQt** (Qt-based lightweight desktop)
- **Cinnamon** (Traditional desktop)
- **MATE** (GNOME 2 fork)
- **i3** (Tiling window manager)
- **Awesome WM** (Lua-based window manager)

### Graphics Drivers
- NVIDIA (proprietary and open source)
- AMD/ATI Radeon
- Intel integrated graphics
- VMware virtual graphics
- VirtualBox guest additions

### Development Tools
- **Languages**: Python, JavaScript/Node.js, Java, C/C++, Ruby, PHP
- **Build Tools**: GCC, CMake, Make, Maven, Gradle
- **IDEs**: VS Code, Vim, Neovim, Emacs
- **Databases**: PostgreSQL, MySQL, MongoDB, Redis
- **Containers**: Docker, Podman, Docker Compose

### Security Features
- Firewall (UFW)
- Mandatory Access Control (AppArmor/SELinux)
- Intrusion Detection (Fail2Ban)
- Antivirus (ClamAV)
- Password Quality Enforcement
- Audit Framework

### Login Managers (Display Managers)
- **LightDM** (Lightweight display manager with GTK greeter)
- **GDM** (GNOME Display Manager)
- **SDDM** (KDE Display Manager)
- **LXDM** (LXDE Display Manager)
- **XDM** (X Display Manager)
- **Console only** (No display manager)

### System Themes and Appearance
- **Arc Theme** (Modern GTK theme)
- **Adwaita/Breeze** (GNOME/KDE default themes)
- **Numix/Papirus** (Icon themes)
- **Additional Fonts** (DejaVu, Liberation, Ubuntu, Noto fonts)
- **Microsoft Fonts** (TrueType fonts)
- **Monospace Fonts** (Fira Code, JetBrains Mono, Source Code Pro)

### System Utilities
- **Archive Tools** (zip, unzip, 7zip, rar)
- **File Managers** (Thunar, PCManFM, Dolphin, Nautilus)
- **Terminal Emulators** (Alacritty, Kitty, Terminator, Tilix)
- **Text Editors** (Gedit, Kate, Mousepad)
- **System Monitors** (htop, nvtop, bashtop)
- **Disk Tools** (GParted, GNOME Disk Utility)
- **Network Tools** (Wireshark, nmap, traceroute, net-tools)
- **Power Management** (TLP, powertop, acpi)

### Network Services
- **File Sharing** (Samba, NFS)
- **VPN** (OpenVPN, WireGuard)
- **Zeroconf** (Avahi)
- **SSH/FTP Servers** (OpenSSH, vsftpd)
- **Web Servers** (Apache, Nginx)

### System Automation
- **Task Scheduling** (Cron, Anacron)
- **Log Management** (logrotate)
- **Automatic Updates** (pacman-contrib)
- **Backup Solutions** (rsync, BorgBackup)
- **Monitoring** (Prometheus, Grafana)
- **Security** (Fail2Ban, UFW, ClamAV, AIDE)

### Multimedia Tools
- **Codecs** (GStreamer plugins, FFmpeg)
- **Media Players** (VLC, MPV, Audacious, Rhythmbox)
- **Creative Software** (GIMP, Krita, Inkscape, Blender, Audacity)
- **Screen Recording** (OBS Studio, SimpleScreenRecorder)
- **CD/DVD Tools** (Asunder, Brasero, K3b)
- **Streaming** (Streamlink, youtube-dl)

### Office and Productivity
- **Office Suite** (LibreOffice)
- **Email Clients** (Thunderbird, Evolution, Geary)
- **Web Browsers** (Firefox, Chromium, Opera)
- **PDF Tools** (Evince, Okular, Master PDF Editor)
- **Note Taking** (CherryTree, Zim, Joplin)
- **Calendars** (GNOME Calendar, KOrganizer)
- **Calculators** (Galculator, SpeedCrunch, Qalculate)
- **Document Scanning** (Simple Scan, Skanlite)
- **OCR Tools** (Tesseract, GOCR)
- **Project Management** (ProjectLibre, Planner)

### System Configuration
- **Locales**: Support for 12+ languages and regions
- **Services**: Automatic service configuration based on selections
- **Package Management**: Intelligent package selection and conflict resolution
- **Installation Summary**: Detailed completion report with next steps

## Advanced Features

### Advanced Performance Tuning ⚡
Fine-tune your system for optimal performance:

- **CPU Governor Optimization** (power management)
- **I/O Scheduler Tuning** (storage performance)
- **Memory Management** (swap and caching)
- **Network Optimization** (latency and throughput)
- **Storage Optimization** (SSD/HDD tuning)
- **Gaming Performance** (Feral Gamemode, MangoHud)
- **Battery Optimization** (TLP, PowerTOP)
- **Thermal Management** (fan control, temperature monitoring)

### Cloud Integration ☁️
Seamless integration with major cloud platforms:

- **AWS CLI & Tools** (EC2, S3, Lambda)
- **Azure CLI & Tools** (VMs, Functions, Storage)
- **Google Cloud SDK** (GCP services)
- **Docker & Kubernetes** (container orchestration)
- **Terraform** (infrastructure as code)
- **Ansible** (configuration management)
- **Pulumi** (modern IaC)
- **Cloud-Init Support** (automated provisioning)

### Specialized Development Environments 🔬
Pre-configured stacks for specific development needs:

- **Data Science** (R, Python, databases)
- **Game Development** (Godot, Unity, Blender)
- **Audio Production** (Ardour, LMMS, JACK)
- **Video Editing** (Kdenlive, DaVinci Resolve)
- **3D Animation** (Blender, Natron, Synfig)
- **Web Development** (full-stack tools)
- **Mobile Development** (Android Studio, Flutter)
- **IoT Development** (Arduino, Raspberry Pi)
- **Embedded Systems** (ARM, RTOS tools)

### System Health Monitoring 🏥
Comprehensive system monitoring and maintenance:

- **System Monitoring** (htop, nvtop, bashtop)
- **Hardware Monitoring** (sensors, psensor)
- **Network Monitoring** (vnstat, iftop)
- **Storage Monitoring** (SMART, hdparm)
- **Security Monitoring** (rkhunter, lynis)
- **Performance Monitoring** (perf, sysstat)
- **Log Monitoring** (logwatch, swatch)
- **Automated Maintenance** (cron jobs, logrotate)

### Accessibility Features ♿
Enhanced accessibility and usability:

- **Screen Reader** (Orca, speech synthesis)
- **Braille Support** (brltty, braille displays)
- **High Contrast Themes** (improved visibility)
- **Large Text/Cursors** (better readability)
- **Keyboard Navigation** (alternative input)
- **Voice Control** (speech recognition)
- **Gesture Recognition** (touchpad gestures)
- **Alternative Input Methods** (Dasher, on-screen keyboards)

### Configuration Scoring & Recommendations 📊
SENDUNE provides intelligent scoring of your system configuration:

- **Real-time Analysis**: Automatic evaluation of your setup
- **Grade System**: A+ to D grading based on completeness
- **Personalized Recommendations**: Specific suggestions for improvement
- **Category Breakdown**: Detailed scoring by feature area
- **Optimization Guidance**: Tips to achieve optimal configuration

**Scoring Categories:**
- Desktop Environment (15 points)
- Graphics Drivers (15 points)
- Development Tools (15 points)
- Security Features (15 points)
- System Utilities (10 points)
- Network Services (10 points)
- Multimedia Support (10 points)
- Office/Productivity (10 points)

## Quick Start Guide

1. **Download and Build ISO**:
   ```bash
   curl -L -o archlinux-x86_64.iso https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso
   chmod +x build_arch_iso.sh
   sudo ./build_arch_iso.sh archlinux-x86_64.iso ./SENDUNE_installer ./SENDUNE_Arch.iso
   ```

2. **Boot the ISO** and run:
   ```bash
   python3 -m SENDUNE_installer
   ```

3. **Follow the interactive prompts** to customize your installation:
   - Choose your desktop environment
   - Select graphics drivers
   - Pick development tools
   - Configure security features
   - Add additional software

4. **Reboot** and enjoy your customized SENDUNE Linux system!

## Package Management with Flip

- `flip install <package>` - Install packages
- `flip yeet <package>` - Remove packages and dependencies
- `flip update` - Update system
- `flip search <query>` - Search for packages
- `flip info <package>` - Show package information
- `flip list` - List installed packages
- `flip autoremove` - Remove orphaned packages
- `flip clean` - Clean cache
- `flip help` - Show help

**Note:** Direct use of `pacman` is disabled to encourage using `flip` for a better experience.

## AUR Support with Yay

SENDUNE comes pre-installed with `yay` (Yet Another Yogurt), the most popular AUR helper for Arch Linux. This allows you to easily install packages from the Arch User Repository:

- `yay -S <package>` - Install AUR packages
- `yay -R <package>` - Remove AUR packages
- `yay -Ss <query>` - Search AUR packages
- `yay -Syu` - Update all packages including AUR
- `yay -Q` - List installed packages

**Tip:** Use `yay` for packages not available in the official repositories!

---

**Built with ❤️ by the SENDUNE Linux team**