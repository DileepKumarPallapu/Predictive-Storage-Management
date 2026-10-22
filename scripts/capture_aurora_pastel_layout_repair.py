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
        ctx_light.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light');")
        page = ctx_light.new_page()
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_01_overview_desktop_light.png"))

        # 2. Desktop Dark (1727x893)
        print("Capturing 2: Desktop Overview Dark (1727x893)...")
        theme_btn = page.locator("button[aria-label='Toggle Color Theme']")
        theme_btn.click()
        time.sleep(1)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_02_overview_desktop_dark.png"))

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
        page.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_03_compare_actions_light.png"))

        # 4. Storage Fleet Page (1727x893)
        print("Capturing 4: Storage Fleet Page...")
        page.locator("button:has-text('Storage Fleet')").first.click()
        time.sleep(1.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_04_storage_fleet_light.png"))

        # 5. Device Details Page (1727x893)
        print("Capturing 5: Device Details Page...")
        page.locator("button:has-text('Device Details')").first.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_05_device_details_light.png"))

        # 6. Digital Twin Sandbox (1727x893)
        print("Capturing 6: Digital Twin Sandbox...")
        page.locator("button:has-text('Digital Twin Sandbox')").first.click()
        try:
            page.wait_for_selector("text=Monte Carlo Resilience Sandbox", timeout=8000)
        except Exception:
            pass
        time.sleep(2.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_06_digital_twin_light.png"))

        # 7. Incident Command Page (1727x893)
        print("Capturing 7: Incident Command Page...")
        page.locator("button:has-text('Incident Command')").first.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_07_incident_command_light.png"))

        # 8. Laptop (1366x768) Overview
        print("Capturing 8: Laptop 1366x768 Overview...")
        ctx_laptop = browser.new_context(viewport={"width": 1366, "height": 768})
        ctx_laptop.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light');")
        p_laptop = ctx_laptop.new_page()
        p_laptop.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        p_laptop.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_08_overview_laptop_1366.png"))

        # 9. Tablet Landscape (1024x768) Overview
        print("Capturing 9: Tablet Landscape 1024x768 Overview...")
        ctx_tab_ls = browser.new_context(viewport={"width": 1024, "height": 768})
        ctx_tab_ls.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light');")
        p_tab_ls = ctx_tab_ls.new_page()
        p_tab_ls.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        p_tab_ls.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_09_overview_tablet_1024.png"))

        # 10. Tablet Landscape (1024x768) Compare Actions (Verify 2-column layout)
        print("Capturing 10: Tablet Landscape 1024x768 Compare Actions...")
        p_tab_ls.locator("button:has-text('Compare Actions')").first.click()
        try:
            p_tab_ls.wait_for_selector("text=Safe, Feasible Actions", timeout=8000)
        except Exception:
            pass
        time.sleep(2.5)
        p_tab_ls.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_10_compare_actions_tablet_1024.png"))

        # 11. Tablet Portrait (768x1024) Overview
        print("Capturing 11: Tablet Portrait 768x1024 Overview...")
        ctx_tab_pt = browser.new_context(viewport={"width": 768, "height": 1024})
        ctx_tab_pt.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light');")
        p_tab_pt = ctx_tab_pt.new_page()
        p_tab_pt.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        p_tab_pt.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_11_overview_tablet_768.png"))

        # 12. Mobile (390x844) Overview
        print("Capturing 12: Mobile 390x844 Overview...")
        ctx_mob = browser.new_context(viewport={"width": 390, "height": 844})
        ctx_mob.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true'); localStorage.setItem('aegisstor_theme', 'light');")
        p_mob = ctx_mob.new_page()
        p_mob.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)
        p_mob.screenshot(path=os.path.join(OUTPUT_DIR, "aurora_repair_12_overview_mobile_390.png"))

        browser.close()
        print("All 12 Aurora Pastel Layout Repair screenshots captured successfully!")

if __name__ == "__main__":
    run()
