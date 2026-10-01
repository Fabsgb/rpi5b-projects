#!/usr/bin/env python3
"""Playwright helpers shared by browser-automation scripts."""
from __future__ import annotations

from random import uniform
from time import sleep

from playwright.sync_api import Frame, Locator

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


def human_typing(*, locator: Locator, text: str, min_delay: float = 0.08, max_delay: float = 0.25) -> None:
    """Type `text` into `locator` one character at a time with random delays."""
    for char in text:
        locator.press_sequentially(char)
        sleep(uniform(min_delay, max_delay))