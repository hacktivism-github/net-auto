from __future__ import annotations

from typing import Optional, List
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class LexmarkEWSClient:
    """
    Thin client wrapper around Playwright Page with:
    - consistent navigation (base_url + paths)
    - safe locators for IDs containing dots
    - small UI helpers
    - debug dump
    """

    def __init__(self, page, base_url: str, timeout_s: float = 12.0, debug_html: bool = False):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.timeout_ms = int(timeout_s * 1000)
        self.debug_html = debug_html

    def goto(self, path_or_url: str, wait_until: str = "domcontentloaded"):
        url = path_or_url
        if not url.startswith(("http://", "https://")):
            url = f"{self.base_url}/{path_or_url.lstrip('/')}"
        return self.page.goto(url, wait_until=wait_until, timeout=self.timeout_ms)

    def dump(self, tag: str):
        if not self.debug_html:
            return
        try:
            print(f"    [debug] ({tag}) URL: {self.page.url}")
            html = self.page.content()
            print(f"    [debug] ({tag}) HTML (first 4000 chars): {html[:4000]}")
        except Exception as e:
            print(f"    [debug] ({tag}) dump failed: {e}")

    def by_id(self, element_id: str):
        # CSS #id breaks when id contains dots; attribute selector is safe.
        return self.page.locator(f'[id="{element_id}"]')

    def click_submit(self, preferred_values: Optional[List[str]] = None) -> bool:
        preferred_values = preferred_values or []
        for v in preferred_values:
            loc = self.page.locator(f'input[type="submit"][value="{v}"]')
            if loc.count() > 0:
                loc.first.click(timeout=self.timeout_ms)
                return True

        fallback = self.page.locator('input[type="submit"]')
        if fallback.count() > 0:
            fallback.first.click(timeout=self.timeout_ms)
            return True

        return False

    def ensure_visible(self, selector: str) -> None:
        try:
            hidden = self.page.eval_on_selector(
                selector, "el => window.getComputedStyle(el).display === 'none'"
            )
            if hidden:
                self.page.eval_on_selector(selector, "el => el.style.display = 'block'")
        except Exception:
            pass

    def wait(self, selector: str, state: str = "attached") -> None:
        self.page.wait_for_selector(selector, state=state, timeout=self.timeout_ms)

    def safe(self, fn, tag: str) -> bool:
        try:
            fn()
            return True
        except PlaywrightTimeoutError:
            self.dump(f"{tag}_timeout")
            return False
        except Exception:
            self.dump(f"{tag}_exception")
            return False

