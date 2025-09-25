import json
import os
import pathlib
import re
from typing import Any, Dict, List, Optional


def expand_user(path: str) -> str:
    return os.path.expanduser(path)


XDG_CONFIG_HOME = expand_user(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
APP_CONFIG_DIR = os.path.join(XDG_CONFIG_HOME, "git-profile-switcher")
PROFILES_PATH = os.path.join(APP_CONFIG_DIR, "profiles.json")

SSH_DIR = expand_user("~/.ssh")
SSH_CONFIG_PATH = os.path.join(SSH_DIR, "config")


def ensure_app_dirs() -> None:
    pathlib.Path(APP_CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    pathlib.Path(SSH_DIR).mkdir(parents=True, exist_ok=True)
    # Secure permissions for ~/.ssh
    try:
        os.chmod(SSH_DIR, 0o700)
    except PermissionError:
        pass


def read_profiles() -> Dict[str, Any]:
    ensure_app_dirs()
    if not os.path.exists(PROFILES_PATH):
        return {"profiles": []}
    try:
        with open(PROFILES_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"profiles": []}


def write_profiles(data: Dict[str, Any]) -> None:
    ensure_app_dirs()
    tmp_path = PROFILES_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    os.replace(tmp_path, PROFILES_PATH)


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9-_]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered)
    return lowered.strip("-")


def read_ssh_config_text() -> str:
    if not os.path.exists(SSH_CONFIG_PATH):
        return ""
    with open(SSH_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


def write_ssh_config_text(content: str) -> None:
    pathlib.Path(SSH_CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(SSH_CONFIG_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)


def upsert_block_in_ssh_config(alias: str, block: str) -> None:
    content = read_ssh_config_text()
    begin_marker = f"# gps-begin: {alias}\n"
    end_marker = f"# gps-end: {alias}\n"

    if begin_marker in content and end_marker in content:
        pre, _, rest = content.partition(begin_marker)
        _, _, post = rest.partition(end_marker)
        new_content = pre + begin_marker + block + end_marker + post
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        new_content = content + begin_marker + block + end_marker
    write_ssh_config_text(new_content)


def remove_block_in_ssh_config(alias: str) -> None:
    content = read_ssh_config_text()
    begin_marker = f"# gps-begin: {alias}\n"
    end_marker = f"# gps-end: {alias}\n"
    if begin_marker in content and end_marker in content:
        pre, _, rest = content.partition(begin_marker)
        _, _, post = rest.partition(end_marker)
        write_ssh_config_text(pre + post)


def read_file_text(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write_file_text(path: str, text: str, mode: int = 0o600) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    try:
        os.chmod(path, mode)
    except PermissionError:
        pass
