import os
import shlex
import subprocess
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import re

from .storage import (
    PROFILES_PATH,
    SSH_DIR,
    read_ssh_config_text,
    read_profiles,
    write_profiles,
    slugify,
    upsert_block_in_ssh_config,
    remove_block_in_ssh_config,
)


@dataclass
class Profile:
    id: str
    name: str
    email: str
    host: str
    alias: str
    ssh_key_path: str
    public_key_path: str


class ProfileManager:
    def __init__(self) -> None:
        self._data = read_profiles()
        self._profiles: List[Profile] = [Profile(**p) for p in self._data.get("profiles", [])]

    def reload(self) -> None:
        self.__init__()

    def list_profiles(self) -> List[Profile]:
        return list(self._profiles)

    def get_profile(self, profile_id: str) -> Optional[Profile]:
        for p in self._profiles:
            if p.id == profile_id:
                return p
        return None

    def _ensure_unique_alias(self, alias: str, exclude_id: Optional[str] = None) -> str:
        existing = {p.alias for p in self._profiles if p.id != exclude_id}
        candidate = alias
        index = 2
        while candidate in existing:
            candidate = f"{alias}-{index}"
            index += 1
        return candidate

    def add_profile(self, name: str, email: str, host: str = "github.com", alias: Optional[str] = None) -> Profile:
        base_alias = slugify(alias or name)
        final_alias = self._ensure_unique_alias(base_alias)
        key_name = f"id_ed25519_{final_alias}"
        ssh_key_path = os.path.join(SSH_DIR, key_name)
        public_key_path = ssh_key_path + ".pub"
        profile = Profile(
            id=str(uuid.uuid4()),
            name=name.strip(),
            email=email.strip(),
            host=host.strip() or "github.com",
            alias=final_alias,
            ssh_key_path=ssh_key_path,
            public_key_path=public_key_path,
        )
        self._profiles.append(profile)
        self._persist()
        return profile

    def update_profile(self, profile_id: str, name: Optional[str] = None, email: Optional[str] = None, host: Optional[str] = None, alias: Optional[str] = None) -> Optional[Profile]:
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        if name is not None:
            profile.name = name.strip()
        if email is not None:
            profile.email = email.strip()
        if host is not None:
            profile.host = host.strip() or profile.host
        if alias is not None:
            new_alias = self._ensure_unique_alias(slugify(alias), exclude_id=profile_id)
            if new_alias != profile.alias:
                remove_block_in_ssh_config(profile.alias)
                profile.alias = new_alias
        self._persist()
        # Re-sync SSH block for updated alias/host
        if os.path.exists(profile.ssh_key_path):
            self._write_ssh_config_block(profile)
        return profile

    def delete_profile(self, profile_id: str, remove_keys: bool = True) -> bool:
        profile = self.get_profile(profile_id)
        if not profile:
            return False
        remove_block_in_ssh_config(profile.alias)
        if remove_keys:
            for path in [profile.ssh_key_path, profile.public_key_path]:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
        self._profiles = [p for p in self._profiles if p.id != profile_id]
        self._persist()
        # If active was this profile, clear core.sshCommand if it points to missing key
        active_id = self.get_active_profile_id()
        if active_id == profile_id:
            try:
                subprocess.run(["git", "config", "--global", "--unset", "core.sshCommand"], check=False)
            except Exception:
                pass
        return True

    def generate_ssh_key(self, profile_id: str) -> Tuple[bool, str]:
        profile = self.get_profile(profile_id)
        if not profile:
            return False, "Profile not found"
        if os.path.exists(profile.ssh_key_path):
            return False, "SSH key already exists"
        comment = f"{profile.name} <{profile.email}>"
        try:
            cmd = [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                profile.ssh_key_path,
                "-C",
                comment,
                "-N",
                "",
            ]
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            return False, f"ssh-keygen failed: {exc}"
        # Fix permissions just in case
        try:
            os.chmod(profile.ssh_key_path, 0o600)
        except PermissionError:
            pass
        self._write_ssh_config_block(profile)
        return True, "SSH key generated"

    def _write_ssh_config_block(self, profile: Profile) -> None:
        block = (
            f"Host {profile.alias}\n"
            f"  HostName {profile.host}\n"
            f"  User git\n"
            f"  IdentityFile {profile.ssh_key_path}\n"
            f"  IdentitiesOnly yes\n"
        )
        upsert_block_in_ssh_config(profile.alias, block)

    def set_active(self, profile_id: str) -> Tuple[bool, str]:
        profile = self.get_profile(profile_id)
        if not profile:
            return False, "Profile not found"
        if not os.path.exists(profile.ssh_key_path):
            return False, "SSH key not found. Generate it first."
        ssh_command = f"ssh -i {shlex.quote(profile.ssh_key_path)} -o IdentitiesOnly=yes"
        try:
            subprocess.run(["git", "config", "--global", "user.name", profile.name], check=True)
            subprocess.run(["git", "config", "--global", "user.email", profile.email], check=True)
            subprocess.run(["git", "config", "--global", "core.sshCommand", ssh_command], check=True)
        except subprocess.CalledProcessError as exc:
            return False, f"Failed to set active profile: {exc}"
        # Ensure SSH block exists for convenience alias usage
        self._write_ssh_config_block(profile)
        return True, "Active profile set"

    def get_active_profile_id(self) -> Optional[str]:
        try:
            res = subprocess.run([
                "git",
                "config",
                "--global",
                "--get",
                "core.sshCommand",
            ], check=False, capture_output=True, text=True)
        except Exception:
            return None
        if res.returncode != 0:
            return None
        cmd = res.stdout.strip()
        if not cmd:
            return None
        try:
            parts = shlex.split(cmd)
        except Exception:
            parts = cmd.split()
        key_path: Optional[str] = None
        for idx, token in enumerate(parts):
            if token == "-i" and idx + 1 < len(parts):
                key_path = parts[idx + 1]
                break
        if not key_path:
            return None
        key_path = os.path.expanduser(key_path)
        for p in self._profiles:
            if os.path.abspath(p.ssh_key_path) == os.path.abspath(key_path):
                return p.id
        return None

    def _persist(self) -> None:
        data = {"profiles": [asdict(p) for p in self._profiles]}
        write_profiles(data)

    def import_from_ssh_config(self) -> int:
        text = read_ssh_config_text()
        if not text:
            return 0

        def flush_block(aliases, host_name, identity_file) -> None:
            nonlocal imported
            if not aliases or not identity_file:
                return
            # Expand ~ in key path
            key_path = os.path.expanduser(identity_file)
            # Skip if path looks like a directory or wildcard
            if any(ch in key_path for ch in ["*", "?"]):
                return
            for alias in aliases:
                alias = alias.strip()
                if not alias or any(ch in alias for ch in ["*", "?", " "]):
                    continue
                # Skip if alias already exists
                if any(p.alias == alias for p in self._profiles):
                    continue
                # Create profile with empty email; user can edit later
                profile = Profile(
                    id=str(uuid.uuid4()),
                    name=alias,
                    email="",
                    host=host_name or "github.com",
                    alias=alias,
                    ssh_key_path=key_path,
                    public_key_path=key_path + ".pub",
                )
                self._profiles.append(profile)
                imported += 1

        imported = 0
        current_aliases = []
        current_host_name: Optional[str] = None
        current_identity: Optional[str] = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            lower = line.lower()
            if lower.startswith("host "):
                # New block; flush previous
                flush_block(current_aliases, current_host_name, current_identity)
                # Start new
                parts = line.split()[1:]
                current_aliases = parts
                current_host_name = None
                current_identity = None
                continue
            if lower.startswith("hostname "):
                current_host_name = line.split(None, 1)[1].strip()
                continue
            if lower.startswith("identityfile "):
                current_identity = line.split(None, 1)[1].strip()
                continue

        # Flush last
        flush_block(current_aliases, current_host_name, current_identity)

        if imported:
            self._persist()
        return imported

    def import_from_git_aliases(self) -> int:
        try:
            res = subprocess.run([
                "git",
                "config",
                "--global",
                "--get-regexp",
                r"^alias\.",
            ], check=False, capture_output=True, text=True)
        except Exception:
            return 0
        if res.returncode != 0:
            return 0
        lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
        if not lines:
            return 0

        alias_re = re.compile(r"^alias\.([^ ]+)\s+(.+)$")
        name_re = re.compile(r"user\.name\s+\"([^\"]+)\"")
        email_re = re.compile(r"user\.email\s+\"([^\"]+)\"")

        def base_from_alias_key(key: str) -> str:
            base = key
            for suff in ("-global", "-local"):
                if base.endswith(suff):
                    base = base[: -len(suff)]
            base = base.replace("github-", "")
            return slugify(base)

        updated = 0
        for ln in lines:
            m = alias_re.match(ln.strip())
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if not val.startswith("!"):
                continue
            nm = name_re.search(val)
            em = email_re.search(val)
            if not nm or not em:
                continue
            name_val = nm.group(1).strip()
            email_val = em.group(1).strip()
            base = base_from_alias_key(key)
            # Find best matching profile by alias
            candidates = [p for p in self._profiles if base in p.alias or p.alias.endswith(base)]
            target: Optional[Profile] = None
            if len(candidates) == 1:
                target = candidates[0]
            elif len(candidates) > 1:
                exact = [p for p in candidates if p.alias == base or p.alias.endswith(f"-{base}")]
                target = exact[0] if exact else candidates[0]
            else:
                # Create a new profile with this alias, without touching keys
                key_name = f"id_ed25519_{base}"
                ssh_key_path = os.path.join(SSH_DIR, key_name)
                target = Profile(
                    id=str(uuid.uuid4()),
                    name=name_val,
                    email=email_val,
                    host="github.com",
                    alias=base,
                    ssh_key_path=ssh_key_path,
                    public_key_path=ssh_key_path + ".pub",
                )
                # Ensure alias uniqueness if needed
                if any(p.alias == target.alias for p in self._profiles):
                    target.alias = self._ensure_unique_alias(target.alias)
                self._profiles.append(target)
            # Update name/email if empty or different
            changed = False
            if not target.name or target.name != name_val:
                target.name = name_val
                changed = True
            if not target.email or target.email != email_val:
                target.email = email_val
                changed = True
            if changed:
                updated += 1
        if updated:
            self._persist()
        return updated
