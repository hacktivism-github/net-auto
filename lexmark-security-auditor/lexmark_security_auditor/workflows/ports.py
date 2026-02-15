from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


TCP80_NAME = "vac.255.GUIPORTENABLE.3"


def disable_http_tcp80(client) -> bool:
    """
    Assumes an authenticated session (runner/auth guarantees it).
    Goes to ports page, ensures TCP 80 is unchecked, submits, verifies.

    Idempotent: if already disabled, returns True.
    """
    page = client.page

    try:
        # Navigate straight to the ports page (works once authenticated)
        client.goto("/cgi-bin/dynamic/config/secure/ports.html", wait_until="domcontentloaded")

        # If we got bounced to login, we don't have a session
        if "login.html" in (page.url or "").lower():
            client.dump("ports_bounced_to_login")
            return False

        # IMPORTANT: don't call .first before .count()
        tcp80 = page.locator(f'input[type="checkbox"][name="{TCP80_NAME}"]')
        if tcp80.count() == 0:
            tcp80 = page.locator(f'input[type="checkbox"][id="{TCP80_NAME}"]')

        if tcp80.count() == 0:
            client.dump("ports_no_tcp80_checkbox")
            return False

        tcp80_first = tcp80.first

        # If already unchecked, success (idempotent)
        if not tcp80_first.is_checked():
            return True

        # Uncheck (prefer uncheck; fallback click)
        try:
            tcp80_first.uncheck(timeout=client.timeout_ms)
        except Exception:
            tcp80_first.click(timeout=client.timeout_ms)

        # Submit
        submit = page.locator('form input[type="submit"][value="Enviar"]')
        if submit.count() == 0:
            submit = page.locator("form input[type='submit']")

        if submit.count() == 0:
            client.dump("ports_no_submit")
            return False

        # Some Lexmark pages do NOT trigger a navigation.
        # So: click and then wait for network idle / domcontentloaded safely.
        submit.first.click(timeout=client.timeout_ms)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)
        except Exception:
            # if no load event, still proceed to verify
            pass

        # Verify again (reload ports page)
        client.goto("/cgi-bin/dynamic/config/secure/ports.html", wait_until="domcontentloaded")

        # Still authenticated?
        if "login.html" in (page.url or "").lower():
            client.dump("ports_verify_bounced_to_login")
            return False

        tcp80_after = page.locator(f'input[type="checkbox"][name="{TCP80_NAME}"]')
        if tcp80_after.count() == 0:
            tcp80_after = page.locator(f'input[type="checkbox"][id="{TCP80_NAME}"]')

        if tcp80_after.count() == 0:
            client.dump("ports_verify_no_tcp80_checkbox")
            return False

        # Return True if disabled (unchecked)
        return not tcp80_after.first.is_checked()

    except PlaywrightTimeoutError:
        client.dump("ports_timeout")
        return False
    except Exception:
        client.dump("ports_exception")
        return False