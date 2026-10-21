from fastapi import APIRouter
from app.api.v1 import (
    endpoints_health,
    endpoints_overview,
    endpoints_devices,
    endpoints_telemetry,
    endpoints_forecasts,
    endpoints_risks,
    endpoints_scenarios,
    endpoints_recommendations,
    endpoints_experiments,
    endpoints_reliability,
    endpoints_alerts,
    endpoints_datasets,
    endpoints_settings,
    endpoints_auth,
    endpoints_metrics,
    endpoints_omega,
    endpoints_jurassic,
    endpoints_phoenix,
    endpoints_atlas,
    endpoints_oracle,
    endpoints_evidence_gated
)

api_router = APIRouter()

api_router.include_router(endpoints_health.router, tags=["Health & System"])
api_router.include_router(endpoints_auth.router, tags=["Authentication & Access Control"])
api_router.include_router(endpoints_metrics.router, tags=["Prometheus Telemetry"])
api_router.include_router(endpoints_overview.router, tags=["Overview & Dashboard"])
api_router.include_router(endpoints_devices.router, tags=["Devices & Storage Fleet"])
api_router.include_router(endpoints_telemetry.router, tags=["Telemetry"])
api_router.include_router(endpoints_forecasts.router, tags=["Forecasting Engine"])
api_router.include_router(endpoints_risks.router, tags=["Risk & Reserve Runway"])
api_router.include_router(endpoints_scenarios.router, tags=["Digital Twin & Simulator"])
api_router.include_router(endpoints_recommendations.router, tags=["Interventions & Governance"])
api_router.include_router(endpoints_experiments.router, tags=["Experiment Workbench"])
api_router.include_router(endpoints_reliability.router, tags=["Model Reliability & Calibration"])
api_router.include_router(endpoints_alerts.router, tags=["Alerts & Incidents"])
api_router.include_router(endpoints_datasets.router, tags=["Datasets & Provenance"])
api_router.include_router(endpoints_settings.router, tags=["Settings & Audit"])
api_router.include_router(endpoints_omega.router, tags=["AEGISSTOR Omega Intelligence"])
api_router.include_router(endpoints_jurassic.router, tags=["AEGISSTOR Jurassic Resilience Lab"])
api_router.include_router(endpoints_phoenix.router, tags=["AEGISSTOR Phoenix Incident Orchestration"])
api_router.include_router(endpoints_atlas.router, tags=["AEGISSTOR Atlas Reality Calibration & Evidence Intelligence"])
api_router.include_router(endpoints_oracle.router, tags=["AEGISSTOR Oracle Workload Attribution & Bottleneck Intelligence"])
api_router.include_router(endpoints_evidence_gated.router, tags=["Research Contribution & Benchmarks (Prompt 17.0)"])


