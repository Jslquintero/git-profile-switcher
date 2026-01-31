import sys

from gps.cli import run_cli
from gps.tray import run_tray
from gps.gtk_gui import run_app as run_gui


def main() -> None:
    if "--tray" in sys.argv or "-t" in sys.argv:
        run_tray()
    elif "--gui" in sys.argv or "-g" in sys.argv:
        run_gui()
    else:
        run_cli()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise
