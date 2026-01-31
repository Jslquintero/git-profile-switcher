#!/usr/bin/env python3
"""
Git Profile Switcher - Native GNOME GUI

A GTK3 application following GNOME HIG for managing Git profiles.
"""

import gi
import os
import shutil
import subprocess
from typing import Optional, List

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gtk, Gdk, GLib, Gio, Pango

from .manager import ProfileManager, Profile
from .storage import PROFILES_PATH, SSH_DIR


APP_ID = "com.github.git-profile-switcher"


class ProfileRow(Gtk.ListBoxRow):
    """A list box row representing a Git profile."""

    def __init__(self, profile: Profile, is_active: bool = False):
        super().__init__(activatable=True, selectable=True)

        self.profile = profile
        self.is_active = is_active

        # Main container
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=12, margin_end=12, margin_top=8, margin_bottom=8)
        self.add(box)

        # Top row: name and active indicator
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.pack_start(top_box, False, False, 0)

        # Name with bold styling
        name_label = Gtk.Label(label=profile.name)
        name_label.set_halign(Gtk.Align.START)
        if not is_active:
            name_label.get_style_context().add_class("dim-label")

        if is_active:
            attrs = Pango.AttrList()
            attrs.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
            name_label.set_attributes(attrs)

        top_box.pack_start(name_label, False, False, 0)

        # Active indicator
        if is_active:
            active_dot = Gtk.Label()
            active_dot.set_markup("<span foreground='#2eb390'>\u25cf</span> <span size='small'>Active</span>")
            top_box.pack_end(active_dot, False, False, 0)

        # Email
        email_label = Gtk.Label(label=profile.email)
        email_label.set_halign(Gtk.Align.START)
        email_label.get_style_context().add_class(Gtk.STYLE_CLASS_DIM_LABEL)
        email_label.set_ellipsize(Pango.EllipsizeMode.END)
        box.pack_start(email_label, False, False, 0)

        # Details row: host, alias, and key status
        details_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        box.pack_start(details_box, False, False, 0)

        # Host
        host_label = Gtk.Label()
        host_label.set_markup(f"<span size='small' foreground='#555'>Host:</span> <span size='small'>{GLib.markup_escape_text(profile.host)}</span>")
        host_label.set_halign(Gtk.Align.START)
        details_box.pack_start(host_label, False, False, 0)

        # Alias
        alias_label = Gtk.Label()
        alias_label.set_markup(f"<span size='small' foreground='#555'>Alias:</span> <span size='small' font_family='monospace'>{GLib.markup_escape_text(profile.alias)}</span>")
        alias_label.set_halign(Gtk.Align.START)
        details_box.pack_start(alias_label, False, False, 0)

        # SSH Key status
        has_key = os.path.exists(profile.ssh_key_path)
        key_status = Gtk.Label()
        if has_key:
            key_status.set_markup("<span size='small' foreground='#2eb390'>\u26bf Key</span>")
        else:
            key_status.set_markup("<span size='small' foreground='#cc5555'>\u26bf No key</span>")
        key_status.set_halign(Gtk.Align.START)
        details_box.pack_start(key_status, False, False, 0)

        self.show_all()


