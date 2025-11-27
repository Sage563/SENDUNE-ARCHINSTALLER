# 🌐 SENDUNE Linux

## 🔁 Feature updater (auto-updates from GitHub)

This project includes an optional "feature updater" that the installer can deploy. The updater:

- Downloads a tar.gz archive of a configured GitHub repository (or branch).
- Extracts it and runs a small installer (for example `install_features.py`) from the repo.
- Is installed as a systemd oneshot service plus a systemd timer so it runs shortly after boot and then periodically (daily).

Files installed by the installer:

- `/usr/local/bin/narchs_feature_updater.sh` - shell script that downloads, extracts and runs the repo installer.
- `/etc/systemd/system/narchs-feature-updater.service` - oneshot systemd unit that runs the script.
- `/etc/systemd/system/narchs-feature-updater.timer` - systemd timer to run the updater regularly.

Security note: the updater runs installer code as root by default. Only point it at trusted repositories. Consider adding GPG/SHA verification or running the installer with reduced privileges.

4. To fully simulate the updater script, point the installed `/usr/local/bin/narchs_feature_updater.sh` to the archive (or replace `ARCHIVE_URL` with the local `/tmp` file) and run it as root:

```bash
sudo /usr/local/bin/narchs_feature_updater.sh
```

Check logs and artifacts:

- `/tmp/narchs-feature-installer.log` — installer log in the test example
- `/tmp/narchs-features/add-widgets.txt` — marker written by the test feature script
- `/tmp/narchs-sample.conf` — sample configuration copied by the test manifest
- `/tmp/narchs_features_installed.json` (non-root) or `/var/lib/narchs/features_installed.json` (root) — records what was applied

## 🔐 Security & best practices

- Verify archives before executing (GPG or SHA256).
- Prefer running untrusted or third-party installers with reduced privileges and only escalate operations that require root via careful sudo rules.
- Log activity and rotate logs with `logrotate` or similar.
- ![MADEWITH PYTHON](https://user-images.githubusercontent.com/74038190/212257472-08e52665-c503-4bd9-aa20-f5a4dae769b5.gif)


## Making the iso
Use `curl https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso >> archlinux-2024.08.01-x86_64.iso  ` to install iso(ARCH)
Then run `chmod +x build_arch_iso.sh`
Then run `./build_arch_iso.sh archlinux-2024.08.01-x86_64.iso ./SENDUNE_installer ./SENDUNE_Arch.iso`
Boot up, run `cd /archinstall` , then `python3 -m SENDUNE_installer`


