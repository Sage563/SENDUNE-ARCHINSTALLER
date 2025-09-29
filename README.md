# 🌐 SENDUNE Linux

**SENDUNE** is a custom Arch-based Linux distribution designed for developers, tinkerers, and power users who want a fast, minimal, and modern desktop powered by **Hyperland**.  
It ships with a curated set of packages, preconfigured dotfiles, and automation scripts for a smooth out-of-the-box experience.

---

## ✨ Features

### 🖥️ Desktop & UI
- **Hyperland compositor** with Wayland support  
- Preconfigured dotfiles for a polished desktop  
- **Waybar**, **Wofi**, and **Swaybg** for bar, launcher, and wallpaper  
- **Mako** for notifications  
- **Foot terminal** as the lightweight terminal emulator  
- Built-in screenshot tools (**Grim** + **Slurp**)  
- Clipboard management with **wl-clipboard**  

### ⚙️ System & Services
- **Arch Linux base** for flexibility and rolling updates  
- **systemd services pre-enabled**:  
  - `NetworkManager` (network)  
  - `sshd` (remote access)  
  - `bluetooth`  
  - `pipewire` (modern audio)  
- Automatic partition formatting and mounting via installer  

### 🧰 Developer Tools
- **Git**, **Docker**, **Node.js**, **npm**, **Python**, **pip**  
- **GNU toolchain** (`gcc`, `make`, `base-devel`)  
- Editors: **Vim**, **Nano**, **VS Code**  
- Browsers: **Firefox**, **Chromium**  
- Extras: **htop**, **neofetch**, **zsh**, **bash-completion**  

### 🎨 Extras & Fun
- **Krita** for digital art  
- **Wine** for running Windows apps  
- **Minecraft Launcher** preinstalled  
- CLI goodies: `lolcat`, `sl`  

---

## 🚀 Installation

### On Linux
```bash
git clone https://github.com/yourusername/SENDUNE.git
cd SENDUNE
sudo python3 installer.py
