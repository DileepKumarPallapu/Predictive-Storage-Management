# AEGISSTOR — End-to-End System Architecture Map
**Document**: Architecture Map & Component Interactions  
**Standard**: C4 Model Architecture Specification (Level 1 System Context & Level 2 Containers)  
**Date**: October 2026  

---

## 1. System Context Diagram

```mermaid
flowchart TD
    User([Storage Administrator / SRE / Researcher])
    
    subgraph AEGISSTOR Platform
        UI[Ember Noir Single-Page Application\nReact 19 + TypeScript + Vite]
        API[FastAPI REST API Gateway\nUvicorn ASGI Server]
        
        subgraph Core Analytics Services
            ML[Quantile ML Forecaster & Calibrator]
            RISK[Fleet Risk & Reserve Runway Engine]
            TWIN[Storage Resilience Digital Twin]
            OMEGA[Omega Topology & Contention Graph]
            ORACLE[Oracle Workload Forensics & Attribution]
            ATLAS[Atlas Reality Calibration & Evidence Gating]
            PHOENIX[Phoenix Safe Incident Orchestrator]
            JURASSIC[Jurassic Resilience Stress Lab]
        end
        
        DB[(Relational Storage & Ledger\nSQLite / PostgreSQL)]
    end
    
    StorageEnv[Enterprise Multi-Tier Storage Hardware\nNVMe SSDs, SAS HDD, Flash Controllers]

    User <-->|HTTPS / Web Interface (Ctrl+K)| UI
    UI <-->|REST API + JWT Bearer| API
    
    API <--> ML
    API <--> RISK
    API <--> TWIN
    API <--> OMEGA
    API <--> ORACLE
    API <--> ATLAS
    API <--> PHOENIX
    API <--> JURASSIC
    
    ML & RISK & TWIN & OMEGA & ORACLE & ATLAS & PHOENIX & JURASSIC <--> DB
    
    StorageEnv -.->|Read-Only Ingest / Telemetry Agent| API
```

---

## 2. Component Layering & Dependencies

### Layer 1: Presentation & User Experience (`frontend/src/`)
- **Shell**: `App.tsx` (dynamic routing, `React.lazy` code splitting, Ember Noir visual design tokens).
- **Global Contexts**: `PresentationModeContext.tsx` (Guided vs Expert operational modes).
- **Navigation**: `Sidebar.tsx`, `TopBar.tsx`, `CommandPalette.tsx` (`Ctrl+K` universal keyboard palette).
- **Performance**: `FlowstatePageSkeleton.tsx`, `utils/decimation.ts` (Min/Max bucket downsampling).
- **Client Cache**: `api/client.ts` (in-memory TTL query cache with in-flight deduplication).

### Layer 2: API Gateway & Security (`backend/app/api/`)
- Enforces JWT Bearer Token validation and Role-Based Access Control (RBAC).
- Request tracing middleware (`X-Request-ID`, structured process timing logs).
- 14 modular routers mounted cleanly under `/api/v1/`.

### Layer 3: Mathematical & Machine Learning Engines (`backend/app/ml/`)
- **`models.py`**: Quantile drift-seasonal regressions ($q_{10}, q_{50}, q_{90}$), tail latency physics ($Q^{1.3}$).
- **`calibration.py`**: Conformal prediction empirical coverage validation, pinball loss evaluation.

### Layer 4: Storage Intelligence & Governance Services (`backend/app/services/`)
- **`digital_twin.py`**: Isolated sandbox simulating migration, tiering, compression, and throttling.
- **`risk_engine.py`**: Reserve runway hours and breach probability estimator.
- **`fleet_topology_service.py`**: Multi-device backplane dependency and failure propagation.
- **`atlas/`**: Reality calibration, held-out validation, sim-to-real discrepancy scoring.
- **`oracle/`**: Direct measurement, aggregate reconciliation with residual delta, and falsifiable hypothesis management.
- **`phoenix/`**: Safe incident recovery runbooks, policy validation, and recovery verification.
- **`jurassic/`**: Resilience lab testing anomalous workloads and telemetry corruption.
- **`outcome_ledger.py`**: Immutable audit ledger chaining decisions with SHA-256 hashes.

### Layer 5: Data Persistence (`backend/app/models/entities.py`, `database.py`)
- Standardized SQLAlchemy ORM entities with comprehensive composite indexes (`idx_device_timestamp`, `idx_oracle_tel_dev_ts`).
- Database abstraction supporting local development (`sqlite:///./aegisstor.db`) and production cloud databases (`postgresql://`).
