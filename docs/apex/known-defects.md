# AEGISSTOR APEX — Known Defects, Warnings & Environmental Constraints (Phase 0)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** APEX-DEF-001  
**Audit Standard:** Strict Transparency — Zero Concealment  

---

## 1. Active Defects & Warnings Inventory

| Defect ID | Severity | Category | Description | Mitigation / Resolution Status |
| :--- | :--- | :--- | :--- | :--- |
| **DEF-001** | Low (Cosmetic) | Scripts | `scripts/seed_demo_data.py` contains UTF-8 character encoding corruption (`?"`) in terminal print banner. | Resolved in APEX Phase 1 via string cleanup. |
| **DEF-002** | Low (Tooling) | Pytest Configuration | Running `pytest` from workspace root without `PYTHONPATH` throws `ModuleNotFoundError: No module named 'app'`. | Resolved in APEX Phase 1 by creating a root `pytest.ini` with `pythonpath = backend`. |
| **DEF-003** | Low (Linter) | Frontend Oxlint | 195 unused import and variable warnings across frontend TypeScript pages (e.g. unused `Sparkles` in `ContextualHelp.tsx`, unused icons in `PageOracleIntelligence.tsx`). Zero compile errors. | Cleaned up in APEX Phase 3/4. |
| **DEF-004** | Info (Deprecation) | Backend Dependencies | Starlette testclient issues `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`. | Documented for future minor upgrade; tests execute with 100% pass rate. |
| **DEF-005** | Environmental Constraint | Operating System | Physical Linux block device inspection (`/sys/block/*`, `smartctl`) is unavailable on native Windows host. | Architectural invariant: cleanly falls back to synthetic telemetry generation and recorded trace replay with explicit UI mode indicators. |
| **DEF-006** | Architectural Constraint | Safety Guard | Autonomous physical disk mutation is intentionally blocked by `PHYSICAL_MUTATION_DISABLED = True`. | Not a defect: essential safety guard preserving host storage integrity. |

---

## 2. Risk & Impact Analysis

None of the identified defects impact core prediction accuracy, risk engine safety, database integrity, or test execution. The core computational pathways for capacity forecasting, uncertainty estimation, digital twin simulation, and evidence-gated planning operate with 100% deterministic repeatability.
