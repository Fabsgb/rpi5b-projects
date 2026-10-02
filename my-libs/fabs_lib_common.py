#!/usr/bin/env python3
"""Shared text-matching and colored-logging helpers."""
from __future__ import annotations

from math import isfinite
from os import name as os_name
from select import select
from sys import stdin, stdout
from time import monotonic, sleep
from typing import Literal

from colorama import Fore

from fabs_lib import log, normalize_text, now


def match_choice(wanted_choice: str, options: list[str]) -> str:
    """Match a wanted value to the shortest normalized option containing it.

    Raises `ValueError` instead of silently guessing when nothing matches.
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


def log_event(msg: object, *, level: Literal["SUCCESS", "INFO", "WARNING", "ERROR"], end: str = "\n", flush: bool = False) -> None:
    """Log a message to stderr with a colored severity tag and timestamp.

    Requires `colorama.init()` to have been called once beforehand.
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


def timed_input(prompt: str, timeout: float) -> str | None:
    """Read a line from an interactive terminal, or return None on timeout.

    Supports interactive terminals on Unix and Windows. Returns None when
    stdin is not connected to a terminal.
    """
    if not isfinite(timeout) or timeout < 0:
        raise ValueError("timeout must be a finite, non-negative number")
    if not stdin.isatty():
        return None

    stdout.write(prompt)
    stdout.flush()
    deadline = monotonic() + timeout

    if os_name == "nt":
        from msvcrt import getwch, kbhit

        chars = []
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                stdout.write("\n")
                return None

            if not kbhit():
                sleep(min(0.05, remaining))
                continue

            char = getwch()
            if char in ("\x00", "\xe0"):
                getwch()
            elif char in ("\r", "\n"):
                stdout.write("\n")
                return "".join(chars)
            elif char == "\x03":
                raise KeyboardInterrupt
            elif char == "\b":
                if chars:
                    chars.pop()
                    stdout.write("\b \b")
                    stdout.flush()
            elif char.isprintable():
                chars.append(char)
                stdout.write(char)
                stdout.flush()

    remaining = max(0, deadline - monotonic())
    readable, _, _ = select([stdin], [], [], remaining)
    if not readable:
        stdout.write("\n")
        return None

    return stdin.readline().rstrip("\r\n")