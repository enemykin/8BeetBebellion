#!/usr/bin/env python3
"""Clone and pin a local touchHLE source tree for reproducible investigation."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "touchhle.json"
DEFAULT_DESTINATION = PROJECT_ROOT / "vendor" / "touchHLE"


class BootstrapError(RuntimeError):
    """Raised when the touchHLE bootstrap operation cannot complete safely."""


def run(command: list[str], *, cwd: Path | None = None) -> str:
    """Run a command and return stripped stdout, raising a useful error on failure."""
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise BootstrapError(f"Required command was not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() or exc.stdout.strip() or "no diagnostic output"
        raise BootstrapError(f"Command failed: {' '.join(command)}\n{details}") from exc
    return completed.stdout.strip()


def load_config(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"Cannot read configuration {path}: {exc}") from exc

    required = ("repository", "branch", "pinned_commit")
    missing = [key for key in required if not isinstance(data.get(key), str) or not data[key]]
    if missing:
        raise BootstrapError(f"Configuration is missing required keys: {', '.join(missing)}")
    return data


def ensure_clean_repository(destination: Path) -> None:
    status = run(["git", "status", "--porcelain"], cwd=destination)
    if status:
        raise BootstrapError(
            f"Refusing to change {destination}: the touchHLE working tree has local changes."
        )


def bootstrap(
    *,
    config_path: Path,
    destination: Path,
    update: bool,
    latest: bool,
) -> str:
    if shutil.which("git") is None:
        raise BootstrapError("Git is required but was not found in PATH.")

    config = load_config(config_path)
    repository = config["repository"]
    branch = config["branch"]
    requested_ref = f"origin/{branch}" if latest else config["pinned_commit"]

    if destination.exists():
        if not (destination / ".git").is_dir():
            raise BootstrapError(
                f"Destination already exists and is not a Git repository: {destination}"
            )
        if not update:
            current = run(["git", "rev-parse", "HEAD"], cwd=destination)
            print(f"touchHLE already exists at {destination}")
            print(f"Current commit: {current}")
            print("Use --update to fetch and checkout the configured revision.")
            return current
        ensure_clean_repository(destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        print(f"Cloning {repository} into {destination} …")
        run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                repository,
                str(destination),
            ]
        )

    print(f"Fetching {branch} …")
    run(["git", "fetch", "origin", branch, "--tags"], cwd=destination)

    if not latest:
        # Fetch the exact object explicitly in case the remote clone is shallow or filtered.
        run(["git", "fetch", "origin", config["pinned_commit"]], cwd=destination)

    print(f"Checking out {requested_ref} in detached HEAD mode …")
    run(["git", "checkout", "--detach", requested_ref], cwd=destination)
    current = run(["git", "rev-parse", "HEAD"], cwd=destination)

    print(f"touchHLE is ready at {destination}")
    print(f"Checked out commit: {current}")
    if latest:
        print("Note: --latest is not reproducible; record this commit in the compatibility log.")
    return current


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Configuration file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=DEFAULT_DESTINATION,
        help=f"Clone destination (default: {DEFAULT_DESTINATION})",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Fetch and move an existing clean checkout to the requested revision.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use the latest remote branch instead of the pinned reproducible commit.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        bootstrap(
            config_path=args.config.resolve(),
            destination=args.destination.resolve(),
            update=args.update,
            latest=args.latest,
        )
    except BootstrapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
