## Git Profile Switcher

A GTK3 application to manage multiple Git profiles on Linux. It lets you:

- Create profiles with name/email and an SSH key
- Import existing SSH keys from files
- Write per-profile SSH alias blocks into `~/.ssh/config`
- Switch the active global Git profile with one click
- Copy the public key to paste into GitHub/GitLab
- Export SSH private keys to backup or transfer
- See which profile is currently active
- System tray icon for quick profile switching

### Requirements

- Python 3.9+
- PyGObject (GTK3 bindings)
- AppIndicator3 (system tray support)

Install on Fedora:

```bash
sudo dnf install -y python3-gobject libappindicator-gtk3
```

Install on Debian/Ubuntu:

```bash
sudo apt-get install -y python3-gi gir1.2-appindicator3-0.1
```

### Run

Launch the system tray icon (default):
```bash
python3 main.py
```

Launch the GTK3 management window:
```bash
python3 main.py --gui
```

Show help:
```bash
python3 main.py --help
```

### Installing the Tray Application

To install the tray application for easy access and autostart:

```bash
./install-tray.sh
```

This will:
1. Install required system dependencies
2. Create a desktop entry in `~/.local/share/applications/`
3. Install the application icon

To enable autostart on login:
```bash
ln -s ~/.local/share/applications/git-profile-switcher-tray.desktop ~/.config/autostart/
```

### RPM Package

Build an RPM package for Fedora/RHEL:

```bash
./build-rpm.sh
```

The resulting RPM will be in `~/rpmbuild/RPMS/noarch/`.

### How it works

- Profiles are stored in `~/.config/git-profile-switcher/profiles.json`.
- SSH keys are created in `~/.ssh/id_ed25519_<profile-slug>`.
- SSH config blocks are managed inside `~/.ssh/config` between markers like:

```
# gps-begin: <alias>
Host <alias>
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_<profile-slug>
  IdentitiesOnly yes
# gps-end: <alias>
```

- Switching the active profile updates global Git config:
  - `user.name`
  - `user.email`
  - `core.sshCommand` (sets the identity file globally)

### Notes

- After creating a profile, click "Copy Public Key" and add it to GitHub/GitLab.
- You can use the alias in remotes, e.g. `git@my-github-alias:owner/repo.git`.
- Deleting a profile removes its SSH config block and key files.
- The tray icon shows the active profile's alias and allows quick switching.
