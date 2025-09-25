import sys

from gps.gui import run_app


def main() -> None:
    run_app()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise
