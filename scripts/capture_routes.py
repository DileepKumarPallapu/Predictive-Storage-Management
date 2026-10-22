import os
from playwright.sync_api import sync_playwright

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
screenshot_dir = r'C:\Users\dilee\.gemini\antigravity\brain\ca01d69b-34d0-4861-9b05-3a2b2ae733c4\screenshots'

def capture_routes():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=edge_path)
        context = browser.new_context(viewport={'width': 1722, 'height': 896})
        page = context.new_page()

        page.goto('http://127.0.0.1:5173/')
        page.evaluate("() => { localStorage.setItem('aegisstor_theme', 'light'); localStorage.setItem('aegisstor_onboarding_completed', 'true'); }")
        page.reload()
        page.wait_for_timeout(1000)

        routes = [
            ('fleet', 'Storage Fleet'),
            ('twin', 'Digital Twin Sandbox'),
            ('interventions', 'Compare Actions'),
            ('alerts', 'Alerts & Safeguards'),
        ]

        for route_id, label in routes:
            btn = page.locator(f"button:has-text('{label}')").first
            if btn.count() > 0:
                btn.click()
                page.wait_for_timeout(800)
                page.screenshot(path=os.path.join(screenshot_dir, f'page_{route_id}_light.png'))
                print(f"Captured {route_id} screenshot")

        browser.close()

if __name__ == '__main__':
    capture_routes()
