from __future__ import annotations

from typing import Dict

def identify_model(client) -> Dict[str, str]:
    """
    Best-effort model detection. Returns:
        {"model": "MX710" or "MS811" or None, "family": "MX"|"MS"|None, "evidence": "..."}
    """
    page = client.page
    try:
        client.goto("/cgi-bin/dynamic/topbar.html", wait_until="domcontentloaded")
    except Exception:
        pass

    text = ""
    try:
        text = page.inner_text("body")
    except Exception:
        try:
            text = page.content()
        except Exception:
            text = ""
    t = (text or "").lower()

    if "lexmark ms" in t:
        return {"model": "Lexmark MS Series", "family": "MS"}
    if "lexmark mx" in t:
        return {"model": "Lexmark MX Series", "family": "MX"}
    return {"model": "Unknown", "family": "Unknown"}

    
