#!/usr/bin/env python3
"""
Git Profile Switcher - Professional System Tray Application

A clean, responsive system tray application for managing Git profiles.
"""

import gi
import os
import signal
import subprocess
import sys
from typing import Optional, List

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")

from gi.repository import Gtk, AppIndicator3, GLib, Gdk, Gio

from .manager import ProfileManager, Profile
from .storage import PROFILES_PATH

APP_ID = "com.github.git-profile-switcher"
# Use standard GTK icon that's always available
DEFAULT_ICON = "emblem-generic"
ACTIVE_ICON = "user-available"

# Check git config less frequently (we handle our own switches)
GIT_CONFIG_CHECK_INTERVAL = 10


class ProfileMenuItem(Gtk.MenuItem):
    """A custom menu item for profiles with icon and styling."""

    def __init__(self, profile: Profile, is_active: bool = False):
        label = f"{profile.name}"
        if is_active:
            label = f"✓ {label}"

        super().__init__(label)

        self.profile_id = profile.id
        self.is_active = is_active

        # Style based on state
        if is_active:
            self.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)


class TrayIcon:
    """
    Professional system tray icon for Git Profile Switcher.

    Features:
    - Clean icon using GTK theme
    - Organized menu with sections
    - Visual indicators for active profile
    - Non-blocking operations
    - Desktop notifications
    """

    def __init__(self):
        self.manager = ProfileManager()
        self.indicator: Optional[AppIndicator3.Indicator] = None
        self._notification = None
        self._last_active_id: Optional[str] = None
        self._file_monitor = None
        self._setup_indicator()
        self._setup_signals()
        self._setup_css()
        self._setup_file_monitor()
        self._start_git_config_check()

    def _setup_css(self):
        """Apply custom CSS styling for a polished look."""
        css = b"""
        menuitem {
            padding: 4px 8px;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _setup_indicator(self):
        """Initialize the AppIndicator with professional defaults."""
        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            DEFAULT_ICON,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )

        # Set ordering hints for proper positioning
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_attention_icon("user-available")

        # Set initial label (empty for cleaner look)
        self.indicator.set_label("", "")

        # Build and set the menu
        self._build_menu()
        self._update_display()

    def _setup_signals(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGHUP, self._on_signal)

    def _on_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        GLib.idle_add(Gtk.main_quit)

    def _start_git_config_check(self):
        """Start lightweight periodic check for git config changes only."""
        self._last_active_id = self.manager.get_active_profile_id()
        GLib.timeout_add_seconds(GIT_CONFIG_CHECK_INTERVAL, self._check_git_config)

    def _setup_file_monitor(self):
        """Setup inotify-based file monitoring for profiles.json."""
        try:
            # Ensure config directory exists
            config_dir = os.path.dirname(PROFILES_PATH)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            # Create a file monitor for the profiles.json
            # If file doesn't exist yet, monitor the directory
            target_path = PROFILES_PATH if os.path.exists(PROFILES_PATH) else config_dir

            f = Gio.File.new_for_path(target_path)
            self._file_monitor = f.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self._file_monitor.connect("changed", self._on_file_changed)
        except Exception as e:
            # Fall back to polling if inotify fails
            print(f"File monitoring not available: {e}, falling back to polling")
            GLib.timeout_add_seconds(2, self._poll_profiles)

    def _on_file_changed(self, monitor, file, other_file, event_type):
        """Handle file system change events via inotify."""
        # Only care about changes that affect content
        if event_type in (Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CREATED,
                          Gio.FileMonitorEvent.DELETED):
            # Debounce slightly to avoid multiple rapid updates
            GLib.timeout_add(100, self._update_all)

    def _check_git_config(self) -> bool:
        """
        Periodically check if git config changed (e.g., via terminal).
        Much less frequent than file monitoring since we handle our own switches.
        Returns True to keep timer running.
        """
        current_active_id = self.manager.get_active_profile_id()
        if current_active_id != self._last_active_id:
            self._last_active_id = current_active_id
            self._update_all()
        return True

    def _poll_profiles(self) -> bool:
        """Fallback polling method if inotify isn't available."""
        self._update_all()
        return True

    def _update_all(self):
        """Update all UI elements."""
        self._update_profiles_menu()
        self._update_display()

    def _get_active_profile(self) -> Optional[Profile]:
        """Get the currently active profile."""
        active_id = self.manager.get_active_profile_id()
        if active_id:
            return self.manager.get_profile(active_id)
        return None

    def _update_display(self):
        """Update icon and label based on current state."""
        active = self._get_active_profile()

        if active:
            # Show active profile with subtle label
            alias = active.alias[:15] + "…" if len(active.alias) > 15 else active.alias
            self.indicator.set_label(f"  {alias}", "Git")
            self.indicator.set_icon(ACTIVE_ICON)
        else:
            self.indicator.set_label("", "Git")
            self.indicator.set_icon(DEFAULT_ICON)

    def _build_menu(self) -> Gtk.Menu:
        """Build the main context menu with organized sections."""
        menu = Gtk.Menu()

        # === Header Section: Current Status ===
        self._status_item = Gtk.MenuItem.new_with_label("Git Profile: None")
        self._status_item.set_sensitive(False)
        menu.append(self._status_item)

        menu.append(Gtk.SeparatorMenuItem())

        # === Profiles Section ===
        profiles_item = Gtk.MenuItem.new_with_label("Switch Profile")
        self._profiles_menu = Gtk.Menu()
        profiles_item.set_submenu(self._profiles_menu)
        menu.append(profiles_item)

        # === Actions Section ===
        menu.append(Gtk.SeparatorMenuItem())

        # Refresh
        refresh_item = self._create_menu_item("Refresh", "view-refresh")
        refresh_item.connect("activate", self._on_refresh)
        menu.append(refresh_item)

        # === Import Section ===
        import_item = Gtk.MenuItem.new_with_label("Import")
        import_menu = Gtk.Menu()
        import_item.set_submenu(import_menu)
        menu.append(import_item)

        # Import from SSH Config
        import_ssh_item = self._create_menu_item("Import from SSH Config…", "document-open")
        import_ssh_item.connect("activate", self._on_import_ssh)
        import_menu.append(import_ssh_item)

        # Import Git Aliases
        import_aliases_item = self._create_menu_item("Import Git Aliases…", "document-open")
        import_aliases_item.connect("activate", self._on_import_aliases)
        import_menu.append(import_aliases_item)

        # === Manage Section ===
        menu.append(Gtk.SeparatorMenuItem())

        # Manage Profiles
        manage_item = self._create_menu_item("Manage Profiles…", "document-properties")
        manage_item.connect("activate", self._on_manage_profiles)
        menu.append(manage_item)

        # === Footer Section ===
        menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = self._create_menu_item("Quit", "application-exit")
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()

        self._main_menu = menu
        self.indicator.set_menu(menu)

        # Populate profiles
        self._update_profiles_menu()

        return menu

    def _create_menu_item(self, label: str, icon_name: str) -> Gtk.ImageMenuItem:
        """Create a menu item with an icon."""
        item = Gtk.ImageMenuItem.new_with_mnemonic(label)

        # Try to load icon from theme
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        item.set_always_show_image(True)
        item.set_image(icon)

        return item

    def _update_profiles_menu(self):
        """Update the profiles submenu with current profiles."""
        # Clear existing items
        for item in self._profiles_menu.get_children():
            self._profiles_menu.remove(item)

        # Reload profiles
        self.manager.reload()
        profiles = self.manager.list_profiles()
        active_id = self.manager.get_active_profile_id()

        # Update status header
        active = self._get_active_profile()
        if active:
            self._status_item.set_label(f"Active: {active.name} <{active.email}>")
        else:
            self._status_item.set_label("Git Profile: None")

        if not profiles:
            # No profiles message
            no_profiles = Gtk.MenuItem.new_with_label("No profiles configured")
            no_profiles.set_sensitive(False)
            self._profiles_menu.append(no_profiles)

            # Add "Create Profile" option
            create_item = self._create_menu_item("Create Profile…", "list-add")
            create_item.connect("activate", self._on_manage_profiles)
            self._profiles_menu.append(create_item)
        else:
            # Group profiles: active first, then others
            active_profiles = [p for p in profiles if p.id == active_id]
            inactive_profiles = [p for p in profiles if p.id != active_id]

            # Active profile section
            if active_profiles:
                active_profile = active_profiles[0]
                item = Gtk.MenuItem.new_with_label(f"● {active_profile.name} ({active_profile.alias})")
                item.set_sensitive(False)
                self._profiles_menu.append(item)
                self._profiles_menu.append(Gtk.SeparatorMenuItem())

            # Inactive profiles
            for profile in inactive_profiles:
                item = Gtk.MenuItem.new_with_label(f"  {profile.name} ({profile.alias})")
                item.connect("activate", self._on_switch_profile, profile.id)
                self._profiles_menu.append(item)

        self._profiles_menu.show_all()

    def _on_refresh(self, _widget):
        """Handle refresh - non-blocking."""
        self._update_profiles_menu()
        self._update_display()

    def _on_switch_profile(self, _widget, profile_id: str):
        """
        Handle profile switching - runs async to keep UI responsive.
        """
        def do_switch():
            profile = self.manager.get_profile(profile_id)
            if not profile:
                GLib.idle_add(lambda: self._show_notification(
                    "Error", "Profile not found", error=True
                ))
                return

            ok, msg = self.manager.set_active(profile_id)

            def update_ui():
                # Update our tracked state immediately since we made the change
                self._last_active_id = profile_id
                self._update_all()
                if ok:
                    self._show_notification(
                        f"Git Profile: {profile.name}",
                        f"Now using {profile.email} for git operations"
                    )
                else:
                    self._show_notification("Failed to switch profile", msg, error=True)

            GLib.idle_add(update_ui)

        # Run in thread to avoid blocking
        from threading import Thread
        Thread(target=do_switch, daemon=True).start()

    def _on_manage_profiles(self, _widget):
        """Open the profile management GUI in a separate process."""
        try:
            # Use subprocess to avoid blocking the tray icon
            # Run GUI via -c flag to import and execute
            subprocess.Popen(
                [sys.executable, "-c", "from gps.gtk_gui import run_app; run_app()"],
                start_new_session=True,
            )
        except Exception as e:
            self._show_notification("Error", f"Failed to open GUI: {e}", error=True)

    def _on_import_ssh(self, _widget):
        """Import profiles from SSH config."""
        imported = self.manager.import_from_ssh_config()
        if imported:
            self._update_all()
            self._show_notification("Import Successful", f"Imported {imported} profile(s) from SSH config")
        else:
            self._show_notification("Import", "No profiles found to import", error=True)

    def _on_import_aliases(self, _widget):
        """Import profiles from git aliases."""
        imported = self.manager.import_from_git_aliases()
        if imported:
            self._update_all()
            self._show_notification("Import Successful", f"Imported {imported} profile(s) from git aliases")
        else:
            self._show_notification("Import", "No matching aliases found", error=True)

    def _on_quit(self, _widget):
        """Handle quit - clean shutdown."""
        Gtk.main_quit()

    def _show_notification(self, title: str, message: str, error: bool = False):
        """Show a desktop notification."""
        try:
            gi.require_version("Notify", "0.7")
            from gi.repository import Notify

            if not Notify.is_initted():
                Notify.init(APP_ID)

            if self._notification:
                self._notification.close()

            icon_name = "dialog-error" if error else "user-available"
            self._notification = Notify.Notification.new(title, message, icon_name)
            self._notification.set_urgency(2 if error else 1)  # Low urgency, normal for error
            self._notification.show()
        except Exception:
            # Notifications are optional - fail silently
            pass

    def run(self):
        """Start the GTK main loop."""
        Gtk.main()


def run_tray() -> None:
    """Entry point for running the tray application."""
    # Initialize app
    app = TrayIcon()
    app.run()
