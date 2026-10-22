import os
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\dilee\.gemini\antigravity\brain\ca01d69b-34d0-4861-9b05-3a2b2ae733c4\screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH if os.path.exists(EDGE_PATH) else None,
            headless=True
        )

        # 1. Desktop Light (1722x896)
        ctx_light = browser.new_context(viewport={"width": 1722, "height": 896})
        ctx_light.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light');")
        page = ctx_light.new_page()

        print("Capturing 1: Desktop Overview Light (1722x896)...")
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "twain_01_overview_desktop_light.png"))

        # 2. Desktop Dark (1722x896)
        print("Capturing 2: Desktop Overview Dark (1722x896)...")
        theme_btn = page.locator("button[aria-label='Toggle Color Theme']")
        theme_btn.click()
        time.sleep(1)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "twain_02_overview_desktop_dark.png"))

        # Switch back to light
        theme_btn.click()
        time.sleep(1)

        # 3. Storage Fleet Page
        print("Capturing 3: Storage Fleet Page...")
        page.locator("button:has-text('Storage Fleet')").first.click()
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "twain_03_storage_fleet_light.png"))

        # 4. Device Details Page
        print("Capturing 4: Device Details Page...")
        page.locator("button:has-text('Device Details')").first.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "twain_04_device_details_light.png"))

        # 5. Compare Actions Page
        print("Capturing 5: Compare Actions Page...")
        page.locator("button:has-text('Compare Actions')").first.click()
        try:
            page.wait_for_selector("text=Safe, Feasible Actions", timeout=10000)
        except Exception:
            pass
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "twain_05_compare_actions_light.png"))

        # 6. Digital Twin Sandbox
        print("Capturing 6: Digital Twin Sandbox...")
        page.locator("button:has-text('Digital Twin Sandbox')").first.click()
        time.sleep(3.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "twain_06_digital_twin_light.png"))

        # 7. Incident Command Page
        print("Capturing 7: Incident Command Page...")
        page.locator("button:has-text('Incident Command')").first.click()
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "twain_07_incident_command_light.png"))

        ctx_light.close()

        # 8. Tablet (1024x768)
        print("Capturing 8: Tablet 1024x768...")
        ctx_tab = browser.new_context(viewport={"width": 1024, "height": 768})
        ctx_tab.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light');")
        page_tab = ctx_tab.new_page()
        page_tab.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        page_tab.screenshot(path=os.path.join(OUTPUT_DIR, "twain_08_overview_tablet_1024.png"))
        ctx_tab.close()

        # 9. Mobile (390x844)
        print("Capturing 9: Mobile 390x844...")
        ctx_mob = browser.new_context(viewport={"width": 390, "height": 844})
        ctx_mob.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light');")
        page_mob = ctx_mob.new_page()
        page_mob.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        page_mob.screenshot(path=os.path.join(OUTPUT_DIR, "twain_09_overview_mobile_390.png"))

        # 10. Mobile Menu Open
        print("Capturing 10: Mobile Menu Open...")
        menu_btn = page_mob.locator("button[aria-label='Toggle Navigation Menu']").first
        if menu_btn.count() > 0:
            menu_btn.click(force=True)
            time.sleep(1)
            page_mob.screenshot(path=os.path.join(OUTPUT_DIR, "twain_10_mobile_menu_open.png"))
        ctx_mob.close()

        browser.close()
        print("All 10 Twain-inspired pastel showcase screenshots captured successfully!")

if __name__ == "__main__":
    run()
