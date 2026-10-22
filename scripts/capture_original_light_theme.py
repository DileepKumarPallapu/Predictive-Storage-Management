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

        # 1. Desktop Light (1727x893)
        print("Capturing 1: Desktop Overview Light (1727x893)...")
        ctx_light = browser.new_context(viewport={"width": 1727, "height": 893})
        ctx_light.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light'); localStorage.setItem('aegisstor_light_default_v2', 'true');")
        page = ctx_light.new_page()
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_01_overview_desktop_light.png"))

        # 2. Desktop Dark (1727x893)
        print("Capturing 2: Desktop Overview Dark (1727x893)...")
        theme_btn = page.locator("button[aria-label='Toggle Color Theme']")
        theme_btn.click()
        time.sleep(1)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_02_overview_desktop_dark.png"))

        # Switch back to light
        theme_btn.click()
        time.sleep(1)

        # 3. Compare Actions / Safe Feasible Actions (1727x893)
        print("Capturing 3: Compare Actions Page (1727x893)...")
        page.locator("button:has-text('Compare Actions')").first.click()
        try:
            page.wait_for_selector("text=Safe, Feasible Actions", timeout=8000)
        except Exception:
            pass
        time.sleep(2.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_03_compare_actions_light.png"))

        # 4. Storage Fleet Page (1727x893)
        print("Capturing 4: Storage Fleet Page...")
        page.locator("button:has-text('Storage Fleet')").first.click()
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_04_storage_fleet_light.png"))

        # 5. Device Details Page (1727x893)
        print("Capturing 5: Device Details Page...")
        page.locator("button:has-text('Device Details')").first.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_05_device_details_light.png"))

        # 6. Digital Twin Sandbox (1727x893)
        print("Capturing 6: Digital Twin Sandbox...")
        page.locator("button:has-text('Digital Twin Sandbox')").first.click()
        try:
            page.wait_for_selector("text=Monte Carlo Resilience Sandbox", timeout=8000)
        except Exception:
            pass
        time.sleep(2.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_06_digital_twin_light.png"))

        # 7. Incident Command Page (1727x893)
        print("Capturing 7: Incident Command Page...")
        page.locator("button:has-text('Incident Command')").first.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_07_incident_command_light.png"))

        ctx_light.close()

        # 8. Laptop Viewport (1366x768)
        print("Capturing 8: Laptop Overview (1366x768)...")
        ctx_laptop = browser.new_context(viewport={"width": 1366, "height": 768})
        ctx_laptop.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light'); localStorage.setItem('aegisstor_light_default_v2', 'true');")
        p_laptop = ctx_laptop.new_page()
        p_laptop.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        p_laptop.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_08_overview_laptop_1366.png"))
        ctx_laptop.close()

        # 9. Tablet Landscape Overview (1024x768)
        print("Capturing 9: Tablet Landscape Overview (1024x768)...")
        ctx_tab_ls = browser.new_context(viewport={"width": 1024, "height": 768})
        ctx_tab_ls.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light'); localStorage.setItem('aegisstor_light_default_v2', 'true');")
        p_tab_ls = ctx_tab_ls.new_page()
        p_tab_ls.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        p_tab_ls.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_09_overview_tablet_1024.png"))

        # 10. Tablet Landscape Compare Actions (1024x768)
        print("Capturing 10: Tablet Landscape Compare Actions (1024x768)...")
        p_tab_ls.locator("button:has-text('Compare Actions')").first.click()
        try:
            p_tab_ls.wait_for_selector("text=Safe, Feasible Actions", timeout=8000)
        except Exception:
            pass
        time.sleep(2)
        p_tab_ls.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_10_compare_actions_tablet_1024.png"))
        ctx_tab_ls.close()

        # 11. Tablet Portrait Overview (768x1024)
        print("Capturing 11: Tablet Portrait Overview (768x1024)...")
        ctx_tab_pt = browser.new_context(viewport={"width": 768, "height": 1024})
        ctx_tab_pt.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light'); localStorage.setItem('aegisstor_light_default_v2', 'true');")
        p_tab_pt = ctx_tab_pt.new_page()
        p_tab_pt.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        p_tab_pt.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_11_overview_tablet_768.png"))
        ctx_tab_pt.close()

        # 12. Mobile Portrait Overview (390x844)
        print("Capturing 12: Mobile Portrait Overview (390x844)...")
        ctx_mobile = browser.new_context(viewport={"width": 390, "height": 844})
        ctx_mobile.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light'); localStorage.setItem('aegisstor_light_default_v2', 'true');")
        p_mobile = ctx_mobile.new_page()
        p_mobile.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        p_mobile.screenshot(path=os.path.join(OUTPUT_DIR, "light_restore_12_overview_mobile_390.png"))
        ctx_mobile.close()

        browser.close()
        print("All 12 screenshots captured successfully.")

if __name__ == "__main__":
    run()
