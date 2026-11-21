#!/usr/bin/env python3
"""Shared setup steps for the image-generation website."""
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

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from fabs_lib_common import log_event
from fabs_lib_playwright import remaining_timeout_ms


def prepare_image_site(page: Page, *, deadline: float | None = None) -> None:
    """Dismiss the site's age/preferences gate when it is present."""
    preferences_link = page.locator("#changePreferencesLinkEl")
    log_event("Checking for preferences dialog...", level="INFO")
    try:
        preferences_link.wait_for(
            state="visible",
            timeout=remaining_timeout_ms(deadline, maximum=2_000),
        )
    except PlaywrightTimeoutError:
        log_event("Preferences dialog not found; continuing.", level="INFO")
    else:
        log_event("Opening preferences dialog...", level="INFO")
        try:
            preferences_link.click(timeout=remaining_timeout_ms(deadline))
        except PlaywrightTimeoutError:
            log_event(
                "Preferences dialog click failed; trying JavaScript fallback.",
                level="WARNING",
            )
            preferences_link.evaluate(
                "element => element.click()",
                timeout=remaining_timeout_ms(deadline),
            )

        visibility = page.locator("#sensitiveContentVisibilityEl")
        log_event("Setting sensitive-content visibility to warn...", level="INFO")
        try:
            selected_values = visibility.select_option(
                "warn",
                timeout=remaining_timeout_ms(deadline),
            )
        except PlaywrightTimeoutError:
            log_event(
                "select_option() timed out; using JavaScript fallback.",
                level="WARNING",
            )
            selected_value = visibility.evaluate(
                """element => {
                    element.value = "warn";
                    element.dispatchEvent(new Event("input", { bubbles: true }));
                    element.dispatchEvent(new Event("change", { bubbles: true }));
                    return element.value;
                }""",
                timeout=remaining_timeout_ms(deadline),
            )
            if selected_value != "warn":
                raise RuntimeError(
                    "Could not set sensitive-content visibility to warn."
                )
        else:
            if selected_values != ["warn"]:
                raise RuntimeError(
                    "Could not set sensitive-content visibility to warn."
                )

        age_verification_label = page.locator(
            'label[for="ageVerificationCheckboxEl"]'
        )
        log_event("Checking age verification...", level="INFO")
        try:
            age_verification_label.click(timeout=remaining_timeout_ms(deadline))
        except PlaywrightTimeoutError:
            log_event(
                "Age verification label click failed; checking the form control.",
                level="WARNING",
            )
            page.locator("#ageVerificationCheckboxEl").check(
                timeout=remaining_timeout_ms(deadline)
            )

        save_preferences = page.locator('button[onclick*="savePreferences"]')
        log_event("Saving preferences...", level="INFO")
        try:
            save_preferences.click(timeout=remaining_timeout_ms(deadline))
        except PlaywrightTimeoutError:
            log_event(
                "Save button click failed; trying JavaScript fallback.",
                level="WARNING",
            )
            save_preferences.evaluate(
                "element => element.click()",
                timeout=remaining_timeout_ms(deadline),
            )

    show_content = page.locator("#showContentBtn")
    log_event("Showing content...", level="INFO")
    try:
        show_content.wait_for(
            state="visible",
            timeout=remaining_timeout_ms(deadline, maximum=2_000),
        )
    except PlaywrightTimeoutError:
        log_event("Content button not found; continuing.", level="INFO")
    else:
        try:
            show_content.click(timeout=remaining_timeout_ms(deadline))
        except PlaywrightTimeoutError:
            log_event(
                "Content button click failed; using JavaScript fallback.",
                level="WARNING",
            )
            show_content.evaluate(
                "element => element.click()",
                timeout=remaining_timeout_ms(deadline),
            )
