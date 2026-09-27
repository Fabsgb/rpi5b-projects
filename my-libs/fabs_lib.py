"""Personal helper library for my scripts.

Collects small utilities that get reused across scripts (console output,
Playwright helpers, timestamped/colored logging) to avoid copy-pasting the
same boilerplate and to reduce small implementation mistakes.
"""
from __future__ import annotations

from sys import stderr, stdout
from unicodedata import normalize, combining
from datetime import datetime
from time import sleep
from random import uniform
from typing import Literal
from os import path, makedirs, system
from platform import system as platform_system
from getpass import getuser
from secrets import token_urlsafe

from playwright.sync_api import Locator, Frame
from colorama import Fore
from colorama.initialise import orig_stdout


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
    """Return the current local time following ISO-8601 as a string."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def get_content_frame(locator: Locator) -> Frame:
    """Resolve an `<iframe>` locator to the Playwright `Frame` inside it.

    Raises `RuntimeError` instead of returning `None` so a missing or
    detached frame fails loudly right here, rather than causing a
    confusing `AttributeError` further down the script.
    """
    handle = locator.element_handle()
    if not handle:
        raise RuntimeError("Failed to obtain element handle for frame locator.")
    frame = handle.content_frame()
    if not frame:
        raise RuntimeError("Failed to resolve content frame from handle.")
    return frame


def match_choice(wanted_choice: str, options: list[str]) -> str:
    """Match a wanted value to the best-fitting entry in `options`.

    Comparison ignores font styling, accents and casing (via
    `normalize_text`). A match is any option whose normalized text
    contains the normalized `wanted_choice` as a substring; among all
    matches, the shortest one wins, to avoid over-matching against
    longer, unrelated options.

    Raises instead of silently guessing when nothing matches — important
    when `wanted_choice` comes from an LLM, since it's safer to fail
    loudly than to keep going with a silently wrong option selected.

    Raises:
        ValueError: if no option contains `wanted_choice`.
    """
    best_length = float("inf")
    choice = None

    normalized_wanted = normalize_text(wanted_choice)

    for option in options:
        normalized_option = normalize_text(option)

        if normalized_wanted in normalized_option:
            if len(normalized_option) < best_length:
                best_length = len(normalized_option)
                choice = option

    if choice is None:
        raise ValueError(f"{wanted_choice} is not a valid option!")
    return choice


def human_typing(*, locator: Locator, text: str, min_delay: float = 0.08, max_delay: float = 0.25) -> None:
    """Type `text` into `locator` one character at a time, like a human.

    Uses `press_sequentially` (not `press`, which is for key names, and
    not the deprecated `type`) so real per-character keydown/keyup events
    fire — needed for fields that react live to each keystroke (e.g.
    autocomplete). `min_delay`/`max_delay` (seconds) control the random
    pause between characters.
    """
    for char in text:
        locator.press_sequentially(char)
        sleep(uniform(min_delay, max_delay))


def tmp_path(application: str) -> str:
    platform = platform_system().casefold()
    if platform == "linux":
        path_tmp = f"/tmp/{application}_{getuser()}_{token_urlsafe(8)}"
        while path.exists(path_tmp):
            path_tmp = f"/tmp/{application}_{getuser()}_{token_urlsafe(8)}"
        makedirs(path_tmp, exist_ok=True)
        if system("setfacl -d -m u::rwx,g::,o:: " + path_tmp) != 0:
            if orig_stdout is not None:
                log_event("Could not use 'setfacl', using chmod as a fallback.", level="WARNING")
            else:
                log(f"[WARNING][{now()}]Could not use 'setfacl', using chmod as a fallback.")
            system("chmod 2700 " + path_tmp)
    elif platform == "windows":
        path_tmp = path.join(path.expandvars("%TEMP%"), f"{application}_{getuser()}_{token_urlsafe(8)}")
        while path.exists(path_tmp):
            path_tmp = path.join(path.expandvars("%TEMP%"), f"{application}_{getuser()}_{token_urlsafe(8)}")
        makedirs(path_tmp, exist_ok=True)
        system(r'icacls "' + path_tmp + '" /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"')
    else:
        raise NotImplementedError(f"{platform} has not been implemented yet!")

    return path_tmp


def log_event(msg: object, *, level: Literal["SUCCESS", "INFO", "WARNING", "ERROR"], end: str = "\n", flush: bool = False) -> None:
    """Log a message to stderr with a colored severity tag and a timestamp.

    Requires `colorama.init()` to have been called once beforehand
    (needed on Windows terminals for the ANSI color codes to render
    correctly; harmless elsewhere).

    Raises:
        ValueError: if `level` isn't one of the supported values — this
            runtime check matters because `Literal` is only enforced by
            static type checkers, not at runtime.
    """
    colors = {
        "SUCCESS": Fore.GREEN,
        "INFO": Fore.BLUE,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
    }
    if level not in colors:
        raise ValueError(f"{level} is not a valid status level!")

    log(msg=f"{colors[level]}[{level}]{Fore.RESET}[{now()}] {str(msg).strip()}", end=end, flush=flush)