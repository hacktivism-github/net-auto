from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def _has_login_form(ctx) -> bool:
    try:
        return ctx.locator("form#login_form").count() > 0
    except Exception:
        return False


def is_on_login_page(page) -> bool:
    url = (page.url or "").lower()
    if "login.html" in url:
        return True

    # page or frames
    if _has_login_form(page):
        return True
    for fr in page.frames:
        if _has_login_form(fr):
            return True

    return False


def login_form_based(client, username: str, password: str) -> bool:
    """
    Login via Lexmark EWS login form.
    Uses the selectors confirmed in your HTML.

    Success criteria:
      - login form no longer present OR
      - URL no longer contains login.html
    """
    page = client.page

    try:
        page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        # Wait for the form inputs
        page.wait_for_selector("#login_form", timeout=client.timeout_ms)
        page.wait_for_selector("#username", timeout=client.timeout_ms)
        page.wait_for_selector("#password", timeout=client.timeout_ms)

        page.locator("#username").fill(username)
        page.locator("#password").fill(password)

        submit = page.locator('form#login_form input[type="submit"][value="Enviar"]')
        if submit.count() == 0:
            submit = page.locator("form#login_form input[type='submit']").first

        # Click + wait for navigation (important for session cookies)
        with page.expect_navigation(wait_until="domcontentloaded", timeout=client.timeout_ms):
            submit.first.click(timeout=client.timeout_ms)

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


def ensure_authenticated_session(client, username: str, password: str, target_path: str = "/cgi-bin/dynamic/config/config.html") -> bool:
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