"""
AEGISSTOR Research Benchmark Runner (Prompt 17.0 Phase 6 & Phase 7)
Executes Baselines A-F and Ablations 1-7 against real database devices
and serializes empirical results to JSON and markdown for publication.
"""
import sys
import os
import json
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models.entities import Device
from app.services.research_benchmark_engine import ResearchBenchmarkEngine

def main():
    print("[*] Initializing AEGISSTOR Empirical Benchmark Execution...")
    db = SessionLocal()
    try:
        device = db.query(Device).first()
        if not device:
            print("[!] No devices found in database. Exiting.")
            return

        print(f"[*] Targeting Device: {device.id} ({device.name})")

        # 1. Run Baselines
        print("[*] Running Baselines A through F...")
        baselines_data = ResearchBenchmarkEngine.run_all_baselines(db, device.id, horizon_hours=72)
        print(f"    Baselines count: {len(baselines_data['baselines'])}")

        # 2. Run Ablations
        print("[*] Running Ablations 1 through 7...")
        ablations_data = ResearchBenchmarkEngine.run_ablation_study(db, device.id, horizon_hours=72)
        print(f"    Ablations count: {len(ablations_data)}")

        # Combine payload
        benchmark_results = {
            "device_id": device.id,
            "device_name": device.name,
            "baselines_study": baselines_data,
            "ablations_study": ablations_data
        }

        # Save JSON output
        out_json_path = backend_dir.parent / "docs" / "industry-readiness" / "benchmark_empirical_raw.json"
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_results, f, indent=2)
        print(f"[+] Serialized raw empirical benchmark output to {out_json_path}")

        print("\n================= BASELINE EVALUATION SUMMARY =================")
        print(f"{'Baseline / Method':<38} | {'Lead Time':<10} | {'FAR':<6} | {'Miss':<6} | {'Risk':<6} | {'Feasible?'}")
        print("-" * 78)
        for b in baselines_data["baselines"]:
            lt = f"{b['warning_lead_time_hours']}h" if b['warning_lead_time_hours'] is not None else "N/A"
            print(f"{b['name']:<38} | {lt:<10} | {b['false_alarm_rate']:<6.2f} | {b['missed_breach_rate']:<6.2f} | {b['residual_risk_score']:<6.2f} | {b.get('lead_time_feasible', True)}")

        print("\n================== ABLATION STUDY SUMMARY ==================")
        print(f"{'Ablation Variant':<48} | {'Selected Action':<35} | {'Score':<6} | {'Residual Risk'}")
        print("-" * 105)
        for a in ablations_data:
            act_name = a['recommended_action'][:33] if a.get('recommended_action') else "None (Disqualified)"
            score_str = f"{a['utility_score']:<6.3f}" if a.get('utility_score') is not None else "N/A   "
            print(f"{a['ablation_name']:<48} | {act_name:<35} | {score_str} | {a['estimated_residual_risk']:<6.2f}")

        print("\n[+] Benchmark execution successfully completed.")

    finally:
        db.close()

if __name__ == "__main__":
    main()
