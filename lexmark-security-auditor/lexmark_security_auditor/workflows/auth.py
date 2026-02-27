from __future__ import annotations

from typing import Optional
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def _has_login_form(ctx) -> bool:
    try:
        return ctx.locator("form#login_form").count() > 0
    except Exception:
        return False


def _find_login_context(page):
    """
    Returns the first context (page or frame) where the login form exists.
    """
    if _has_login_form(page):
        return page
    for fr in page.frames:
        if _has_login_form(fr):
            return fr
    return None


def is_on_login_page(page) -> bool:
    url = (page.url or "").lower()
    if "login.html" in url:
        return True

    if _has_login_form(page):
        return True
    for fr in page.frames:
        if _has_login_form(fr):
            return True

    return False


def login_form_based(client, username: Optional[str], password: str) -> bool:
    """
    Login via Lexmark EWS login form.

    Supports:
      - MX: username + password
      - MS (password-only): username empty / None

    Success criteria:
      - login form no longer present OR
      - URL no longer contains login.html
    """
    page = client.page
    username = (username or "").strip()

    try:
        page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        ctx = _find_login_context(page)
        if ctx is None:
            # Sometimes URL has login.html but form not yet rendered; dump for tuning.
            client.dump("login_no_form_found")
            return False

        # Always require password field
        ctx.wait_for_selector("#password", timeout=client.timeout_ms)

        # Username may or may not exist / be required
        if username:
            if ctx.locator("#username").count() > 0:
                ctx.locator("#username").fill(username)
        else:
            # MS password-only: if username field exists, clear it (safe)
            if ctx.locator("#username").count() > 0:
                ctx.locator("#username").fill("")

        ctx.locator("#password").fill(password)

        submit = ctx.locator('form#login_form input[type="submit"][value="Enviar"]')
        if submit.count() == 0:
            submit = ctx.locator("form#login_form input[type='submit']").first

        # Click + wait for navigation (important for session cookies)
        # Some firmwares might not trigger full navigation, so we guard it.
        try:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=client.timeout_ms):
                submit.first.click(timeout=client.timeout_ms)
        except Exception:
            submit.first.click(timeout=client.timeout_ms)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)
            except Exception:
                pass

        # Validate we left login
        if not is_on_login_page(page):
            return True

        client.dump("login_failed_still_on_login")
        return False

    except PlaywrightTimeoutError:
        client.dump("login_timeout")
        return False
    except Exception:
        client.dump("login_exception")
        return False


def ensure_authenticated_session(
    client,
    username: Optional[str],
    password: str,
    target_path: str = "/cgi-bin/dynamic/config/config.html",
) -> bool:
    """
    Navigates to target_path. If redirected to login, performs form login.
    - For MS password-only: pass username="" (empty string) and password=<admin_password>
    - For MX: pass username and password
    """
    page = client.page
    try:
        client.goto(target_path, wait_until="domcontentloaded")

        if is_on_login_page(page):
            return login_form_based(client, username=username, password=password)

        return True

    except PlaywrightTimeoutError:
        client.dump("ensure_auth_timeout")
        return False
    except Exception:
        client.dump("ensure_auth_exception")
        return False


def logout(client) -> None:
    try:
        client.goto("/cgi-bin/dynamic/printer/logout.html", wait_until="domcontentloaded")
    except Exception:
        pass