class ProfileDialog(Gtk.Dialog):
    """Dialog for adding/editing a profile."""

    def __init__(self, parent, profile: Optional[Profile] = None, suggested_name: str = "", suggested_alias: str = ""):
        title = "Edit Profile" if profile else "Add Profile"
        super().__init__(
            title=title,
            transient_for=parent,
            modal=True,
            use_header_bar=1,
        )

        self.profile = profile
        self.result = None

        # Setup dialog
        self.set_default_size(500, 200)
        self.set_border_width(0)

        # Header bar buttons
        header_bar = self.get_header_bar()
        if header_bar is not None:
            header_bar.set_show_close_button(False)

            save_btn = Gtk.Button(label="Save")
            save_btn.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
            save_btn.connect("clicked", self._on_save)
            header_bar.pack_end(save_btn)

            cancel_btn = Gtk.Button(label="Cancel")
            cancel_btn.connect("clicked", lambda _: self.destroy())
            header_bar.pack_start(cancel_btn)

            header_bar.show_all()
        else:
            # Fallback: use standard dialog buttons
            self.add_button("Cancel", Gtk.ResponseType.CANCEL)
            save_btn = self.add_button("Save", Gtk.ResponseType.OK)
            save_btn.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
            self.connect("response", self._on_dialog_response)

        # Content area
        content = self.get_content_area()
        content.set_property("margin", 24)
        content.set_spacing(12)

        # Form grid
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(12)
        content.add(grid)

        row = 0

        # Name field
        name_label = Gtk.Label(label="Name")
        name_label.set_halign(Gtk.Align.START)
        name_label.get_style_context().add_class(Gtk.STYLE_CLASS_DIM_LABEL)
        grid.attach(name_label, 0, row, 1, 1)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_hexpand(True)
        if profile:
            self.name_entry.set_text(profile.name)
        elif suggested_name:
            self.name_entry.set_text(suggested_name)
        grid.attach(self.name_entry, 1, row, 1, 1)
        row += 1

        # Email field
        email_label = Gtk.Label(label="Email")
        email_label.set_halign(Gtk.Align.START)
        email_label.get_style_context().add_class(Gtk.STYLE_CLASS_DIM_LABEL)
        grid.attach(email_label, 0, row, 1, 1)

        self.email_entry = Gtk.Entry()
        self.email_entry.set_hexpand(True)
        if profile:
            self.email_entry.set_text(profile.email)
        grid.attach(self.email_entry, 1, row, 1, 1)
        row += 1

        # Host field
        host_label = Gtk.Label(label="Host")
        host_label.set_halign(Gtk.Align.START)
        host_label.get_style_context().add_class(Gtk.STYLE_CLASS_DIM_LABEL)
        grid.attach(host_label, 0, row, 1, 1)

        self.host_entry = Gtk.Entry()
        self.host_entry.set_hexpand(True)
        self.host_entry.set_placeholder_text("github.com")
        if profile:
            self.host_entry.set_text(profile.host)
        else:
            self.host_entry.set_text("github.com")
        grid.attach(self.host_entry, 1, row, 1, 1)
        row += 1

        # Alias field
        alias_label = Gtk.Label(label="SSH Alias")
        alias_label.set_halign(Gtk.Align.START)
        alias_label.get_style_context().add_class(Gtk.STYLE_CLASS_DIM_LABEL)
        grid.attach(alias_label, 0, row, 1, 1)

        self.alias_entry = Gtk.Entry()
        self.alias_entry.set_hexpand(True)
        self.alias_entry.set_placeholder_text("Auto-generated from name")
        if profile:
            self.alias_entry.set_text(profile.alias)
        elif suggested_alias:
            self.alias_entry.set_text(suggested_alias)
        grid.attach(self.alias_entry, 1, row, 1, 1)
        row += 1

        content.show_all()

    def _on_save(self, button):
        name = self.name_entry.get_text().strip()
        email = self.email_entry.get_text().strip()
        host = self.host_entry.get_text().strip() or "github.com"
        alias = self.alias_entry.get_text().strip() or None

        if not name or not email:
            dialog = Gtk.MessageDialog(
                parent=self,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Validation Error",
            )
            dialog.format_secondary_text("Name and Email are required fields.")
            dialog.run()
            dialog.destroy()
            return

        self.result = {
            "name": name,
            "email": email,
            "host": host,
            "alias": alias,
        }
        self.destroy()

    def _on_dialog_response(self, dialog, response_id):
        """Fallback handler when header bar is not available."""
        if response_id == Gtk.ResponseType.OK:
            self._on_save(None)
        else:
            self.destroy()


