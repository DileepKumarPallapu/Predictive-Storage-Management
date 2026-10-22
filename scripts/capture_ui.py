import os
from playwright.sync_api import sync_playwright

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
screenshot_dir = r'C:\Users\dilee\.gemini\antigravity\brain\ca01d69b-34d0-4861-9b05-3a2b2ae733c4\screenshots'

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=edge_path)
        context = browser.new_context(viewport={'width': 1722, 'height': 896})
        page = context.new_page()

        page.goto('http://127.0.0.1:5173/')
        page.evaluate("() => { localStorage.setItem('aegisstor_theme', 'light'); localStorage.setItem('aegisstor_onboarding_completed', 'true'); }")
        page.reload()
        page.wait_for_timeout(1000)

        # 1. Top of light dashboard (1722x896)
        page.screenshot(path=os.path.join(screenshot_dir, 'current_dashboard_light.png'))
        print("Captured top light screenshot")

        # 2. 1024x768 viewport
        page.set_viewport_size({'width': 1024, 'height': 768})
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(screenshot_dir, 'current_dashboard_1024.png'))
        print("Captured 1024px light screenshot")

        browser.close()

if __name__ == '__main__':
    capture()
