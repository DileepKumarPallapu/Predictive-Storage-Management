import os
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"C:\Users\dilee\.gemini\antigravity\brain\ca01d69b-34d0-4861-9b05-3a2b2ae733c4\screenshots"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH if os.path.exists(EDGE_PATH) else None,
            headless=True
        )
        context = browser.new_context(viewport={"width": 1600, "height": 950})
        context.add_init_script("localStorage.setItem('aegisstor_onboarding_completed', 'true');")
        page = context.new_page()

        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        time.sleep(2)

        # Switch to Replay
        source_select = page.locator("select[aria-label='Select Operating Data Mode']")
        source_select.select_option("replay")
        time.sleep(2)

        # Select empty state option
        trace_select = page.locator("select[aria-label='Select Storage Trace Dataset']")
        trace_select.select_option("__unload__")
        time.sleep(2)

        empty_shot = os.path.join(OUTPUT_DIR, "zero_mock_04_replay_empty_state.png")
        page.screenshot(path=empty_shot)
        print(f"Captured empty replay state: {empty_shot}")

        # Switch back to SNIA trace
        trace_select.select_option("snia_enterprise_block_trace.csv")
        time.sleep(1)

        # Switch back to Demo mode
        source_select.select_option("demo")
        time.sleep(1)

        browser.close()

if __name__ == "__main__":
    run()
