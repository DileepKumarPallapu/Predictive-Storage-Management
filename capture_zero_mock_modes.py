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
        context = browser.new_context(viewport={"width": 1600, "height": 950})
        # Bypass first-time tour modal
        context.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true');")
        
        page = context.new_page()

        print("Navigating to http://127.0.0.1:5173...")
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)

        # 1. Capture default (Demo mode)
        demo_shot = os.path.join(OUTPUT_DIR, "zero_mock_01_demo_mode.png")
        page.screenshot(path=demo_shot)
        print(f"Captured demo mode: {demo_shot}")

        # 2. Switch to Replay mode
        source_select = page.locator("select[aria-label='Select Operating Data Mode']")
        source_select.select_option("replay")
        time.sleep(2)

        # Verify Replay bar is visible and interact
        replay_bar = page.locator("section[aria-label='Storage Trace Replay Controls']")
        if replay_bar.count() > 0:
            print("Replay control bar verified!")
            # Click step forward twice
            step_btn = page.locator("button[aria-label='Step Forward']")
            if step_btn.count() > 0 and step_btn.is_enabled():
                step_btn.click()
                time.sleep(0.5)
                step_btn.click()
                time.sleep(0.5)

        replay_shot = os.path.join(OUTPUT_DIR, "zero_mock_02_replay_mode.png")
        page.screenshot(path=replay_shot)
        print(f"Captured replay mode: {replay_shot}")

        # 3. Switch to Live mode
        source_select.select_option("live")
        time.sleep(2)

        live_shot = os.path.join(OUTPUT_DIR, "zero_mock_03_live_mode.png")
        page.screenshot(path=live_shot)
        print(f"Captured live mode: {live_shot}")

        browser.close()
        print("All mode screenshots captured successfully!")

if __name__ == "__main__":
    run()
