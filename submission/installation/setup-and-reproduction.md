# Submission Deliverable: Setup, Installation & Reproduction Guide

**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document:** SUBMISSION-INSTALL-001  

---

## 1. System Requirements

- **Python Runtime:** Python 3.10 to 3.13 (64-bit).
- **Node.js Runtime:** Node.js v18.0+ and npm 9.0+.
- **Supported Operating Systems:** Windows 10/11, Ubuntu 20.04+, Debian 11+, macOS 12+.
- **Hardware Footprint:** Minimal ($< 150\,\text{MB}$ RAM for full backend + frontend operation; no GPU required).

---

## 2. Installation & Verification Commands

### Step 1: Environment Setup
```bash
# Clone the project repository
git clone <repository_url> aegisstor
cd aegisstor

# Set up Python virtual environment
python -m venv env
# Windows:
.\env\Scripts\activate
# Linux/macOS:
source env/bin/activate

# Install locked dependencies
pip install -r backend/requirements.txt
```

### Step 2: Run Full Automated Test Suite (120 Tests)
```bash
python -m pytest backend/tests -v
```
*Expected Result:* `120 passed in ~41s (100% pass rate)`.

### Step 3: Run the 20-Step Canonical Demonstration Workflow
```bash
python scripts/run_canonical_demo.py
```
*Expected Result:* All 20 steps execute successfully with matching cryptographic SHA-256 fingerprint.

### Step 4: Frontend Development Server
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
*Access the live Ember Noir interface at `http://127.0.0.1:5173`.*

---

## 3. Safe Shutdown Commands

- To stop the backend or frontend: press `Ctrl + C` in the respective terminal.
- To deactivate the Python environment: run `deactivate`.
