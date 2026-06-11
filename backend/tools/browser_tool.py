from typing import Any, Dict


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = payload.get("action")
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:
        return {"ok": False, "error": f"playwright not installed: {e}"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            url = payload.get("url", "about:blank")
            page.goto(url)

            if action == "navigate":
                out = {"ok": True, "url": page.url, "title": page.title()}
            elif action == "click":
                page.click(payload["selector"])
                out = {"ok": True, "url": page.url}
            elif action == "fill":
                page.fill(payload["selector"], payload.get("text", ""))
                out = {"ok": True}
            elif action == "screenshot":
                path = payload.get("path", "/tmp/browser_capture.png")
                page.screenshot(path=path, full_page=True)
                out = {"ok": True, "path": path}
            elif action == "extract":
                selector = payload.get("selector", "body")
                content = page.locator(selector).inner_text()
                out = {"ok": True, "content": content[:30000]}
            elif action == "js":
                script = payload.get("script", "() => document.title")
                result = page.evaluate(script)
                out = {"ok": True, "result": result}
            else:
                out = {"ok": False, "error": "Unknown action"}

            browser.close()
            return out
    except Exception as e:
        return {"ok": False, "error": str(e)}
