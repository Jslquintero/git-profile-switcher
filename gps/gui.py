import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import Optional
import os
import shutil

from .manager import ProfileManager, Profile


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Git Profile Switcher")
        self.manager = ProfileManager()

        self.active_label_var = tk.StringVar(value="Active: <none>")
        self._build_widgets()
        self._refresh_profiles()

    def _build_widgets(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=10)

        active_label = ttk.Label(top, textvariable=self.active_label_var)
        active_label.pack(side=tk.LEFT)
        refresh_btn = ttk.Button(top, text="Refresh", command=self._refresh_profiles)
        refresh_btn.pack(side=tk.RIGHT)

        self.tree = ttk.Treeview(self.root, columns=("name", "email", "host", "alias", "key"), show="headings", selectmode="browse")
        self.tree.heading("name", text="Git Name")
        self.tree.heading("email", text="Email")
        self.tree.heading("host", text="Host")
        self.tree.heading("alias", text="SSH Alias")
        self.tree.heading("key", text="Key Path")
        self.tree.column("name", width=160)
        self.tree.column("email", width=220)
        self.tree.column("host", width=120)
        self.tree.column("alias", width=160)
        self.tree.column("key", width=280)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        btns = ttk.Frame(self.root)
        btns.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btns, text="Add", command=self._on_add).pack(side=tk.LEFT)
        ttk.Button(btns, text="Edit", command=self._on_edit).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Delete", command=self._on_delete).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Generate Key", command=self._on_generate_key).pack(side=tk.LEFT, padx=(16, 0))
        ttk.Button(btns, text="Import SSH Key", command=self._on_import_key).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Copy Public Key", command=self._on_copy_pub).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Export SSH Key", command=self._on_export_key).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Import from ~/.ssh/config", command=self._on_import).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(btns, text="Import git aliases", command=self._on_import_git_aliases).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(btns, text="Set Active", command=self._on_set_active).pack(side=tk.RIGHT)

    def _refresh_profiles(self) -> None:
        self.manager.reload()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        active_id = self.manager.get_active_profile_id()
        for p in self.manager.list_profiles():
            values = (p.name, p.email, p.host, p.alias, p.ssh_key_path)
            self.tree.insert("", tk.END, iid=p.id, values=values)
        if active_id:
            self.active_label_var.set(f"Active: {self._label_for_id(active_id)}")
        else:
            self.active_label_var.set("Active: <none>")

    def _label_for_id(self, profile_id: str) -> str:
        p = self.manager.get_profile(profile_id)
        if not p:
            return "<unknown>"
        return f"{p.name} ({p.email})"

    def _get_selected(self) -> Optional[Profile]:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.manager.get_profile(sel[0])

    def _on_add(self) -> None:
        self._open_profile_editor()

    def _on_edit(self) -> None:
        profile = self._get_selected()
        if not profile:
            messagebox.showinfo("Edit", "Select a profile to edit")
            return
        self._open_profile_editor(profile)

    def _on_delete(self) -> None:
        profile = self._get_selected()
        if not profile:
            messagebox.showinfo("Delete", "Select a profile to delete")
            return
        if not messagebox.askyesno("Delete", f"Delete profile '{profile.name}' and remove its keys? This cannot be undone."):
            return
        ok = self.manager.delete_profile(profile.id, remove_keys=True)
        if not ok:
            messagebox.showerror("Delete", "Failed to delete profile")
        self._refresh_profiles()

    def _on_import_git_aliases(self) -> None:
        updated = self.manager.import_from_git_aliases()
        if updated:
            messagebox.showinfo("Import", f"Mapped {updated} profile(s) from git aliases")
        else:
            messagebox.showinfo("Import", "No matching aliases found")
        self._refresh_profiles()

    def _on_export_key(self) -> None:
        profile = self._get_selected()
        if not profile:
            messagebox.showinfo("Export SSH Key", "Select a profile first")
            return
        
        if not os.path.exists(profile.ssh_key_path):
            messagebox.showerror("Export SSH Key", "SSH key not found. Generate the key first.")
            return
        
        # Default filename
        default_name = f"id_ed25519_{profile.alias}"
        
        # Ask user where to save
        file_path = filedialog.asksaveasfilename(
            title="Export SSH Private Key",
            defaultextension="",
            initialfile=default_name,
            filetypes=[
                ("SSH Private Key", ""),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Copy the private key
            shutil.copy2(profile.ssh_key_path, file_path)
            # Set secure permissions on exported file
            os.chmod(file_path, 0o600)
            messagebox.showinfo("Export SSH Key", f"SSH private key exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export SSH Key", f"Failed to export key: {e}")

    def _on_import_key(self) -> None:
        # Ask user to select SSH private key file
        file_path = filedialog.askopenfilename(
            title="Import SSH Private Key",
            filetypes=[
                ("SSH Private Key", "id_*"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return  # User cancelled
        
        if not os.path.exists(file_path):
            messagebox.showerror("Import SSH Key", "Selected file does not exist")
            return
        
        # Check if it looks like a private key
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read(100)  # Read first 100 chars
                if "PRIVATE KEY" not in content:
                    if not messagebox.askyesno("Import SSH Key", 
                        "This doesn't look like a private key file. Continue anyway?"):
                        return
        except Exception:
            messagebox.showerror("Import SSH Key", "Cannot read the selected file")
            return
        
        # Extract suggested profile name from filename
        filename = os.path.basename(file_path)
        suggested_name = filename.replace("id_", "").replace("_rsa", "").replace("_ed25519", "").replace("_ecdsa", "")
        if not suggested_name or suggested_name == filename:
            suggested_name = "imported"
        
        # Open profile editor with pre-filled name
        self._open_import_profile_editor(file_path, suggested_name)

    def _open_import_profile_editor(self, key_path: str, suggested_name: str) -> None:
        win = tk.Toplevel(self.root)
        win.title("Import SSH Key - Create Profile")
        win.grab_set()

        name_var = tk.StringVar(value=suggested_name)
        email_var = tk.StringVar(value="")
        host_var = tk.StringVar(value="github.com")
        alias_var = tk.StringVar(value=suggested_name)

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="Git Name").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frm, textvariable=name_var, width=40).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(frm, text="Email").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frm, textvariable=email_var, width=40).grid(row=1, column=1, sticky=tk.W)
        ttk.Label(frm, text="Host").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frm, textvariable=host_var, width=40).grid(row=2, column=1, sticky=tk.W)
        ttk.Label(frm, text="SSH Alias").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frm, textvariable=alias_var, width=40).grid(row=3, column=1, sticky=tk.W)
        
        ttk.Label(frm, text="SSH Key File").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Label(frm, text=key_path, foreground="gray").grid(row=4, column=1, sticky=tk.W)

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))

        def on_import() -> None:
            name = name_var.get().strip()
            email = email_var.get().strip()
            host = host_var.get().strip() or "github.com"
            alias = alias_var.get().strip() or name
            
            if not name:
                messagebox.showerror("Import", "Git Name is required")
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
                if os.path.exists(source_pub_path):
                    shutil.copy2(source_pub_path, target_pub_path)
                    os.chmod(target_pub_path, 0o644)
                else:
                    # Generate public key from private key
                    try:
                        import subprocess
                        subprocess.run([
                            "ssh-keygen", "-y", "-f", target_key_path
                        ], check=True, stdout=open(target_pub_path, 'w'))
                        os.chmod(target_pub_path, 0o644)
                    except Exception:
                        messagebox.showwarning("Import", "Private key imported, but couldn't generate/copy public key")
                
                # Create profile
                profile = self.manager.add_profile(name=name, email=email, host=host, alias=alias)
                # Update the key paths to point to our copied files
                profile.ssh_key_path = target_key_path
                profile.public_key_path = target_pub_path
                self.manager._persist()
                
                messagebox.showinfo("Import", f"SSH key imported successfully as profile '{name}'")
                win.destroy()
                self._refresh_profiles()
                
            except Exception as e:
                messagebox.showerror("Import", f"Failed to import SSH key: {e}")

        ttk.Button(btns, text="Import", command=on_import).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _on_generate_key(self) -> None:
        profile = self._get_selected()
        if not profile:
            messagebox.showinfo("Generate Key", "Select a profile first")
            return
        ok, msg = self.manager.generate_ssh_key(profile.id)
        if ok:
            messagebox.showinfo("Generate Key", msg)
        else:
            messagebox.showerror("Generate Key", msg)
        self._refresh_profiles()

    def _on_copy_pub(self) -> None:
        profile = self._get_selected()
        if not profile:
            messagebox.showinfo("Copy Public Key", "Select a profile first")
            return
        pub_path = profile.public_key_path
        try:
            with open(pub_path, "r", encoding="utf-8") as fh:
                pub = fh.read().strip()
        except FileNotFoundError:
            messagebox.showerror("Copy Public Key", "Public key not found. Generate the key first.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(pub)
        messagebox.showinfo("Copy Public Key", "Public key copied to clipboard")

    def _on_set_active(self) -> None:
        profile = self._get_selected()
        if not profile:
            messagebox.showinfo("Set Active", "Select a profile first")
            return
        ok, msg = self.manager.set_active(profile.id)
        if ok:
            messagebox.showinfo("Set Active", msg)
        else:
            messagebox.showerror("Set Active", msg)
        self._refresh_profiles()

    def _open_profile_editor(self, profile: Optional[Profile] = None) -> None:
        win = tk.Toplevel(self.root)
        win.title("Edit Profile" if profile else "Add Profile")
        win.grab_set()

        name_var = tk.StringVar(value=profile.name if profile else "")
        email_var = tk.StringVar(value=profile.email if profile else "")
        host_var = tk.StringVar(value=profile.host if profile else "github.com")
        alias_var = tk.StringVar(value=profile.alias if profile else "")

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="Git Name").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frm, textvariable=name_var, width=40).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(frm, text="Email").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frm, textvariable=email_var, width=40).grid(row=1, column=1, sticky=tk.W)
        ttk.Label(frm, text="Host").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frm, textvariable=host_var, width=40).grid(row=2, column=1, sticky=tk.W)
        ttk.Label(frm, text="SSH Alias (optional)").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frm, textvariable=alias_var, width=40).grid(row=3, column=1, sticky=tk.W)

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))

        def on_save() -> None:
            name = name_var.get().strip()
            email = email_var.get().strip()
            host = host_var.get().strip() or "github.com"
            alias = alias_var.get().strip() or None
            if not name or not email:
                messagebox.showerror("Save", "Name and Email are required")
                return
            if profile:
                updated = self.manager.update_profile(profile.id, name=name, email=email, host=host, alias=alias)
                if not updated:
                    messagebox.showerror("Save", "Failed to update profile")
                    return
            else:
                created = self.manager.add_profile(name=name, email=email, host=host, alias=alias)
                ok, msg = self.manager.generate_ssh_key(created.id)
                if not ok:
                    messagebox.showwarning("Generate Key", f"Profile saved, but key not generated: {msg}")
            win.destroy()
            self._refresh_profiles()

        ttk.Button(btns, text="Save", command=on_save).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _on_import(self) -> None:
        imported = self.manager.import_from_ssh_config()
        if imported:
            messagebox.showinfo("Import", f"Imported {imported} host(s) from ~/.ssh/config")
        else:
            messagebox.showinfo("Import", "No importable hosts found or all were already present")
        self._refresh_profiles()


def run_app() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


