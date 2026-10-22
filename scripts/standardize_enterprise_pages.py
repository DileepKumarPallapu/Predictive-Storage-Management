import os
import glob
import re

PAGES_DIR = "frontend/src/pages"

def clean_page(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. Replace glass-panel with titan-card
    content = re.sub(r'\bglass-panel\b', 'titan-card', content)

    # 2. Replace rounded-2xl with rounded-lg in cards/panels
    content = re.sub(r'\brounded-2xl\b', 'rounded-lg', content)
    content = re.sub(r'\brounded-3xl\b', 'rounded-xl', content)

    # 3. Replace shadow-glow-* with shadow-xs
    content = re.sub(r'shadow-glow-[a-zA-Z0-9_-]+', 'shadow-xs', content)
    content = re.sub(r'shadow-glow', 'shadow-xs', content)

    # 4. Clean up header icon container styles if they had old vermilion/purple classes
    # e.g., bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/30 text-[var(--accent-primary)]
    content = re.sub(
        r'bg-\[var\(--accent-primary\)\]/15\s+border\s+border-\[var\(--accent-primary\)\]/30\s+flex\s+items-center\s+justify-center\s+text-\[var\(--accent-primary\)\]\s+shadow-xs',
        'bg-[var(--accent)] text-white flex items-center justify-center shadow-xs',
        content
    )
    content = re.sub(
        r'bg-\[var\(--accent\)\]/15\s+border\s+border-\[var\(--accent\)\]/30\s+flex\s+items-center\s+justify-center\s+text-\[var\(--accent\)\]\s+shadow-xs',
        'bg-[var(--accent)] text-white flex items-center justify-center shadow-xs',
        content
    )

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {os.path.basename(filepath)}")
    else:
        print(f"No changes needed for {os.path.basename(filepath)}")

def main():
    pages = glob.glob(os.path.join(PAGES_DIR, "*.tsx"))
    for p in pages:
        clean_page(p)

if __name__ == "__main__":
    main()
