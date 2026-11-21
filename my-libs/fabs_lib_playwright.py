#!/usr/bin/env python3
"""Playwright helpers shared by browser-automation scripts."""
#
# Copyright (C) 2026  Fabsgb (https://github.com/Fabsgb, https://codeberg.org/Fabsgb)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
from __future__ import annotations

from random import uniform
from time import monotonic, sleep
from typing import Callable, Literal
from urllib import request

from camoufox.sync_api import Camoufox
from playwright.sync_api import Frame, Locator, Page

from fabs_lib_common import log_event, timed_input


class OperationTimeoutError(TimeoutError):
    """Raised when an operation exceeds its shared deadline."""


def remaining_time(deadline: float | None) -> float | None:
    """Return seconds remaining, raising when a supplied deadline has expired."""
    if deadline is None:
        return None
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise OperationTimeoutError("Global timeout reached.")
    return remaining


def remaining_timeout_ms(
    deadline: float | None,
    *,
    maximum: int | None = None,
) -> int | None:
    """Return the remaining deadline as milliseconds, optionally capped."""
    remaining = remaining_time(deadline)
    if remaining is None:
        return maximum
    timeout = max(1, int(remaining * 1000))
    return min(timeout, maximum) if maximum is not None else timeout


def start_browser(
    *,
    headless: bool,
    proxy: str | bool | None = "http://localhost:666",
) -> Camoufox:
    """Create the standard humanized Camoufox browser context manager."""
    return Camoufox(
        humanize=True,
        headless=headless,
        proxy={"server": proxy} if isinstance(proxy, str) else None,
    )


def proxy_check(
    page: Page,
    *,
    deadline: float | None,
    on_error: Callable[[], None] | None = None,
    prompt: str = "Should the generation be continued (y/N)? ",
    warning_level: Literal["WARNING", "ERROR"] = "ERROR",
) -> bool:
    """Check that browser traffic uses the proxy and ask before continuing otherwise."""
    page_timeout = remaining_timeout_ms(deadline)
    page.goto(
        "http://api.ipify.org",
        **({"timeout": page_timeout} if page_timeout is not None else {}),
    )
    remaining_time(deadline)
    content_timeout = remaining_timeout_ms(deadline)
    ip_addr = page.locator("pre").inner_text(
        **({"timeout": content_timeout} if content_timeout is not None else {})
    )
    log_event(f"VPN IP Address: {ip_addr}", level="INFO")
    request_timeout = remaining_time(deadline)
    with request.urlopen(
        "http://api.ipify.org",
        **({"timeout": request_timeout} if request_timeout is not None else {}),
    ) as response:
        host_ip = response.read().decode("utf-8")
    if ip_addr == host_ip:
        if on_error is not None:
            on_error()
        log_event(
            f"IP Address '{ip_addr}' is the ip address of your host, something "
            "might be wrong with the proxy configuration, please check!",
            level=warning_level,
        )
        if deadline is None:
            answer = input(prompt)
        else:
            answer = timed_input(
                prompt,
                timeout=min(30, remaining_time(deadline)),
            ) or ""
        if answer.casefold() not in {"yes", "y"}:
            return False
        log_event("Continuing generation...", level="INFO")
    return True


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