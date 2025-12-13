import sys

from gps.cli import run_cli


def main() -> None:
    run_cli()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise
