"""
AEGISSTOR CERBERUS — 10-Step Mission 11 Canonical Verification Script
"""
import urllib.request
import urllib.error
import json
import sys

BASE = 'http://127.0.0.1:8000/api/v1'

def run():
    print("=" * 70)
    print("AEGISSTOR CERBERUS — MISSION 11 END-TO-END DEMO TEST")
    print("=" * 70)

    # 1. Health
    h = json.loads(urllib.request.urlopen(f'{BASE}/health').read().decode())
    print('[1] Health Check:', h['status'])
    assert h['status'] == 'ok'

    # 2. Dataset / Fleet
    devices = json.loads(urllib.request.urlopen(f'{BASE}/devices').read().decode())
    target = devices[0]['id']
    print(f'[2] Loaded {len(devices)} devices. Target: {target}')
    assert len(devices) >= 4

    # 3. Usage & Telemetry
    tel = json.loads(urllib.request.urlopen(f'{BASE}/devices/{target}/telemetry?metric=used_bytes&hours=48').read().decode())
    pts = len(tel.get('timestamps', []))
    print(f'[3] Telemetry: {pts} points retrieved, is_synthetic={tel.get("is_synthetic", True)}')
    assert pts >= 24

    # 4. Capacity Forecast
    fc = json.loads(urllib.request.urlopen(f'{BASE}/devices/{target}/forecasts?target_metric=used_bytes&model_type=lightgbm_quantile&horizon_hours=24').read().decode())
    q50_start = fc['q50'][0]
    q50_end = fc['q50'][-1]
    print(f'[4] Forecast: 24h q50 start={q50_start:,.0f} B, end={q50_end:,.0f} B')
    assert len(fc['q50']) == 24

    # 5. Risk Assessment
    risk = json.loads(urllib.request.urlopen(f'{BASE}/devices/{target}/risks').read().decode())
    rw = risk.get('runway_hours_estimate', 0)
    lvl = risk.get('risk_level', 'NOMINAL')
    contribs = len(risk.get('risk_contributors', []))
    print(f'[5] Risk Assessment: Runway={rw} hrs, Level={lvl}, Contributors={contribs}')
    assert contribs > 0

    # 6. What-If Scenario
    sim_req = urllib.request.Request(
        f'{BASE}/scenarios',
        data=json.dumps({
            'device_id': target,
            'name': 'Cold Tiering 400GB Test',
            'action_type': 'TIER_COLD_DATA',
            'parameters': {'volume_to_tier_gb': 400.0}
        }).encode(),
        headers={'Content-Type': 'application/json'}
    )
    sim = json.loads(urllib.request.urlopen(sim_req).read().decode())
    sim_id = sim.get('id') or sim.get('scenario_id')
    print(f'[6] Scenario Simulated: id={sim_id}, action={sim.get("action_type")}')
    assert sim_id is not None

    # 7. Recommendations
    recs = json.loads(urllib.request.urlopen(f'{BASE}/devices/{target}/recommendations').read().decode())
    top_act = recs[0]['action_type'] if recs else 'None'
    print(f'[7] Recommendations: count={len(recs)}, top={top_act}')
    assert len(recs) > 0

    # 8. Persist / Overview State
    ov = json.loads(urllib.request.urlopen(f'{BASE}/overview').read().decode())
    tot_tb = ov['total_capacity_bytes'] / (1024**4)
    print(f'[8] Overview State: Total={tot_tb:.2f} TB, Monitored Devices={ov["monitored_device_count"]}')
    assert ov['monitored_device_count'] >= 4

    # 9. Refresh Consistency
    tel_refresh = json.loads(urllib.request.urlopen(f'{BASE}/devices/{target}/telemetry?metric=used_bytes&hours=48').read().decode())
    pts_refresh = len(tel_refresh.get('timestamps', []))
    assert pts_refresh == pts
    print(f'[9] Refresh Consistency: {pts_refresh} points match original {pts} points.')

    # 10. Invalid request error state
    try:
        urllib.request.urlopen(f'{BASE}/devices/non-existent-device-xyz/telemetry')
        print('[10] FAILED: Expected 404 error')
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f'[10] Invalid Request Handled Gracefully: HTTP {e.code} ({e.reason})')
        assert e.code == 404

    print("=" * 70)
    print("ALL 10 MISSION 11 DEMONSTRATION STEPS VERIFIED (100% PASS)")
    print("=" * 70)

if __name__ == '__main__':
    run()
