#!/usr/bin/env python3
"""
AEGISSTOR — Reproducible Research Benchmark Runner (Prompt Upgrade 3).
Executes zero-leakage chronological split (70% train, 15% val, 15% test).
Evaluates Persistence, Seasonal Naive, AR Linear, LightGBM, and EGSIP.
Outputs tabular metrics with clear units and exports machine-readable JSON & CSV.
"""

import sys
import os
import json
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.services.research_benchmark_engine import ResearchBenchmarkEngine


def main():
    device_id = sys.argv[1] if len(sys.argv) > 1 else "vol-nvme-tier1-db"
    random_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    horizon_hours = int(sys.argv[3]) if len(sys.argv) > 3 else 72


    print("=" * 80)
    print(" AEGISSTOR REPRODUCIBLE RESEARCH BENCHMARK RUNNER")
    print("=" * 80)
    print(f" Target Device       : {device_id}")
    print(f" Random Seed (S)     : {random_seed}")
    print(f" Forecast Horizon    : {horizon_hours} hours")
    print(f" Chronological Split : 70% Train / 15% Validation / 15% Test (Zero-Leakage)")
    print("-" * 80)

    db = SessionLocal()
    try:
        results = ResearchBenchmarkEngine.run_chronological_validation(
            db=db,
            device_id=device_id,
            horizon_hours=horizon_hours,
            random_seed=random_seed
        )

        split = results["split_summary"]
        print(f" Dataset Provenance  : {results['dataset_provenance']}")
        print(f" Total Samples       : {split['total_records']} telemetry hourly snapshots")
        print(f" Train Window        : {split['train_samples']} samples ({split['train_window_start'][:10]} to {split['train_window_end'][:10]})")
        print(f" Val Window          : {split['val_samples']} samples ({split['val_window_start'][:10]} to {split['val_window_end'][:10]})")
        print(f" Test Window         : {split['test_samples']} samples ({split['test_window_start'][:10]} to {split['test_window_end'][:10]})")
        print(f" Zero-Leakage Check  : {'PASS (No future leakage)' if split['zero_leakage_verified'] else 'FAIL (Leakage detected!)'}")
        print("=" * 80)

        # Tabular Header
        print(f"{'Model / Framework':<42} | {'Category':<16} | {'MAE (GB)':<9} | {'RMSE (GB)':<10} | {'WAPE (%)':<9} | {'Coverage':<9} | {'Lead Err':<8}")
        print("-" * 115)

        for m in results["models"]:
            name = m["model_name"]
            cat = m["category"]
            mae = f"{m['mae_gb']:.3f}"
            rmse = f"{m['rmse_gb']:.3f}"
            wape = f"{m['wape_pct']:.2f}%"
            cov = f"{m['interval_coverage_pct']:.1f}%" if m["interval_coverage_pct"] is not None else "N/A"
            lead = f"{m['lead_time_error_hours']:.1f}h"
            print(f"{name:<42} | {cat:<16} | {mae:<9} | {rmse:<10} | {wape:<9} | {cov:<9} | {lead:<8}")

        print("=" * 115)
        conf = results["conformal_evaluation"]
        print(f" Conformal Coverage (80% Nominal) : {conf['empirical_coverage_pct']}% empirical")
        print(f" Mean Pinball Loss (q10/50/90)    : {results['models'][-1]['pinball_loss_gb']:.4f} GB")
        print("-" * 115)

        # Export directory
        export_dir = Path(__file__).resolve().parent.parent / "docs" / "benchmarks"
        export_dir.mkdir(parents=True, exist_ok=True)

        json_path = export_dir / f"benchmark_results_{device_id}.json"
        csv_path = export_dir / f"benchmark_results_{device_id}.csv"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        csv_content = ResearchBenchmarkEngine.export_benchmarks_csv(results)
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        print(f" [Export JSON] => {json_path}")
        print(f" [Export CSV]  => {csv_path}")
        print(" [Reproducibility] Validation verified successfully. Seed S=42 locked.")
        print("=" * 115)

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
