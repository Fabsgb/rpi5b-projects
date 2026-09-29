"""Dependency-light utilities shared by my scripts.

Playwright helpers and colored logging live in separate modules so scripts
can use these basic utilities without importing those optional dependencies.
"""
from __future__ import annotations

from sys import stderr, stdout
from unicodedata import normalize, combining
from datetime import datetime
from os import chmod, environ
from platform import system as platform_system
from getpass import getuser
from subprocess import DEVNULL, run
from tempfile import gettempdir, mkdtemp


def output(msg: object, *, end: str = "\n", flush: bool = False) -> None:
    """Print a message to stdout.

    Use this for a script's actual output/result — the kind another
    script or tool might read or pipe. For diagnostic messages, use
    `log` instead, so they don't pollute stdout.
    """
    print(msg, file=stdout, end=end, flush=flush)


def log(msg: object, *, end: str = "\n", flush: bool = False) -> None:
    """Print a diagnostic/progress message to stderr.

    Writing to stderr instead of stdout keeps this from interfering with
    a script's real output when that output is piped elsewhere.
    """
    print(msg, file=stderr, end=end, flush=flush)


def normalize_text(text: str) -> str:
    """Normalize text for loose, font/accent-insensitive comparison.

    Decomposes styled Unicode characters (e.g. mathematical bold/italic
    letters) and accented letters into their plain base form, strips the
    leftover accent/combining marks, and casefolds the result so
    comparisons are also case-insensitive. Meant for matching text
    scraped from a UI, not for display.
    """
    return "".join(c for c in normalize("NFKD", text) if not combining(c)).casefold()


def now() -> str:
    """Return local time as ISO 8601 with second precision and a UTC offset."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def tmp_path(application: str) -> str:
    """Create and return a unique, private temporary directory for an application."""
    platform = platform_system().casefold()
    prefix = f"{application.replace('/', '_').replace('\\', '_')}_{getuser()}_"
    if platform == "linux":
        path_tmp = mkdtemp(prefix=prefix, dir="/tmp")
        try:
            result = run(
                ["setfacl", "-d", "-m", "u::rwx,g::,o::", path_tmp],
                check=False,
                stdout=DEVNULL,
                stderr=DEVNULL,
            )
        except OSError:
            result = None
        if result is None or result.returncode != 0:
            log("[WARNING] Could not use 'setfacl', using chmod as a fallback.")
            chmod(path_tmp, 0o700)
    elif platform == "windows":
        path_tmp = mkdtemp(prefix=prefix, dir=gettempdir())
        username = environ.get("USERNAME", getuser())
        result = run(
            ["icacls", path_tmp, "/inheritance:r", "/grant:r", f"{username}:(OI)(CI)F"],
            check=False,
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        if result.returncode != 0:
            log("[WARNING] Could not set temporary directory permissions with 'icacls'.")
    else:
        raise NotImplementedError(f"{platform} has not been implemented yet!")

    return path_tmp