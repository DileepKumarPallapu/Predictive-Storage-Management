# AEGISSTOR FORGE — Integration Defects & Resolution Audit (Release Candidate 21.0)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-DEF-001  
**Integrity Standard:** Zero Hidden Defects — Transparent Audit  

---

## 1. Resolution of Historical Integration Defects

During earlier development phases and APEX Prompt 20.0, several subtle integration and environment defects were diagnosed and systematically fixed:

| Defect ID | Component | Root Cause | Impact | Resolution in Release Candidate | Verification Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-INT-001** | Database Engine | SQLite relative path (`sqlite:///./aegisstor.db`) resolved relative to invoking shell CWD rather than repository root. | Running scripts or tests from root created empty 0-byte database replicas. | Hardened `database.py` with absolute path resolution targeting `backend/aegisstor.db` across all execution contexts. | `scripts/verify_apex_release_gate.py` (Step 1) |
| **DEF-INT-002** | Digital Twin Simulator | `simulate_scenario` assumed `timestamps` entries were `datetime` objects; string ISO timestamps triggered `TypeError: can only concatenate str to str`. | Simulation crashed when fed serialized JSON forecast contracts. | Added automatic `datetime.fromisoformat()` parsing with UTC timezone normalization and ISO string formatting on return. | `scripts/verify_apex_release_gate.py` (Step 11) |
| **DEF-INT-003** | Pytest Tooling | Workspace root lacked pytest configuration file; running `pytest` without `PYTHONPATH` raised `ModuleNotFoundError: No module named 'app'`. | Root-level test execution failed. | Added root `pytest.ini` declaring `pythonpath = backend` and strict asyncio mode. | `python -m pytest backend/tests` from root |
| **DEF-INT-004** | Safety Configuration | `Settings` object lacked explicit `PHYSICAL_MUTATION_DISABLED` attribute alias. | Release gate assertion failed during safety boundary check. | Explicitly added `PHYSICAL_MUTATION_DISABLED: bool = True` alongside `SHADOW_MODE_ENABLED` in `config.py`. | `scripts/verify_apex_release_gate.py` (Step 17) |
| **DEF-INT-005** | Audit Logging | `AuditLog` entity uses `details_json` instead of generic `details` attribute. | Gate script initialization failed on audit table insert. | Fixed kwargs in seeder and verification harness to use `details_json`. | `scripts/verify_apex_release_gate.py` (Step 13) |

---

## 2. Active Environmental & Architectural Invariants (Not Defects)

1. **Linux Block Device Telemetry (`/sys/block`):** Native Windows hosts do not provide Linux sysfs pseudo-filesystems. The collector cleanly falls back to deterministic synthetic generation and recorded replay traces with visible UI status badges.
2. **Physical Storage Mutation Barrier:** The platform intentionally disallows real host disk mutations (`PHYSICAL_MUTATION_DISABLED = True`), routing all operations to the verified Digital Twin sandbox.
3. **Starlette Deprecation Notice:** Starlette test client logs an informational deprecation warning regarding future `httpx2` migration. Test execution remains 100% green.
