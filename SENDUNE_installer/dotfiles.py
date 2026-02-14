from pathlib import Path
from .custom_classes import LogFile
import os
import subprocess


def write_bashrc(user_home: Path, log: LogFile, mount_point: Path = None):
    """Writes a custom .bashrc that restricts pacman usage."""
    bashrc_file = user_home / ".bashrc"
    
    try:
        # Read existing .bashrc if it exists
        existing_content = ""
        if bashrc_file.exists():
            with bashrc_file.open("r") as f:
                existing_content = f.read()
        
        # Add SENDUNE customizations
        # Add SENDUNE customizations
        sendune_content = """
# SENDUNE Customizations
# Restrict direct pacman usage - use 'flip' instead
alias pacman='echo "Direct pacman usage is disabled. Use flip instead. Run flip help for commands."'
alias sudo='sudo '  # Allow sudo to work with aliases

# Add flip to PATH if not already
export PATH="$PATH:/usr/local/bin"

# SENDUNE First Run Setup
if [ ! -f ~/.config/ml4w-setup-completed ]; then
    echo "=================================================="
    echo "Welcome to SENDUNE Linux!"
    echo "Starting initial configuration..."
    echo "=================================================="
    
    # Ensure we are in the home directory
    cd ~
    
    echo "################################################################"
    echo "###                                                          ###"
    echo "###        WARNING: DO NOT CLOSE THIS WINDOW                 ###"
    echo "###                                                          ###"
    echo "###  Sendune Installer is finishing the system setup.        ###"
    echo "###  This process is automated. Please wait...               ###"
    echo "###                                                          ###"
    echo "################################################################"
    sleep 3
    
    if [ -d ~/Projects/dotfiles/setup ]; then
        echo "Running ML4W Setup Script..."
        # Run the setup script
        ~/Projects/dotfiles/setup/setup.sh
        
        # Run stow silently
        cd ~/Projects/dotfiles
        stow dotfiles > /dev/null 2>&1
        
        # Mark as complete
        mkdir -p ~/.config > /dev/null 2>&1
        touch ~/.config/ml4w-setup-completed
        
        echo "=================================================="
        echo "Setup Complete! Please restart your session."
        echo "=================================================="
    else
        echo "Error: Dotfiles clone not found at ~/Projects/dotfiles"
    fi
else
    # Normal welcome message
    echo "Welcome to SENDUNE Linux! Use 'flip' for package management."
fi
"""
        
        with bashrc_file.open("w") as f:
            f.write(existing_content + "\n" + sendune_content)
        
        # Set ownership
        if os.name != 'nt' and mount_point:
            # Use arch-chroot to chown files to the target user
            # Paths inside chroot
            username = user_home.name
            path_in_chroot = f"/home/{username}/.bashrc"
            
            try:
                cmd = ["arch-chroot", str(mount_point), "chown", f"{username}:{username}", path_in_chroot]
                subprocess.run(cmd, check=True)
                log.info(f"Set ownership of .bashrc for {username}")
            except Exception as e:
                 log.warn(f"Failed to chown .bashrc via chroot: {e}")

        log.info(f"Updated .bashrc to restrict pacman at {bashrc_file}")
        
    except Exception as e:
        log.error(f"Failed to write .bashrc: {e}")

def install_external_dotfiles(user_home: Path, log: LogFile, mount_point: Path):
    """Clones and installs external dotfiles from GitHub using stow and setup.sh."""
    from .installer_functions import MOCK_MODE
    
    repo_url = "https://github.com/mylinuxforwork/dotfiles"
    username = user_home.name
    
    # Paths relative to the host (ISO/Live environment)
    projects_dir = user_home / "Projects"
    repo_dir = projects_dir / "dotfiles"
    
    # Paths relative to the target root (inside chroot)
    # user_home is something like /mnt/home/username
    # We need the path as seen BY THE USER inside the system: /home/username
    home_in_chroot = Path("/") / "home" / username
    projects_in_chroot = home_in_chroot / "Projects"
    repo_in_chroot = projects_in_chroot / "dotfiles"
    
    log.info(f"Starting automated ML4W dotfiles cloning for {username}")
    print(f"\n🚀 Cloning ML4W dotfiles for {username}...")
    
    try:
        if MOCK_MODE:
            log.info(f"[MOCK] mkdir -p {projects_dir}")
            log.info(f"[MOCK] git clone --depth 1 {repo_url} {repo_dir}")
            return

        # 1. Create Projects directory
        projects_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Clone repository silently
        if not repo_dir.exists():
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(repo_dir)], 
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log.info("Dotfiles repository cloned.")
        
        # 3. Ensure ownership of cloned files using arch-chroot
        if os.name != 'nt':
            # Path inside chroot for Projects is /home/username/Projects
            path_in_chroot = f"/home/{username}/Projects"
            try:
                cmd = ["arch-chroot", str(mount_point), "chown", "-R", f"{username}:{username}", path_in_chroot]
                subprocess.run(
                    cmd, 
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                log.info(f"Set ownership of Projects for {username}")
            except Exception as e:
                log.warn(f"Failed to chown Projects via chroot: {e}")

        log.info("External dotfiles cloned (setup deferred to first login).")
        print("✓ ML4W dotfiles cloned. Setup will run on first login.")
            
    except Exception as e:
        log.error(f"Failed to setup external dotfiles: {e}")
        print(f"❌ Failed to setup dotfiles: {e}")
