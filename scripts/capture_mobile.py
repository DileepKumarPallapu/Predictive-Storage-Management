import os
from playwright.sync_api import sync_playwright

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
screenshot_dir = r'C:\Users\dilee\.gemini\antigravity\brain\ca01d69b-34d0-4861-9b05-3a2b2ae733c4\screenshots'

def capture_mobile():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=edge_path)
        context = browser.new_context(viewport={'width': 420, 'height': 850})
        page = context.new_page()

        page.goto('http://127.0.0.1:5173/')
        page.evaluate("() => { localStorage.setItem('aegisstor_theme', 'light'); localStorage.setItem('aegisstor_onboarding_completed', 'true'); }")
        page.reload()
        page.wait_for_timeout(1000)

        page.screenshot(path=os.path.join(screenshot_dir, 'current_dashboard_mobile.png'))
        print("Captured mobile screenshot")

        # Click hamburger menu
        menu_btn = page.locator("button[aria-label='Toggle Navigation Menu']").first
        if menu_btn.count() > 0:
            menu_btn.click()
            page.wait_for_timeout(500)
            page.screenshot(path=os.path.join(screenshot_dir, 'current_dashboard_mobile_menu.png'))
            print("Captured mobile drawer screenshot")

        browser.close()

if __name__ == '__main__':
    capture_mobile()
