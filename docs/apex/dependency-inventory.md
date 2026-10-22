# AEGISSTOR APEX — Dependency Inventory & Supply Chain Audit (Phase 0)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** APEX-DEP-001  
**Audit Scope:** Backend (`requirements.txt`), Frontend (`package.json`), and System Runtimes  

---

## 1. Runtime Environment Specifications

| Environment Component | Detected Version | Minimum Required | Status |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 11 Enterprise (win32) | Windows 10 / Linux 5.15+ | Supported |
| **Python Runtime** | 3.13.14 (64-bit) | 3.10.0 | Fully Compatible |
| **Node.js Runtime** | v24.14.1 | v18.0.0 | Fully Compatible |
| **npm Package Manager** | 11.11.0 | 9.0.0 | Fully Compatible |
| **Vite Build Engine** | 8.3.5 | 5.0.0 | Optimized |
| **TypeScript Compiler** | 6.0.3 | 5.0.0 | Strict Mode Enforced |

---

## 2. Backend Dependency Inventory (`backend/requirements.txt`)

| Package Name | Specified Version | Runtime Purpose | Security / Advisory Status |
| :--- | :--- | :--- | :--- |
| `fastapi` | `>=0.110.0` | High-performance asynchronous REST API framework | Clean. Starlette testclient deprecation warning noted for future migration to `httpx2`. |
| `uvicorn` | `>=0.28.0` | Asynchronous ASGI production server | Clean. |
| `pydantic` | `>=2.6.0` | Schema validation and data modeling (v2 Core) | Clean. High performance Rust core. |
| `pydantic-settings` | `>=2.2.0` | Environment configuration management | Clean. |
| `sqlalchemy` | `>=2.0.28` | Relational ORM and database abstraction layer | Clean. SQLAlchemy 2.0 type mapping enforced. |
| `alembic` | `>=1.13.0` | Relational database schema migrations | Clean. |
| `pandas` | `>=2.2.0` | Time series feature extraction and tabular forensics | Clean. |
| `numpy` | `>=1.26.0` | Vectorized numerical linear algebra and matrices | Clean. |
| `scikit-learn` | `>=1.4.0` | Machine learning baselines, Ridge regression, metrics | Clean. |
| `lightgbm` | `>=4.3.0` | Gradient-boosted decision trees for non-linear forecasting | Clean. Fast native C++ backend. |
| `pyjwt` | `>=2.9.0` | JSON Web Token encoding and verification | Clean. Cryptographic signature validation. |
| `bcrypt` | `>=4.1.0` | Salted password hashing (PBKDF2 fallback) | Clean. |
| `prometheus-client` | `>=0.20.0` | Standard Prometheus metric exposition (`/metrics`) | Clean. |
| `pytest` | `>=8.0.0` | Unit and integration test execution harness | Clean. |
| `httpx` | `>=0.27.0` | Asynchronous HTTP client for test suite | Clean. |
| `python-multipart` | `>=0.0.9` | Form data parsing for file uploads | Clean. Patched against DoS CVEs. |

---

## 3. Frontend Dependency Inventory (`frontend/package.json`)

### Production Dependencies
| Package Name | Specified Version | Runtime Purpose |
| :--- | :--- | :--- |
| `react` | `^19.3.1` | Modern React UI component framework |
| `react-dom` | `^19.3.1` | React DOM renderer |
| `lucide-react` | `^1.61.0` | High-clarity SVG icon set |
| `clsx` | `^2.1.1` | Conditional CSS class constructor |
| `tailwind-merge` | `^3.7.0` | Conflict-free Tailwind CSS utility merger |

### Development Dependencies
| Package Name | Specified Version | Purpose |
| :--- | :--- | :--- |
| `typescript` | `~6.0.3` | Static type checking and compiler |
| `vite` | `^8.3.4` | Development bundler and production packaging |
| `@vitejs/plugin-react` | `^6.1.2` | Fast refresh and React compiler JSX transformation |
| `tailwindcss` | `^3.4.17` | Utility-first CSS engine with Ember Noir theme variables |
| `postcss` | `^8.5.31` | CSS transformation engine |
| `autoprefixer` | `^10.6.1` | Cross-browser vendor prefixing |
| `oxlint` | `^1.88.0` | Ultra-fast Rust-based static code linter |
| `@types/react` | `^19.3.0` | TypeScript definitions for React |
| `@types/react-dom` | `^19.3.0` | TypeScript definitions for React DOM |
| `@types/node` | `^24.19.2` | TypeScript definitions for Node runtimes |

---

## 4. Supply Chain & Vulnerability Evaluation

- **Zero Critical Vulnerabilities:** Neither npm audit nor backend requirements trigger active CVE advisories.
- **Dependency Minimization:** Frontend deliberately avoids heavyweight chart libraries (such as bloated D3 distributions or Recharts 2.x which suffer from React 19 hydration issues); all charts are built with lightweight, zero-dependency, mathematically verified SVG/Canvas rendering primitives.
- **Lockfile Hygiene:** All dependencies resolve cleanly without peer dependency conflicts.
