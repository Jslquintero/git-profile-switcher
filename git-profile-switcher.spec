Name:           git-profile-switcher
Version:        1.1.1
Release:        1%{?dist}
Summary:        Manage multiple Git profiles from the system tray

License:        MIT
URL:            https://github.com/jslquintero/git-profile-switcher
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

Requires:       python3
Requires:       python3-gobject
Requires:       libappindicator-gtk3
Requires:       git
Requires:       openssh

%description
A GTK3 application to manage multiple Git profiles on Linux.
Create profiles with name, email, and SSH keys, then switch between
them with a click from the system tray or the GTK3 management window.

%prep
%setup -q

%install
# Application files
install -d %{buildroot}%{_datadir}/%{name}
install -m 644 main.py %{buildroot}%{_datadir}/%{name}/main.py
cp -a gps %{buildroot}%{_datadir}/%{name}/gps

# Wrapper script
install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/%{name} << 'WRAPPER'
#!/bin/bash
exec python3 %{_datadir}/git-profile-switcher/main.py "$@"
WRAPPER
chmod 755 %{buildroot}%{_bindir}/%{name}

# Desktop entry
install -d %{buildroot}%{_datadir}/applications
install -m 644 git-profile-switcher.desktop %{buildroot}%{_datadir}/applications/%{name}.desktop

# Icon
install -d %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
install -m 644 icons/git-profile-switcher.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{name}.svg

%files
%{_bindir}/%{name}
%{_datadir}/%{name}/
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{name}.svg

%post
touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
update-desktop-database %{_datadir}/applications &>/dev/null || :

%postun
if [ $1 -eq 0 ]; then
    touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
    gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi
update-desktop-database %{_datadir}/applications &>/dev/null || :

%changelog
* Sat Jan 31 2026 Jose Lopez <jose@localhost> - 1.1.1-1
- Fix "Manage Profiles" not opening GUI from system tray

* Sat Jan 31 2026 Jose Lopez <jose@localhost> - 1.1.0-1
- Theme-aware styling (dark/light mode support)
- Floating toast notifications
- Form validation and keyboard accessibility improvements
- About dialog

* Fri Jan 30 2026 Jose Lopez <jose@localhost> - 1.0.0-1
- Initial RPM release
- GTK3 GUI and system tray application
- Removed legacy console and Tkinter interfaces
