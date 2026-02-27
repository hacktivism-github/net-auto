from __future__ import annotations
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def _looks_masked(value: str) -> bool:
    v = (value or "").strip()
    return v != "" and set(v) == {"*"}


def apply_basic_security_ms_password_only(client, admin_password: str) -> bool:
    """
    MS password-only hardening (set admin password).
    Idempotent:
      - If fields are masked (********), assume already set and return True.
      - Otherwise, fill + submit.
      - If after submit we bounce to login.html, treat as success.
    """
    page = client.page
    admin_password = (admin_password or "").strip()
    if not admin_password:
        return False

    try:
        client.goto("/cgi-bin/dynamic/printer/config/secure/auth/lite-password.html", wait_until="domcontentloaded")

        if "login.html" in (page.url or "").lower():
            client.dump("ms_basic_bounced_to_login_initial")
            return False

        page.wait_for_selector("#adminPassword1", timeout=client.timeout_ms)
        page.wait_for_selector("#adminPassword2", timeout=client.timeout_ms)

        a1 = page.locator("#adminPassword1")
        a2 = page.locator("#adminPassword2")

        # If already masked, assume already configured
        try:
            v1 = a1.input_value()
            v2 = a2.input_value()
            if _looks_masked(v1) or _looks_masked(v2):
                return True
        except Exception:
            pass

        # Make sure any onFocus clearSettingByName triggers and existing value is cleared
        try:
            a1.click(timeout=client.timeout_ms)
        except Exception:
            pass
        a1.fill("")                 # clear explicitly
        a1.fill(admin_password)

        try:
            a2.click(timeout=client.timeout_ms)
        except Exception:
            pass
        a2.fill("")
        a2.fill(admin_password)

        submit = page.locator('input[type="submit"][name="ModifyAdmin"]')
        if submit.count() == 0:
            submit = page.locator('input[type="submit"][value="Modificar"]')
        if submit.count() == 0:
            client.dump("ms_basic_no_submit")
            return False

        submit.first.click(timeout=client.timeout_ms)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)
        except Exception:
            pass

        # Bounce to login = strong sign password enforcement is now active
        if "login.html" in (page.url or "").lower():
            return True

        # Verify by reloading
        client.goto("/cgi-bin/dynamic/printer/config/secure/auth/lite-password.html", wait_until="domcontentloaded")
        if "login.html" in (page.url or "").lower():
            return True

        # Check masking after reload
        try:
            v1b = page.locator("#adminPassword1").input_value()
            v2b = page.locator("#adminPassword2").input_value()
            if _looks_masked(v1b) or _looks_masked(v2b):
                return True
        except Exception:
            pass

        client.dump("ms_basic_verify_not_confirmed")
        return False

    except PlaywrightTimeoutError:
        client.dump("ms_basic_timeout")
        return False
    except Exception:
        client.dump("ms_basic_exception")
        return False