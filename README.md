## Git Profile Switcher (GUI)

A simple Tkinter GUI to manage multiple Git profiles on Linux. It lets you:

- Create profiles with name/email and an SSH key
- Import existing SSH keys from files
- Write per-profile SSH alias blocks into `~/.ssh/config`
- Switch the active global Git profile with one click
- Copy the public key to paste into GitHub/GitLab
- Export SSH private keys to backup or transfer
- See which profile is currently active

### Requirements (Fedora)

- Python 3.9+
- Tkinter

Install Tkinter on Fedora:

```bash
sudo dnf install -y python3-tkinter
```

Optional: create a virtualenv (not required):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
python3 main.py
```

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
