from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from ..ews_client import LexmarkEWSClient


def apply_basic_security(client: LexmarkEWSClient, username: str, password: str) -> bool:
    """
    Workflow:
      1) /cgi-bin/dynamic/config/config.html
      2) /cgi-bin/dynamic/config/secure/security.html
      3) /cgi-bin/dynamic/printer/config/secure/authsetup.html
      4) auth_type=UsernamePassword + username/password/password2 + submit
    """
    try:
        client.goto("/cgi-bin/dynamic/config/config.html")
        client.goto("/cgi-bin/dynamic/config/secure/security.html")
        client.goto("/cgi-bin/dynamic/printer/config/secure/authsetup.html")

        client.wait("#auth_type")

        # quicksetup starts display:none in HTML, shown by window.onload; force if needed
        client.ensure_visible("#quicksetup")

        client.page.locator("#auth_type").select_option(value="UsernamePassword")
        client.page.wait_for_selector("#username", state="visible", timeout=client.timeout_ms)

        client.page.locator("#username").fill(username)
        client.page.locator("#password").fill(password)
        client.page.locator("#password2").fill(password)

        btn = client.page.locator('input[type="submit"][name="submit"]')
        if btn.count() == 0:
            btn = client.page.locator('input[type="submit"][value*="configuração básica"]')

        btn.first.click(timeout=client.timeout_ms)
        client.page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)
        return True

    except PlaywrightTimeoutError:
        client.dump("basic_security_timeout")
        return False
    except Exception as e:
        print(f"    [!] Basic Security failed: {e}")
        client.dump("basic_security_exception")
        return False

