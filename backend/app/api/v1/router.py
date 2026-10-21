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
    endpoints_omega
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
