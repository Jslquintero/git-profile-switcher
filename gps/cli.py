import curses
import os
import shutil
import subprocess
from typing import Optional, List, Tuple
from .manager import ProfileManager, Profile


def get_current_git_config() -> Tuple[Optional[str], Optional[str]]:
    """Get current git user.name and user.email from global config."""
    try:
        name_result = subprocess.run(
            ["git", "config", "--global", "user.name"],
            check=False,
            capture_output=True,
            text=True
        )
        email_result = subprocess.run(
            ["git", "config", "--global", "user.email"],
            check=False,
            capture_output=True,
            text=True
        )

        name = name_result.stdout.strip() if name_result.returncode == 0 else None
        email = email_result.stdout.strip() if email_result.returncode == 0 else None

        return name, email
    except Exception:
        return None, None


class CursesUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.manager = ProfileManager()

        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Active profile
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Headers
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Info
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)  # Error

        # Hide cursor
        curses.curs_set(0)

        # Menu options
        self.menu_items = [
            "Add Profile",
            "Edit Profile",
            "Delete Profile",
            "Set Active Profile",
            "Generate SSH Key",
            "Copy Public Key",
            "Export SSH Key",
            "Import SSH Key",
            "Import from SSH Config",
            "Import from Git Aliases",
            "View SSH Config",
            "Refresh",
            "Quit"
        ]

        self.current_menu_idx = 0

    def show_message(self, message: str, color_pair: int = 0, wait: bool = True):
        """Show a message box."""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        lines = message.split('\n')
        y = height // 2 - len(lines) // 2

        for line in lines:
            x = width // 2 - len(line) // 2
            if y < height - 1:
                self.stdscr.addstr(y, max(0, x), line[:width-1], curses.color_pair(color_pair))
                y += 1

        if wait:
            self.stdscr.addstr(height - 2, 2, "Press any key to continue...", curses.color_pair(4))
            self.stdscr.refresh()
            self.stdscr.getch()

    def get_input(self, prompt: str, default: str = "", y_pos: int = None) -> Optional[str]:
        """Get text input from user. Returns None if ESC is pressed."""
        curses.echo()
        curses.curs_set(1)

        height, width = self.stdscr.getmaxyx()
        if y_pos is None:
            y_pos = height // 2

        # Show prompt
        self.stdscr.addstr(y_pos, 2, prompt, curses.color_pair(4))
        if default:
            self.stdscr.addstr(y_pos + 1, 2, f"[{default}]: ")
        else:
            self.stdscr.addstr(y_pos + 1, 2, ": ")

        self.stdscr.refresh()

        # Get input
        input_str = ""
        x_start = 4 if not default else len(default) + 5

        while True:
            try:
                ch = self.stdscr.getch()

                # ESC key
                if ch == 27:
                    curses.noecho()
                    curses.curs_set(0)
                    return None

                # Enter key
                if ch in [10, 13]:
                    break

                # Backspace
                if ch in [curses.KEY_BACKSPACE, 127, 8]:
                    if input_str:
                        input_str = input_str[:-1]
                        y, x = self.stdscr.getyx()
                        self.stdscr.move(y, x - 1)
                        self.stdscr.delch()

                # Regular character
                elif 32 <= ch <= 126:
                    input_str += chr(ch)

            except KeyboardInterrupt:
                curses.noecho()
                curses.curs_set(0)
                return None

        curses.noecho()
        curses.curs_set(0)

        result = input_str.strip()
        return result if result else default

    def confirm(self, message: str) -> bool:
        """Show a confirmation dialog. ESC or 'n' returns False."""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        y = height // 2
        self.stdscr.addstr(y, 2, message, curses.color_pair(3))
        self.stdscr.addstr(y + 2, 2, "[y]es / [n]o / [ESC] cancel", curses.color_pair(4))
        self.stdscr.refresh()

        while True:
            ch = self.stdscr.getch()
            if ch == 27:  # ESC
                return False
            if ch in [ord('y'), ord('Y')]:
                return True
            if ch in [ord('n'), ord('N')]:
                return False

    def select_option(self, title: str, options: List[Tuple[str, str]]) -> Optional[int]:
        """
        Show option selection menu with arrow keys.
        options: List of (label, description) tuples
        Returns: index of selected option, or None if ESC pressed
        """
        selected_idx = 0

        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()

            # Title
            self.stdscr.addstr(1, 2, title, curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(3, 2, "Use ↑/↓ arrows to navigate, Enter to select, ESC to cancel", curses.color_pair(4))

            # Display options
            y = 5
            for idx, (label, description) in enumerate(options):
                if y >= height - 4:
                    break

                if idx == selected_idx:
                    self.stdscr.addstr(y, 2, f"► {label}", curses.color_pair(1) | curses.A_BOLD)
                    if description:
                        self.stdscr.addstr(y + 1, 4, description, curses.color_pair(4))
                else:
                    self.stdscr.addstr(y, 2, f"  {label}")
                    if description:
                        self.stdscr.addstr(y + 1, 4, description, curses.color_pair(4))

                y += 2

            self.stdscr.refresh()

            # Handle input
            key = self.stdscr.getch()

            if key == 27:  # ESC
                return None
            elif key == curses.KEY_UP:
                selected_idx = (selected_idx - 1) % len(options)
            elif key == curses.KEY_DOWN:
                selected_idx = (selected_idx + 1) % len(options)
            elif key in [10, 13]:  # Enter
                return selected_idx

    def select_profile(self, title: str) -> Optional[Profile]:
        """Show profile selection menu with arrow keys. Returns None if ESC pressed."""
        profiles = self.manager.list_profiles()
        if not profiles:
            self.show_message("No profiles available")
            return None

        selected_idx = 0

        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()

            # Title
            self.stdscr.addstr(1, 2, title, curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(3, 2, "Use ↑/↓ arrows to navigate, Enter to select, ESC to cancel", curses.color_pair(4))

            # Display profiles
            y = 5
            for idx, profile in enumerate(profiles):
                if y >= height - 2:
                    break

                display_text = f"{idx + 1}. {profile.name} ({profile.email}) - {profile.alias}"
                if len(display_text) > width - 4:
                    display_text = display_text[:width - 7] + "..."

                if idx == selected_idx:
                    self.stdscr.addstr(y, 2, display_text, curses.color_pair(1))
                else:
                    self.stdscr.addstr(y, 2, display_text)

                y += 1

            self.stdscr.refresh()

            # Handle input
            key = self.stdscr.getch()

            if key == 27:  # ESC
                return None
            elif key == curses.KEY_UP:
                selected_idx = (selected_idx - 1) % len(profiles)
            elif key == curses.KEY_DOWN:
                selected_idx = (selected_idx + 1) % len(profiles)
            elif key in [10, 13]:  # Enter
                return profiles[selected_idx]

    def display_main_screen(self):
        """Display the main screen with profiles and menu."""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        self.manager.reload()
        profiles = self.manager.list_profiles()
        active_id = self.manager.get_active_profile_id()
        current_name, current_email = get_current_git_config()

        # Header
        y = 0
        self.stdscr.addstr(y, 2, "=" * (width - 4), curses.color_pair(3))
        y += 1
        title = "Git Profile Switcher"
        self.stdscr.addstr(y, (width - len(title)) // 2, title, curses.color_pair(3) | curses.A_BOLD)
        y += 1
        self.stdscr.addstr(y, 2, "=" * (width - 4), curses.color_pair(3))
        y += 2

        # Active profile
        active_profile = None
        if active_id:
            active_profile = self.manager.get_profile(active_id)

        if active_profile:
            self.stdscr.addstr(y, 2, "Active Profile:", curses.color_pair(2) | curses.A_BOLD)
            y += 1
            self.stdscr.addstr(y, 4, f"Name:      {current_name or '<not set>'}", curses.color_pair(2))
            y += 1
            self.stdscr.addstr(y, 4, f"Email:     {current_email or '<not set>'}", curses.color_pair(2))
            y += 1
            self.stdscr.addstr(y, 4, f"SSH Alias: {active_profile.alias}", curses.color_pair(2))
            y += 1
        else:
            self.stdscr.addstr(y, 2, "Active Profile: None", curses.color_pair(4))
            y += 1

        y += 1
        self.stdscr.addstr(y, 2, "-" * (width - 4))
        y += 1

        # Profile table header
        header = f"{'#':<4} {'Name':<20} {'Email':<25} {'SSH Alias':<15} {'Host':<15}"
        if len(header) > width - 4:
            header = header[:width - 4]
        self.stdscr.addstr(y, 2, header, curses.color_pair(3) | curses.A_BOLD)
        y += 1
        self.stdscr.addstr(y, 2, "-" * (width - 4))
        y += 1

        # Profiles
        profile_start_y = y
        max_profiles_display = height - y - 13  # Leave room for menu

        for idx, profile in enumerate(profiles[:max_profiles_display]):
            marker = "*" if profile.id == active_id else " "

            name = profile.name[:19] if len(profile.name) > 19 else profile.name
            email = profile.email[:24] if len(profile.email) > 24 else profile.email
            alias = profile.alias[:14] if len(profile.alias) > 14 else profile.alias
            host = profile.host[:14] if len(profile.host) > 14 else profile.host

            row = f"{marker}{idx + 1:<3} {name:<20} {email:<25} {alias:<15} {host:<15}"
            if len(row) > width - 4:
                row = row[:width - 4]

            color = curses.color_pair(2) if profile.id == active_id else 0
            self.stdscr.addstr(y, 2, row, color)
            y += 1

        if len(profiles) > max_profiles_display:
            self.stdscr.addstr(y, 2, f"... and {len(profiles) - max_profiles_display} more profiles", curses.color_pair(4))
            y += 1

        # Menu
        y = height - 11
        self.stdscr.addstr(y, 2, "=" * (width - 4), curses.color_pair(3))
        y += 1

        for idx, item in enumerate(self.menu_items):
            if idx == self.current_menu_idx:
                self.stdscr.addstr(y, 2, f"► {item}", curses.color_pair(1) | curses.A_BOLD)
            else:
                self.stdscr.addstr(y, 2, f"  {item}")
            y += 1
            if y >= height - 1:
                break

        # Footer
        self.stdscr.addstr(height - 1, 2, "↑/↓: Navigate | Enter: Select | ESC: Back/Quit", curses.color_pair(4))

        self.stdscr.refresh()

    def add_profile(self):
        """Add a new profile."""
        # First, ask for SSH type
        ssh_type_options = [
            ("Normal SSH", "For GitHub, GitLab, Bitbucket, and other standard Git hosts"),
            ("Azure DevOps SSH", "For Azure DevOps repositories (ssh.dev.azure.com)")
        ]

        ssh_type_idx = self.select_option("Select SSH Type", ssh_type_options)
        if ssh_type_idx is None:
            return

        # Set default host based on SSH type
        if ssh_type_idx == 0:  # Normal SSH
            default_host = "github.com"
        else:  # Azure DevOps SSH
            default_host = "ssh.dev.azure.com"

        self.stdscr.clear()
        self.stdscr.addstr(1, 2, "Add New Profile", curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(2, 2, "Press ESC to cancel", curses.color_pair(4))
        self.stdscr.refresh()

        name = self.get_input("Git Name", y_pos=4)
        if name is None:
            return
        if not name:
            self.show_message("Error: Name is required", color_pair=5)
            return

        email = self.get_input("Email", y_pos=7)
        if email is None:
            return
        if not email:
            self.show_message("Error: Email is required", color_pair=5)
            return

        host = self.get_input("Host", default=default_host, y_pos=10)
        if host is None:
            return

        alias = self.get_input("SSH Alias (optional, defaults to name)", y_pos=13)
        if alias is None:
            return

        profile = self.manager.add_profile(name=name, email=email, host=host, alias=alias)

        # Generate SSH key automatically
        ok, msg = self.manager.generate_ssh_key(profile.id)
        if ok:
            self.show_message(f"Success!\n\nProfile '{profile.name}' created\nSSH Alias: {profile.alias}\nSSH config has been updated", color_pair=2)
        else:
            self.show_message(f"Profile created but SSH key generation failed:\n{msg}", color_pair=5)

    def edit_profile(self):
        """Edit an existing profile."""
        profile = self.select_profile("Select Profile to Edit")
        if not profile:
            return

        self.stdscr.clear()
        self.stdscr.addstr(1, 2, f"Editing: {profile.name}", curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(2, 2, "Press Enter to keep current value, ESC to cancel", curses.color_pair(4))
        self.stdscr.refresh()

        name = self.get_input("Git Name", default=profile.name, y_pos=4)
        if name is None:
            return

        email = self.get_input("Email", default=profile.email, y_pos=7)
        if email is None:
            return

        host = self.get_input("Host", default=profile.host, y_pos=10)
        if host is None:
            return

        alias = self.get_input("SSH Alias", default=profile.alias, y_pos=13)
        if alias is None:
            return

        updated = self.manager.update_profile(
            profile.id,
            name=name if name else None,
            email=email if email else None,
            host=host if host else None,
            alias=alias if alias else None
        )

        if updated:
            self.show_message("Success! Profile updated", color_pair=2)
        else:
            self.show_message("Error: Failed to update profile", color_pair=5)

    def delete_profile(self):
        """Delete a profile."""
        profile = self.select_profile("Select Profile to Delete")
        if not profile:
            return

        if self.confirm(f"Delete '{profile.name}' and remove SSH keys?\nThis cannot be undone!"):
            ok = self.manager.delete_profile(profile.id, remove_keys=True)
            if ok:
                self.show_message("Success! Profile deleted", color_pair=2)
            else:
                self.show_message("Error: Failed to delete profile", color_pair=5)

    def set_active_profile(self):
        """Set the active profile."""
        profile = self.select_profile("Select Profile to Activate")
        if not profile:
            return

        ok, msg = self.manager.set_active(profile.id)
        if ok:
            self.show_message(f"Success!\n\n{msg}\nActive: {profile.name} ({profile.email})", color_pair=2)
        else:
            self.show_message(f"Error: {msg}", color_pair=5)

    def generate_ssh_key(self):
        """Generate SSH key for a profile."""
        profile = self.select_profile("Select Profile to Generate SSH Key")
        if not profile:
            return

        ok, msg = self.manager.generate_ssh_key(profile.id)
        color = 2 if ok else 5
        self.show_message(msg, color_pair=color)

    def copy_public_key(self):
        """Copy public key to clipboard."""
        profile = self.select_profile("Select Profile to Copy Public Key")
        if not profile:
            return

        try:
            with open(profile.public_key_path, "r", encoding="utf-8") as fh:
                pub = fh.read().strip()

            # Try different clipboard tools
            clipboard_set = False
            for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard"], ["pbcopy"]]:
                try:
                    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    proc.communicate(pub.encode())
                    if proc.returncode == 0:
                        clipboard_set = True
                        break
                except FileNotFoundError:
                    continue

            if clipboard_set:
                self.show_message("Success! Public key copied to clipboard", color_pair=2)
            else:
                self.show_message(f"Clipboard tool not found.\n\nHere's the public key:\n\n{pub}", color_pair=4)

        except FileNotFoundError:
            self.show_message("Error: Public key not found. Generate the key first.", color_pair=5)

    def export_ssh_key(self):
        """Export SSH private key."""
        profile = self.select_profile("Select Profile to Export SSH Key")
        if not profile:
            return

        if not os.path.exists(profile.ssh_key_path):
            self.show_message("Error: SSH key not found. Generate the key first.", color_pair=5)
            return

        default_name = f"id_ed25519_{profile.alias}"
        file_path = self.get_input(f"Export to path", default=default_name, y_pos=5)

        if not file_path:
            return

        file_path = os.path.expanduser(file_path)

        try:
            shutil.copy2(profile.ssh_key_path, file_path)
            os.chmod(file_path, 0o600)
            self.show_message(f"Success!\n\nSSH private key exported to:\n{file_path}", color_pair=2)
        except Exception as e:
            self.show_message(f"Error: Failed to export key:\n{e}", color_pair=5)

    def import_ssh_key(self):
        """Import an SSH key and create a profile."""
        self.stdscr.clear()
        self.stdscr.addstr(1, 2, "Import SSH Key", curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(2, 2, "Press ESC to cancel", curses.color_pair(4))
        self.stdscr.refresh()

        key_path = self.get_input("Path to SSH private key", y_pos=4)
        if not key_path:
            return

        key_path = os.path.expanduser(key_path)

        if not os.path.exists(key_path):
            self.show_message("Error: File does not exist", color_pair=5)
            return

        # Check if it looks like a private key
        try:
            with open(key_path, "r", encoding="utf-8") as fh:
                content = fh.read(100)
                if "PRIVATE KEY" not in content:
                    if not self.confirm("This doesn't look like a private key. Continue anyway?"):
                        return
        except Exception:
            self.show_message("Error: Cannot read the file", color_pair=5)
            return

        # Extract suggested name from filename
        filename = os.path.basename(key_path)
        suggested_name = filename.replace("id_", "").replace("_rsa", "").replace("_ed25519", "").replace("_ecdsa", "")
        if not suggested_name or suggested_name == filename:
            suggested_name = "imported"

        # Ask for SSH type
        ssh_type_options = [
            ("Normal SSH", "For GitHub, GitLab, Bitbucket, and other standard Git hosts"),
            ("Azure DevOps SSH", "For Azure DevOps repositories (ssh.dev.azure.com)")
        ]

        ssh_type_idx = self.select_option("Select SSH Type", ssh_type_options)
        if ssh_type_idx is None:
            return

        # Set default host based on SSH type
        if ssh_type_idx == 0:  # Normal SSH
            default_host = "github.com"
        else:  # Azure DevOps SSH
            default_host = "ssh.dev.azure.com"

        self.stdscr.clear()
        self.stdscr.addstr(1, 2, "Create Profile for this Key", curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.refresh()

        name = self.get_input("Git Name", default=suggested_name, y_pos=3)
        if name is None or not name:
            return

        email = self.get_input("Email", y_pos=6)
        if email is None or not email:
            return

        host = self.get_input("Host", default=default_host, y_pos=9)
        if host is None:
            return

        alias = self.get_input("SSH Alias", default=suggested_name, y_pos=12)
        if alias is None:
            return

        try:
            # Copy the key to ~/.ssh with proper naming
            target_key_name = f"id_ed25519_{self.manager._ensure_unique_alias(alias.lower().replace(' ', '-'))}"
            target_key_path = os.path.join(os.path.expanduser("~/.ssh"), target_key_name)
            target_pub_path = target_key_path + ".pub"

            # Copy private key
            shutil.copy2(key_path, target_key_path)
            os.chmod(target_key_path, 0o600)

            # Try to copy public key if it exists
            source_pub_path = key_path + ".pub"
            pub_generated = False
            if os.path.exists(source_pub_path):
                shutil.copy2(source_pub_path, target_pub_path)
                os.chmod(target_pub_path, 0o644)
            else:
                # Generate public key from private key
                try:
                    with open(target_pub_path, 'w') as f:
                        subprocess.run([
                            "ssh-keygen", "-y", "-f", target_key_path
                        ], check=True, stdout=f)
                    os.chmod(target_pub_path, 0o644)
                    pub_generated = True
                except Exception:
                    pass

            # Create profile
            profile = self.manager.add_profile(name=name, email=email, host=host, alias=alias)
            # Update the key paths to point to our copied files
            profile.ssh_key_path = target_key_path
            profile.public_key_path = target_pub_path
            self.manager._persist()

            # Write SSH config block
            self.manager._write_ssh_config_block(profile)

            msg = f"Success!\n\nSSH key imported as profile '{name}'\nSSH config has been updated"
            if pub_generated:
                msg += "\n\nNote: Public key was generated from private key"

            self.show_message(msg, color_pair=2)

        except Exception as e:
            self.show_message(f"Error: Failed to import SSH key:\n{e}", color_pair=5)

    def import_from_ssh_config(self):
        """Import profiles from ~/.ssh/config."""
        imported = self.manager.import_from_ssh_config()
        if imported:
            self.show_message(f"Success!\n\nImported {imported} host(s) from ~/.ssh/config", color_pair=2)
        else:
            self.show_message("No importable hosts found or all were already present", color_pair=4)

    def import_from_git_aliases(self):
        """Import profiles from git aliases."""
        updated = self.manager.import_from_git_aliases()
        if updated:
            self.show_message(f"Success!\n\nMapped {updated} profile(s) from git aliases", color_pair=2)
        else:
            self.show_message("No matching aliases found", color_pair=4)

    def view_ssh_config(self):
        """View the SSH config file."""
        ssh_config_path = os.path.expanduser("~/.ssh/config")

        if not os.path.exists(ssh_config_path):
            self.show_message("SSH config file does not exist\n\n~/.ssh/config not found", color_pair=4)
            return

        try:
            with open(ssh_config_path, "r", encoding="utf-8") as fh:
                content = fh.read()

            if not content.strip():
                self.show_message("SSH config file is empty", color_pair=4)
                return

            # Display the SSH config with scrolling support
            lines = content.split('\n')
            scroll_offset = 0
            max_display_lines = 0

            while True:
                self.stdscr.clear()
                height, width = self.stdscr.getmaxyx()

                # Header
                self.stdscr.addstr(0, 2, "SSH Config (~/.ssh/config)", curses.color_pair(3) | curses.A_BOLD)
                self.stdscr.addstr(1, 2, "=" * (width - 4), curses.color_pair(3))

                # Calculate max display lines
                max_display_lines = height - 5  # Leave room for header and footer

                # Display lines with scrolling
                y = 2
                for idx in range(scroll_offset, min(len(lines), scroll_offset + max_display_lines)):
                    line = lines[idx]
                    # Truncate line if too long
                    if len(line) > width - 4:
                        line = line[:width - 7] + "..."

                    # Color code different line types
                    color = 0
                    if line.strip().startswith('#'):
                        color = curses.color_pair(4)  # Comments in cyan
                    elif line.strip().startswith('Host '):
                        color = curses.color_pair(3) | curses.A_BOLD  # Host entries in yellow bold
                    elif any(line.strip().startswith(key) for key in ['HostName', 'User', 'IdentityFile', 'IdentitiesOnly']):
                        color = curses.color_pair(2)  # Config keys in green

                    try:
                        self.stdscr.addstr(y, 2, line, color)
                    except curses.error:
                        pass  # Ignore if we can't write (e.g., last line)

                    y += 1

                # Footer with instructions
                footer_y = height - 2
                self.stdscr.addstr(footer_y, 2, "=" * (width - 4), curses.color_pair(3))

                scroll_info = f"Lines {scroll_offset + 1}-{min(len(lines), scroll_offset + max_display_lines)} of {len(lines)}"
                instructions = "↑/↓: Scroll | ESC/q: Close"

                self.stdscr.addstr(footer_y + 1, 2, scroll_info, curses.color_pair(4))
                self.stdscr.addstr(footer_y + 1, width - len(instructions) - 3, instructions, curses.color_pair(4))

                self.stdscr.refresh()

                # Handle input
                key = self.stdscr.getch()

                if key == 27 or key == ord('q') or key == ord('Q'):  # ESC or q
                    break
                elif key == curses.KEY_UP:
                    scroll_offset = max(0, scroll_offset - 1)
                elif key == curses.KEY_DOWN:
                    scroll_offset = min(len(lines) - max_display_lines, scroll_offset + 1)
                    scroll_offset = max(0, scroll_offset)
                elif key == curses.KEY_PPAGE:  # Page Up
                    scroll_offset = max(0, scroll_offset - max_display_lines)
                elif key == curses.KEY_NPAGE:  # Page Down
                    scroll_offset = min(len(lines) - max_display_lines, scroll_offset + max_display_lines)
                    scroll_offset = max(0, scroll_offset)
                elif key == curses.KEY_HOME:  # Home
                    scroll_offset = 0
                elif key == curses.KEY_END:  # End
                    scroll_offset = max(0, len(lines) - max_display_lines)

        except Exception as e:
            self.show_message(f"Error reading SSH config:\n{e}", color_pair=5)

    def run(self):
        """Main loop."""
        while True:
            self.display_main_screen()

            # Handle input
            key = self.stdscr.getch()

            if key == 27:  # ESC
                if self.confirm("Are you sure you want to quit?"):
                    break
            elif key == curses.KEY_UP:
                self.current_menu_idx = (self.current_menu_idx - 1) % len(self.menu_items)
            elif key == curses.KEY_DOWN:
                self.current_menu_idx = (self.current_menu_idx + 1) % len(self.menu_items)
            elif key in [10, 13]:  # Enter
                selected = self.menu_items[self.current_menu_idx]

                if selected == "Add Profile":
                    self.add_profile()
                elif selected == "Edit Profile":
                    self.edit_profile()
                elif selected == "Delete Profile":
                    self.delete_profile()
                elif selected == "Set Active Profile":
                    self.set_active_profile()
                elif selected == "Generate SSH Key":
                    self.generate_ssh_key()
                elif selected == "Copy Public Key":
                    self.copy_public_key()
                elif selected == "Export SSH Key":
                    self.export_ssh_key()
                elif selected == "Import SSH Key":
                    self.import_ssh_key()
                elif selected == "Import from SSH Config":
                    self.import_from_ssh_config()
                elif selected == "Import from Git Aliases":
                    self.import_from_git_aliases()
                elif selected == "View SSH Config":
                    self.view_ssh_config()
                elif selected == "Refresh":
                    pass  # Just redraw
                elif selected == "Quit":
                    if self.confirm("Are you sure you want to quit?"):
                        break


def run_cli() -> None:
    """Run the CLI interface."""
    curses.wrapper(lambda stdscr: CursesUI(stdscr).run())
