from __future__ import annotations

import re
from typing import Optional, Dict

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

MODEL_RE = re.compile(r"Lexmark\s+([A-Z]{2}\d{3})", re.IGNORECASE)

def identify_model(client) -> Dict[str, Optional[str]]:
    """
    Best-effort model detection. Returns:
        {"model": "MX710" or "MS811" or None, "family": "MX"|"MS"|None, "evidence": "..."}
    """
    page = client.page
    try:
        client.goto("/cgi-bin/dynamic/topbar.html", wait_until="domcontentloaded")

        html = page.content()
        m = MODEL_RE.search(html)
        if not m:
            return {"model": None, "family": None, "evidence": "Model not found in topbar.html"}
        model = m.group(1).upper()
        family = "MX" if model.startswith("MX") else "MS" if model.startswith("MS") else None
        return {"model": model, "family": family, "evidence": f"Detected in /topbar.html: {model}"}
    except PlaywrightTimeoutError:
        client.dump("identify_timeout")
        return {"model": None, "family": None, "evidence": "Timeout while loading topbar.html"}
    except Exception:
        client.dump("identify_exception")
        return {"model": None, "family": None, "evidence": "Exception during model detection"}