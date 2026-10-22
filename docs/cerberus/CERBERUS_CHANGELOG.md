# AEGISSTOR CERBERUS — Master Changelog & Defect Repair History

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** CERBERUS-CHANGELOG-001  

---

## 1. Summary of Changes & Fixes

| Change ID | Target File | Issue Addressed | Technical Modification | Test Verification |
| :---: | :--- | :--- | :--- | :--- |
| **CHG-001** | `backend/app/database.py` | SQLite relative path created 0-byte database when invoked outside `backend/` | Added absolute directory targeting: `db_path = os.path.join(backend_dir, "aegisstor.db")` | `python scripts/test_cerberus_demo.py` (Step 2) |
| **CHG-002** | `backend/app/simulator/digital_twin.py` | String ISO timestamps caused `TypeError: can only concatenate str to str` on line 197 | Added `datetime.fromisoformat()` parsing with UTC normalization and serialized ISO return strings | `python scripts/run_canonical_demo.py` (Step 14) |
| **CHG-003** | `backend/app/config.py` | Pydantic Settings lacked `PHYSICAL_MUTATION_DISABLED` alias attribute | Added `PHYSICAL_MUTATION_DISABLED: bool = True` alongside `SHADOW_MODE_ENABLED` | `python scripts/test_cerberus_demo.py` (Step 20) |
| **CHG-004** | `pytest.ini` | Root-level pytest execution failed with `ModuleNotFoundError: No module named 'app'` | Created root `pytest.ini` with `pythonpath = backend` and strict asyncio mode | `python -m pytest backend/tests` from root |
| **CHG-005** | `scripts/seed_demo_data.py` | Console character encoding glitch (`?"`) in terminal output banner | Corrected UTF-8 string encoding to standard ASCII hyphen | `python scripts/seed_demo_data.py` |
| **CHG-006** | `scripts/verify_apex_release_gate.py` | Master 17-step release gate verification script | Automated end-to-end slice, cryptographic hashing, and physical safety barrier assertion | `python scripts/verify_apex_release_gate.py` (17/17 passed) |
| **CHG-007** | `scripts/run_canonical_demo.py` | Canonical 20-step demonstration workflow harness | Automated complete end-to-end user journey with bitwise reproduction parity check | `python scripts/run_canonical_demo.py` (20/20 passed) |
| **CHG-008** | `scripts/test_cerberus_demo.py` | Mission 11 10-step demonstration verification script | Validated live API endpoints, telemetry retrieval, quantile forecasting, scenario simulation, and 404 error handling | `python scripts/test_cerberus_demo.py` (10/10 passed) |
| **CHG-009** | `docs/cerberus/` | Comprehensive CERBERUS audit, test report, runbook, checklist, and changelog suite | Authored 5 authoritative operational documents for examiner review | Document audit |
