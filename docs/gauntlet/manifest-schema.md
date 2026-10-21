# AEGISSTOR GAUNTLET — Run Manifest Schema & Cryptographic Integrity Standard
**Standard:** Prompt 18.0 Part 2 (Reproducible Run Manifests)  
**Schema Version:** `1.0.0`  
**Hashing Algorithm:** SHA-256 (Canonical JSON RFC 8785 representation)  

---

## 1. Manifest Structure & Data Dictionary

Every benchmark run executed by GAUNTLET automatically generates an immutable, versioned manifest persisted in `gauntlet_runs.manifest_json`.

```json
{
  "$schema": "https://aegisstor.internal/schemas/gauntlet-manifest-v1.json",
  "schema_version": "1.0.0",
  "run_id": "grun-20261021175401-c8a7d1",
  "suite_id": "suite-capacity-forecast-v1",
  "suite_version": "1.0.0",
  "device_id": "vol-nvme-tier1-db",
  "dataset_id": "enterprise-telemetry-primary",
  "dataset_provenance": "AEGISSTOR Standard Synthetic Enterprise Telemetry Generator",
  "dataset_license": "Apache-2.0 / Academic Research Use",
  "source_code_revision": "87b20a5",
  "execution_environment": "Python 3.13.14 on win32",
  "random_seed": 42,
  "split_ratios": {
    "train": 0.70,
    "val": 0.15,
    "test": 0.15
  },
  "evaluation_window": {
    "start_time": "2026-10-18T12:00:00Z",
    "end_time": "2026-10-21T12:00:00Z",
    "train_samples": 504,
    "val_samples": 108,
    "test_samples": 109
  },
  "parameters": {
    "horizon_hours": 72,
    "random_seed": 42
  },
  "safety_profile": {
    "physical_mutation_enabled": false,
    "bounded_runtime_seconds": 60,
    "isolated_memory_execution": true
  },
  "created_at_utc": "2026-10-21T17:54:01.120456Z",
  "manifest_sha256": "4fcad8603e25d33553420dc5a3c9582bce56e247619e4d8a40386a5b3366b1cf"
}
```

---

## 2. Cryptographic Hash Calculation Protocol

To guarantee that the manifest hash is stable and verifiable across different operating systems, Python versions, and database engines:

1. **Field Normalization:** The dictionary is serialized with lexicographically sorted keys (`sort_keys=True`) and minimal separators (`separators=(',', ':')`).
2. **Exclusion of the Hash Field:** The target field `manifest_sha256` is omitted during the initial digest computation.
3. **Encoding:** The canonical string is encoded in UTF-8 without byte-order marks (BOM).
4. **Digest:** The SHA-256 algorithm produces a 64-character lowercase hexadecimal string:
   $$\text{SHA-256}(\text{CanonicalJSON}(M)) \to h \in \{0-9, a-f\}^{64}$$
5. **Persistence:** The calculated hash is stored both inside the manifest and as an indexed column `gauntlet_runs.manifest_sha256`.

---

## 3. Security & Secrecy Boundaries

In compliance with Prompt 18.0 Part 14:
* **No Leaked Secrets:** Passwords, API keys, JWT secret keys, and database connection strings are strictly omitted from run manifests.
* **No Unpublished Invention Claims:** Manifests record technical parameters only (e.g. learning rate, quantile alpha, bus threshold); they do not serialize confidential patent claim language.
* **Integrity vs Scientific Truth:** A valid SHA-256 hash proves that the manifest has not been tampered with or modified since execution; it does not replace empirical evaluation or prove causality on its own.