class MainWindow(Gtk.ApplicationWindow):
    """Main application window."""

    def __init__(self, app):
        super().__init__(application=app, title="Git Profile Switcher")

        self.manager = ProfileManager()
        self._setup_ui()
        self._setup_keyboard_shortcuts()
        self._load_profiles()

    def _setup_ui(self):
        """Setup the user interface."""
        self.set_default_size(800, 500)
        self.set_border_width(0)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Header bar
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        header_bar.set_title("Git Profile Switcher")
        header_bar.set_subtitle("Manage your Git identities")

        # Left side: Add button
        add_btn = Gtk.Button(label="Add")
        add_btn.set_tooltip_text("Add new profile (Ctrl+N)")
        add_btn.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
        add_btn.connect("clicked", self._on_add)
        header_bar.pack_start(add_btn)

        # Right side: Hamburger menu
        menu_btn = Gtk.MenuButton()
        menu_icon = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
        menu_btn.add(menu_icon)
        menu_btn.set_tooltip_text("Menu")

        # Build hamburger menu
        hamburger_menu = Gio.Menu()
        hamburger_menu.append("Import from SSH Config", "win.import-ssh-config")
        hamburger_menu.append("Import from Git Aliases", "win.import-git-aliases")

        menu_btn.set_menu_model(hamburger_menu)
        header_bar.pack_end(menu_btn)

        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_tooltip_text("Refresh (Ctrl+R)")
        refresh_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh_btn.add(refresh_icon)
        refresh_btn.connect("clicked", self._on_refresh)
        header_bar.pack_end(refresh_btn)

        self.set_titlebar(header_bar)

        # Actions
        self._setup_actions()

        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # Status bar
        self.status_revealer = Gtk.Revealer()
        self.status_revealer.set_property("margin-start", 12)
        self.status_revealer.set_property("margin-end", 12)
        self.status_revealer.set_property("margin-top", 6)
        self.status_revealer.set_property("margin-bottom", 6)

        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_bar.get_style_context().add_class("app-notification")
        status_bar.set_property("margin", 0)

        self.status_label = Gtk.Label()
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.status_label.set_halign(Gtk.Align.START)
        status_bar.pack_start(self.status_label, True, True, 0)

        close_status = Gtk.Button()
        close_status.add(Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU))
        close_status.get_style_context().add_class("flat")
        close_status.connect("clicked", lambda _: self.status_revealer.set_reveal_child(False))
        status_bar.pack_end(close_status, False, False, 0)

        self.status_revealer.add(status_bar)
        main_box.pack_start(self.status_revealer, False, False, 0)

        # Scrolled window for list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_property("margin", 12)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.get_style_context().add_class("frame")
        main_box.pack_start(scrolled, True, True, 0)

        # Profile list
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_header_func(self._list_header_func)
        self.list_box.connect("row-activated", self._on_row_activated)
        self.list_box.connect("button-press-event", self._on_button_press)
        scrolled.add(self.list_box)

        # Help text at bottom
        help_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        help_bar.get_style_context().add_class(Gtk.STYLE_CLASS_BACKGROUND)
        help_bar.set_property("margin-start", 12)
        help_bar.set_property("margin-end", 12)
        help_bar.set_property("margin-top", 6)
        help_bar.set_property("margin-bottom", 6)

        help_label = Gtk.Label()
        help_label.set_markup(
            "<span size='small' foreground='#777'>"
            "Double-click to edit \u2022 Right-click for actions \u2022 "
            "Ctrl+N to add \u2022 Delete to remove"
            "</span>"
        )
        help_label.set_halign(Gtk.Align.START)
        help_bar.pack_start(help_label, True, True, 0)

        main_box.pack_start(help_bar, False, False, 0)

        self.show_all()
        self.status_revealer.set_reveal_child(False)

    def _setup_actions(self):
        """Setup window actions."""
        # Refresh action
        refresh_action = Gio.SimpleAction.new("refresh", None)
        refresh_action.connect("activate", self._on_refresh)
        self.add_action(refresh_action)

        # Import from SSH config
        import_ssh_action = Gio.SimpleAction.new("import-ssh-config", None)
        import_ssh_action.connect("activate", self._on_import_ssh_config)
        self.add_action(import_ssh_action)

        # Import from git aliases
        import_git_action = Gio.SimpleAction.new("import-git-aliases", None)
        import_git_action.connect("activate", self._on_import_git_aliases)
        self.add_action(import_git_action)

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts."""
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        # Ctrl+N - Add profile
        key, mod = Gtk.accelerator_parse("<Control>n")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self._on_add(None))

        # Ctrl+R - Refresh
        key, mod = Gtk.accelerator_parse("<Control>r")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self._on_refresh())

        # F5 - Refresh
        key, mod = Gtk.accelerator_parse("F5")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self._on_refresh())

        # Delete - Delete selected profile
        key, mod = Gtk.accelerator_parse("Delete")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self._on_delete_selected())

    def _list_header_func(self, row, before):
        """Add headers between list items."""
        if before and not row.get_header():
            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            row.set_header(separator)

    def _load_profiles(self):
        """Load and display all profiles."""
        # Clear existing
        for child in self.list_box.get_children():
            self.list_box.remove(child)

        self.manager.reload()
        profiles = self.manager.list_profiles()
        active_id = self.manager.get_active_profile_id()

        if not profiles:
            # Empty state
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=48)
            empty_box.set_halign(Gtk.Align.CENTER)
            empty_box.set_valign(Gtk.Align.CENTER)

            empty_icon = Gtk.Image()
            empty_icon.set_from_icon_name("avatar-default-symbolic", Gtk.IconSize.DIALOG)
            empty_icon.get_style_context().add_class(Gtk.STYLE_CLASS_DIM_LABEL)
            empty_icon.set_pixel_size(64)
            empty_box.pack_start(empty_icon, False, False, 0)

            empty_label = Gtk.Label()
            empty_label.set_markup("<span size='large'>No profiles yet</span>")
            empty_label.get_style_context().add_class(Gtk.STYLE_CLASS_DIM_LABEL)
            empty_box.pack_start(empty_label, False, False, 0)

            empty_hint = Gtk.Label(label="Click 'Add' to create your first Git profile")
            empty_hint.get_style_context().add_class(Gtk.STYLE_CLASS_DIM_LABEL)
            empty_box.pack_start(empty_hint, False, False, 0)

            empty_box.show_all()
            self.list_box.add(empty_box)
        else:
            for profile in profiles:
                is_active = (profile.id == active_id)
                row = ProfileRow(profile, is_active)
                self.list_box.add(row)

        self.list_box.show_all()

    def _get_selected_profile(self) -> Optional[Profile]:
        """Get the currently selected profile."""
        row = self.list_box.get_selected_row()
        if row and isinstance(row, ProfileRow):
            return row.profile
        return None

    def _show_status(self, message, error=False):
        """Show status message."""
        if error:
            self.status_label.get_style_context().add_class("error")
        else:
            self.status_label.get_style_context().remove_class("error")
        self.status_label.set_text(message)
        self.status_revealer.set_reveal_child(True)

        # Auto-hide after 5 seconds
        GLib.timeout_add_seconds(5, lambda: self.status_revealer.set_reveal_child(False))

    # ── Context menu ──────────────────────────────────────────────────

    def _on_button_press(self, widget, event):
        """Handle right-click on the list box to show context menu."""
        if event.button != 3:  # Right-click only
            return False

        # Find which row was clicked
        row = self.list_box.get_row_at_y(int(event.y))
        if not row or not isinstance(row, ProfileRow):
            return False

        self.list_box.select_row(row)
        profile = row.profile
        has_key = os.path.exists(profile.ssh_key_path)

        menu = Gtk.Menu()

        # Set Active
        item_active = Gtk.MenuItem(label="Set Active")
        item_active.connect("activate", lambda _: self._on_set_active(profile))
        menu.append(item_active)

        # Edit
        item_edit = Gtk.MenuItem(label="Edit")
        item_edit.connect("activate", lambda _: self._on_edit(profile))
        menu.append(item_edit)

        # Delete
        item_delete = Gtk.MenuItem(label="Delete")
        item_delete.connect("activate", lambda _: self._on_delete(profile))
        menu.append(item_delete)

        menu.append(Gtk.SeparatorMenuItem())

        # Generate SSH Key
        item_gen = Gtk.MenuItem(label="Generate SSH Key")
        item_gen.connect("activate", lambda _: self._on_generate_key(profile))
        item_gen.set_sensitive(not has_key)
        menu.append(item_gen)

        # Copy Public Key
        item_copy = Gtk.MenuItem(label="Copy Public Key")
        item_copy.connect("activate", lambda _: self._on_copy_public_key(profile))
        item_copy.set_sensitive(has_key and os.path.exists(profile.public_key_path))
        menu.append(item_copy)

        # Import SSH Key
        item_import = Gtk.MenuItem(label="Import SSH Key\u2026")
        item_import.connect("activate", lambda _: self._on_import_key(profile))
        item_import.set_sensitive(not has_key)
        menu.append(item_import)

        # Export SSH Key
        item_export = Gtk.MenuItem(label="Export SSH Key\u2026")
        item_export.connect("activate", lambda _: self._on_export_key(profile))
        item_export.set_sensitive(has_key)
        menu.append(item_export)

        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    # ── Profile actions ───────────────────────────────────────────────

    def _on_add(self, button):
        """Handle add button click."""
        dialog = ProfileDialog(self)
        dialog.run()

        if dialog.result:
            profile = self.manager.add_profile(**dialog.result)
            ok, msg = self.manager.generate_ssh_key(profile.id)
            self._load_profiles()
            if ok:
                self._show_status(f"Profile '{profile.name}' created with SSH key")
            else:
                self._show_status(f"Profile created but key generation failed: {msg}", error=True)
        dialog.destroy()

    def _on_edit(self, profile: Profile):
        """Handle edit - triggered by double-click or Enter."""
        dialog = ProfileDialog(self, profile)
        dialog.run()

        if dialog.result:
            updated = self.manager.update_profile(profile.id, **dialog.result)
            if updated:
                self._load_profiles()
                self._show_status(f"Profile '{updated.name}' updated")
        dialog.destroy()

    def _on_row_activated(self, list_box, row):
        """Handle row double-click/enter - opens edit dialog."""
        if isinstance(row, ProfileRow):
            self._on_edit(row.profile)

    def _on_set_active(self, profile: Profile):
        """Set a profile as the active Git profile."""
        ok, msg = self.manager.set_active(profile.id)
        self._load_profiles()
        if ok:
            self._show_status(f"'{profile.name}' is now the active profile")
        else:
            self._show_status(f"Failed to activate: {msg}", error=True)

    def _on_delete(self, profile: Profile):
        """Delete a profile with confirmation."""
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=f"Delete '{profile.name}'?",
        )
        dialog.format_secondary_text(
            "This will remove the profile and delete its SSH keys. This cannot be undone."
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        delete_btn = dialog.add_button("Delete", Gtk.ResponseType.OK)
        delete_btn.get_style_context().add_class(Gtk.STYLE_CLASS_DESTRUCTIVE_ACTION)

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            ok = self.manager.delete_profile(profile.id, remove_keys=True)
            self._load_profiles()
            if ok:
                self._show_status(f"Profile '{profile.name}' deleted")
            else:
                self._show_status("Failed to delete profile", error=True)

    def _on_delete_selected(self):
        """Delete the currently selected profile (keyboard shortcut)."""
        profile = self._get_selected_profile()
        if profile:
            self._on_delete(profile)

    # ── SSH key actions ───────────────────────────────────────────────

    def _on_generate_key(self, profile: Profile):
        """Generate an SSH key for a profile."""
        ok, msg = self.manager.generate_ssh_key(profile.id)
        self._load_profiles()
        if ok:
            self._show_status(f"SSH key generated for '{profile.name}'")
        else:
            self._show_status(f"Key generation failed: {msg}", error=True)

    def _on_copy_public_key(self, profile: Profile):
        """Copy the public SSH key to the clipboard."""
        try:
            with open(profile.public_key_path, "r", encoding="utf-8") as fh:
                pub_key = fh.read().strip()
        except FileNotFoundError:
            self._show_status("Public key file not found", error=True)
            return

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(pub_key, -1)
        clipboard.store()
        self._show_status(f"Public key for '{profile.name}' copied to clipboard")

    def _on_import_key(self, profile: Profile):
        """Import an existing SSH key for a profile."""
        chooser = Gtk.FileChooserDialog(
            title="Select SSH Private Key",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
        chooser.add_button("Import", Gtk.ResponseType.OK)
        chooser.set_current_folder(os.path.expanduser("~/.ssh"))

        # File filter for SSH keys
        key_filter = Gtk.FileFilter()
        key_filter.set_name("SSH Keys")
        key_filter.add_pattern("id_*")
        key_filter.add_pattern("*.pem")
        chooser.add_filter(key_filter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name("All Files")
        all_filter.add_pattern("*")
        chooser.add_filter(all_filter)

        response = chooser.run()
        file_path = chooser.get_filename()
        chooser.destroy()

        if response != Gtk.ResponseType.OK or not file_path:
            return

        # Validate it looks like a private key
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read(100)
            if "PRIVATE KEY" not in content:
                confirm = Gtk.MessageDialog(
                    parent=self,
                    flags=Gtk.DialogFlags.MODAL,
                    message_type=Gtk.MessageType.QUESTION,
                    buttons=Gtk.ButtonsType.YES_NO,
                    text="This doesn't look like a private key file.",
                )
                confirm.format_secondary_text("Continue anyway?")
                resp = confirm.run()
                confirm.destroy()
                if resp != Gtk.ResponseType.YES:
                    return
        except Exception:
            self._show_status("Cannot read selected file", error=True)
            return

        # Copy key to ~/.ssh with profile naming
        target_path = profile.ssh_key_path
        target_pub = profile.public_key_path
        try:
            shutil.copy2(file_path, target_path)
            os.chmod(target_path, 0o600)

            # Try to copy or derive public key
            source_pub = file_path + ".pub"
            if os.path.exists(source_pub):
                shutil.copy2(source_pub, target_pub)
                os.chmod(target_pub, 0o644)
            else:
                try:
                    with open(target_pub, "w") as pub_fh:
                        subprocess.run(
                            ["ssh-keygen", "-y", "-f", target_path],
                            check=True, stdout=pub_fh,
                        )
                    os.chmod(target_pub, 0o644)
                except Exception:
                    pass  # Public key derivation is best-effort

            # Write SSH config block
            self.manager._write_ssh_config_block(profile)
            self._load_profiles()
            self._show_status(f"SSH key imported for '{profile.name}'")
        except Exception as e:
            self._show_status(f"Import failed: {e}", error=True)

    def _on_export_key(self, profile: Profile):
        """Export an SSH key to a chosen location."""
        if not os.path.exists(profile.ssh_key_path):
            self._show_status("SSH key not found", error=True)
            return

        chooser = Gtk.FileChooserDialog(
            title="Export SSH Private Key",
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
        chooser.add_button("Export", Gtk.ResponseType.OK)
        chooser.set_do_overwrite_confirmation(True)
        chooser.set_current_name(f"id_ed25519_{profile.alias}")

        response = chooser.run()
        file_path = chooser.get_filename()
        chooser.destroy()

        if response != Gtk.ResponseType.OK or not file_path:
            return

        try:
            shutil.copy2(profile.ssh_key_path, file_path)
            os.chmod(file_path, 0o600)
            self._show_status(f"SSH key exported to {os.path.basename(file_path)}")
        except Exception as e:
            self._show_status(f"Export failed: {e}", error=True)

    # ── Import actions (hamburger menu) ───────────────────────────────

    def _on_import_ssh_config(self, action, param):
        """Import profiles from ~/.ssh/config."""
        imported = self.manager.import_from_ssh_config()
        self._load_profiles()
        if imported:
            self._show_status(f"Imported {imported} profile(s) from SSH config")
        else:
            self._show_status("No importable hosts found or all already present")

    def _on_import_git_aliases(self, action, param):
        """Import profiles from git aliases."""
        updated = self.manager.import_from_git_aliases()
        self._load_profiles()
        if updated:
            self._show_status(f"Mapped {updated} profile(s) from git aliases")
        else:
            self._show_status("No matching aliases found")

    # ── Refresh ───────────────────────────────────────────────────────

    def _on_refresh(self, *args):
        """Handle refresh action."""
        self._load_profiles()
        self._show_status("Refreshed")


class Application(Gtk.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        """Handle application activation."""
        win = MainWindow(self)
        win.show_all()
        win.present()


def run_app() -> None:
    """Entry point for running the GTK application."""
    import sys
    # Filter out custom flags that GTK doesn't understand
    gtk_args = [a for a in sys.argv if a not in ("--gui", "-g", "--tray", "-t")]
    app = Application()
    app.run(gtk_args)


if __name__ == "__main__":
    run_app()
