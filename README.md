# 🌐 SENDUNE Linux

- Verify archives before executing (GPG or SHA256).
- Prefer running untrusted or third-party installers with reduced privileges and only escalate operations that require root via careful sudo rules.
- Log activity and rotate logs with `logrotate` or similar.
- ![MADEWITH PYTHON](https://user-images.githubusercontent.com/74038190/212257472-08e52665-c503-4bd9-aa20-f5a4dae769b5.gif)

## Making the iso
Use `curl https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso >> archlinux-2024.08.01-x86_64.iso  ` to install iso(ARCH)
Then run `chmod +x build_arch_iso.sh`
Then run `./build_arch_iso.sh archlinux-2024.08.01-x86_64.iso ./SENDUNE_installer ./SENDUNE_Arch.iso`
Boot up, run `cd /archinstall` , then `python3 -m SENDUNE_installer`


