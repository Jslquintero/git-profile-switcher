# Git Profile Switcher

A GTK3 application for managing multiple Git profiles on Linux.
Runs as a system tray icon by default and provides a full management window for detailed operations.

## Features

- **Profile management** — create, edit, and delete profiles (name, email, Git host, SSH alias)
- **SSH key handling** — generate ed25519 keys, import existing keys from files, export keys for backup
- **SSH config integration** — automatically writes per-profile `Host` blocks in `~/.ssh/config`
- **One-click switching** — sets `user.name`, `user.email`, and `core.sshCommand` globally
- **System tray** — shows the active profile and allows quick switching via menu
- **Desktop notifications** — notifies on profile switch
- **Import** — bulk-import profiles from `~/.ssh/config` or existing git aliases
- **Clipboard** — copy the public key for pasting into GitHub/GitLab

## Installation

### RPM (Fedora / RHEL)

```bash
./build-rpm.sh
sudo dnf install ~/rpmbuild/RPMS/noarch/git-profile-switcher-1.0.0-*.noarch.rpm
```

After installing, `git-profile-switcher` is available system-wide and appears in your application menu.

### Manual (any distro)

Install the system dependencies first:

**Fedora:**
```bash
sudo dnf install -y python3-gobject libappindicator-gtk3
```

**Debian / Ubuntu:**
```bash
sudo apt-get install -y python3-gi gir1.2-appindicator3-0.1
```

Then run the install script to set up the desktop entry and icon:

```bash
./install-tray.sh
```

## Usage

```
git-profile-switcher [OPTION]

Options:
  -g, --gui     Launch the GTK3 management window
  -t, --tray    Launch the system tray icon (default)
  -h, --help    Show this help message and exit
```

The system tray icon is the default mode. Use `--gui` to open the full management window directly.

### Autostart on login

```bash
mkdir -p ~/.config/autostart
ln -s /usr/share/applications/git-profile-switcher.desktop ~/.config/autostart/
```

## How it works

Profiles are stored in `~/.config/git-profile-switcher/profiles.json`.

Each profile gets an ed25519 SSH key at `~/.ssh/id_ed25519_<alias>` and a corresponding
block in `~/.ssh/config`:

```
# gps-begin: <alias>
Host <alias>
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_<alias>
  IdentitiesOnly yes
# gps-end: <alias>
```

Switching the active profile updates the global Git config:

- `user.name`
- `user.email`
- `core.sshCommand` (points to the profile's identity file)

You can use the SSH alias in remotes, e.g. `git@my-alias:owner/repo.git`.

## License

MIT
