import sys

from agent.commands import run_cli


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    sys.exit(main())
