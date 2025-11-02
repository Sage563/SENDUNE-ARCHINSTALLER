# 🌐 SENDUNE Linux (Updated)

This repository contains the SENDUNE installer and helper scripts. See `README.md` for the original project description; this file highlights the new feature-updater and test instructions added during development.

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

## 🧪 Test feature repo (included)

For development and testing there's a `test_feature_repo/` in this workspace with a minimal example:

- `test_feature_repo/install_features.py` - example Python installer that reads `manifest.json` and applies features in an idempotent way.
- `test_feature_repo/manifest.json` - example manifest listing packages, files and scripts.
- `test_feature_repo/features/add-widgets.sh` - a small feature script (creates a marker file under `/tmp` for testing).
- `test_feature_repo/files/etc/sample.conf` - an example file copied by the installer.
- `scripts/package_test_repo.sh` - helper to create a tar.gz archive that mimics GitHub's auto-generated archive layout.

### Quick local test

1. Package the test repo into a tarball that mimics GitHub:

```bash
chmod +x scripts/package_test_repo.sh
./scripts/package_test_repo.sh
# creates /tmp/narchs-features-main.tar.gz
```

2. Run the example installer directly (safe to run as non-root; it will skip package installs when not root):

```bash
python3 test_feature_repo/install_features.py
```

3. Rerun the installer to verify idempotency — the second run should skip already-applied items.

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

- Verify archives before executing (GPG or SHA256). I can add example verification to the updater script if you want.
- Prefer running untrusted or third-party installers with reduced privileges and only escalate operations that require root via careful sudo rules.
- Log activity and rotate logs with `logrotate` or similar.
w