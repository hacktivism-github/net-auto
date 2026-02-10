from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from ..ews_client import LexmarkEWSClient

TCP80_ID = "vac.255.GUIPORTENABLE.3"


def disable_http_tcp80(client: LexmarkEWSClient) -> bool:
    """
    Workflow:
      1) /cgi-bin/dynamic/config/config.html
      2) /cgi-bin/dynamic/config/secure/security.html
      3) /cgi-bin/dynamic/config/secure/ports.html
      4) uncheck TCP 80 checkbox + submit("Enviar") + validate
    """
    try:
        client.goto("/cgi-bin/dynamic/config/config.html")
        client.goto("/cgi-bin/dynamic/config/secure/security.html")
        resp = client.goto("/cgi-bin/dynamic/config/secure/ports.html")

        if resp is not None and resp.status in (401, 403):
            client.dump("ports_auth_required")
            return False

        # SAFE selector for id with dots
        cb = client.page.locator(f'input[type="checkbox"][id="{TCP80_ID}"]')
        if cb.count() == 0:
            # fallback by label text
            cb = client.page.get_by_label("TCP 80 (HTTP)")

        if cb.count() == 0:
            client.dump("ports_no_tcp80_checkbox")
            return False

        # if enabled, disable it
        if cb.first.is_checked():
            cb.first.uncheck(timeout=client.timeout_ms)

        # submit (button is: <input type="submit" value=Enviar>)
        if not client.click_submit(["Enviar"]):
            client.dump("ports_no_submit")
            return False

        client.page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        # Validate
        client.goto("/cgi-bin/dynamic/config/secure/ports.html")
        cb2 = client.page.locator(f'input[type="checkbox"][id="{TCP80_ID}"]')
        if cb2.count() == 0:
            cb2 = client.page.get_by_label("TCP 80 (HTTP)")

        if cb2.count() == 0:
            client.dump("ports_validate_no_checkbox")
            return False

        return not cb2.first.is_checked()

    except PlaywrightTimeoutError:
        client.dump("disable_http_timeout")
        return False
    except Exception as e:
        print(f"    [!] Disable HTTP failed: {e}")
        client.dump("disable_http_exception")
        return False

