#!/usr/bin/env python3
"""Shared text-matching and colored-logging helpers."""
from __future__ import annotations

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