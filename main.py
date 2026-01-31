import sys

from gps.tray import run_tray
from gps.gtk_gui import run_app as run_gui

USAGE = """\
Usage: git-profile-switcher [OPTION]

Manage Git profiles from the system tray or a GTK3 window.

Options:
  -g, --gui     Launch the GTK3 management window
  -t, --tray    Launch the system tray icon (default)
  -h, --help    Show this help message and exit
"""


def main() -> None:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(USAGE, end="")
        sys.exit(0)
    elif "--gui" in sys.argv or "-g" in sys.argv:
        run_gui()
    else:
        run_tray()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise
