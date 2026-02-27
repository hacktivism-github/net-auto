from __future__ import annotations

from typing import Dict, Any, Optional
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

PREFERRED_VALUES = ["110002", "110000"]  # strict admin-only, then admin/user

# Fallback by label (Portuguese variants seen in your HTML)
PREFERRED_LABEL_CONTAINS = [
    "proteg",          # "Proteg por senha admin", "Protegido por senha ..."
    "senha",           # ensure it's password-related
    "admin",           # prefer admin protection
]


def _best_option_value_for_select(select_loc) -> Optional[str]:
    """
    Returns the best available option value for this <select>,
    based on PREFERRED_VALUES; falls back to label heuristics.
    """
    try:
        options = select_loc.evaluate(
            """el => Array.from(el.options).map(o => ({value: String(o.value), label: String(o.text || '')}))"""
        ) or []
    except Exception:
        options = []

    values = [o.get("value") for o in options if o.get("value") is not None]

    # 1) Prefer known numeric values
    for v in PREFERRED_VALUES:
        if v in values:
            return v

    # 2) Fallback: pick an option whose label suggests password protection (admin)
    # Avoid "Sem segurança" and "Desativado"
    def label_ok(lbl: str) -> bool:
        t = (lbl or "").lower()
        if "sem segurança" in t or "desativ" in t:
            return False
        return all(k in t for k in PREFERRED_LABEL_CONTAINS)

    for o in options:
        if label_ok(o.get("label", "")):
            return o.get("value")

    return None


def harden_ms_function_protection(client) -> Dict[str, Any]:
    """
    Harden MS 'function protection' dropdowns on lite-password.html.

    Changes any dropdown still at '0' (Sem segurança) to:
      - 110002 if present, else 110000, else label-based password-protect option.

    Only targets the templates form (the one with submit name="Submit" value="Enviar").
    """
    page = client.page
    changed = 0
    total_relevant = 0

    try:
        client.goto(
            "/cgi-bin/dynamic/printer/config/secure/auth/lite-password.html",
            wait_until="domcontentloaded",
        )

        if "login.html" in (page.url or "").lower():
            client.dump("ms_templates_bounced_to_login")
            return {"ok": False, "changed": 0, "total": 0}

        # Target ONLY the templates form (avoids clicking ModifyAdmin/ModifyUser by mistake)
        form = page.locator('form:has(input[type="submit"][name="Submit"][value="Enviar"])')
        if form.count() == 0:
            client.dump("ms_templates_no_templates_form")
            return {"ok": False, "changed": 0, "total": 0}

        selects = form.locator("select")
        if selects.count() == 0:
            client.dump("ms_templates_no_selects")
            return {"ok": False, "changed": 0, "total": 0}

        for i in range(selects.count()):
            sel = selects.nth(i)

            # Count only selects that we know how to harden (have a best option)
            best = _best_option_value_for_select(sel)
            if not best:
                continue
            total_relevant += 1

            try:
                current = str(sel.input_value())
            except Exception:
                continue

            if current != "0":
                continue

            try:
                sel.select_option(value=best)
                changed += 1
            except Exception:
                continue

        if changed == 0:
            # Already hardened (or nothing relevant)
            return {"ok": True, "changed": 0, "total": total_relevant}

        submit = form.locator('input[type="submit"][name="Submit"][value="Enviar"]')
        if submit.count() == 0:
            client.dump("ms_templates_no_submit")
            return {"ok": False, "changed": changed, "total": total_relevant}

        submit.first.click(timeout=client.timeout_ms)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)
        except Exception:
            pass

        # Verify again
        client.goto(
            "/cgi-bin/dynamic/printer/config/secure/auth/lite-password.html",
            wait_until="domcontentloaded",
        )

        if "login.html" in (page.url or "").lower():
            # Session may have ended; submit might still have worked.
            client.dump("ms_templates_verify_bounced_login")
            return {"ok": True, "changed": changed, "total": total_relevant}

        form2 = page.locator('form:has(input[type="submit"][name="Submit"][value="Enviar"])')
        if form2.count() == 0:
            client.dump("ms_templates_verify_no_templates_form")
            return {"ok": False, "changed": changed, "total": total_relevant}

        selects2 = form2.locator("select")
        for i in range(selects2.count()):
            sel = selects2.nth(i)
            best = _best_option_value_for_select(sel)
            if not best:
                continue
            try:
                current = str(sel.input_value())
            except Exception:
                continue
            if current == "0":
                client.dump("ms_templates_verify_still_open")
                return {"ok": False, "changed": changed, "total": total_relevant}

        return {"ok": True, "changed": changed, "total": total_relevant}

    except PlaywrightTimeoutError:
        client.dump("ms_templates_timeout")
        return {"ok": False, "changed": changed, "total": total_relevant}
    except Exception:
        client.dump("ms_templates_exception")
        return {"ok": False, "changed": changed, "total": total_relevant}