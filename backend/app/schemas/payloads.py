from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Health & System
class SystemHealth(BaseModel):
    status: str
    version: str
    mode: str
    database: str
    collector_status: str
    models_loaded: int
    timestamp: datetime

class ModeChangeRequest(BaseModel):
    mode: str = Field(..., description="Operating mode: demo, replay, live")

# Devices
class DeviceBase(BaseModel):
    id: str
    name: str
    tier: str
    media_type: str
    total_capacity_bytes: int
    warning_threshold_pct: float
    critical_threshold_pct: float
    max_acceptable_latency_ms: float
    min_free_reserve_pct: float
    status: str
    workload_profile: str

class DeviceSummary(DeviceBase):
    current_used_bytes: int
    current_utilization_pct: float
    current_read_iops: float
    current_write_iops: float
    current_latency_p95_ms: float
    runway_hours_estimate: float
    risk_level: str

class ThresholdsUpdate(BaseModel):
    warning_threshold_pct: Optional[float] = None
    critical_threshold_pct: Optional[float] = None
    max_acceptable_latency_ms: Optional[float] = None
    min_free_reserve_pct: Optional[float] = None

# Telemetry
class TelemetryPoint(BaseModel):
    timestamp: datetime
    used_bytes: int
    free_bytes: int
    utilization_pct: float
    read_iops: float
    write_iops: float
    throughput_mb_s: float
    latency_p95_ms: float
    queue_depth: float
    is_synthetic: bool

class TelemetryResponse(BaseModel):
    device_id: str
    metric: str
    total_capacity_bytes: int
    is_synthetic: bool
    timestamps: List[datetime]
    values: List[float]
    units: str
    missing_intervals: List[Dict[str, Any]] = []

class TelemetryIngestItem(BaseModel):
    timestamp: datetime
    used_bytes: int
    free_bytes: int
    read_iops: float = 0.0
    write_iops: float = 0.0
    throughput_mb_s: float = 0.0
    latency_p95_ms: float = 0.0
    queue_depth: float = 1.0
    is_synthetic: bool = True

class TelemetryIngestBatch(BaseModel):
    device_id: str
    records: List[TelemetryIngestItem]

# Forecasts
class ForecastResponse(BaseModel):
    device_id: str
    target_metric: str
    model_name: str
    forecast_horizon_hours: int
    generated_at: datetime
    historical_cutoff: datetime
    timestamps: List[datetime]
    q10: List[float]
    q50: List[float]
    q90: List[float]
    units: str
    hard_constraint_value: Optional[float] = None
    interval_coverage: float
    inference_latency_ms: float

# Risks & Runway
class RiskContributor(BaseModel):
    factor: str
    impact_score: float

class RiskResponse(BaseModel):
    device_id: str
    computed_at: datetime
    current_capacity_pct: float
    runway_hours_estimate: float
    runway_hours_lower_bound: float
    runway_hours_upper_bound: float
    risk_level: str
    breach_status: Optional[str] = "NOMINAL_HEADROOM"
    is_runway_reliable: bool = True
    unreliability_reason: Optional[str] = None
    capacity_breach_prob_24h: float
    capacity_breach_prob_72h: float
    latency_breach_prob_24h: float
    risk_contributors: List[RiskContributor]

# Digital Twin & Scenarios
class ScenarioCreate(BaseModel):
    device_id: str
    name: str
    action_type: str = Field(..., description="DO_NOTHING, EXPAND_CAPACITY, TIER_COLD_DATA, RESCHEDULE_TASK, REBALANCE_WORKLOAD")
    parameters: Dict[str, Any] = {}

class ScenarioSimulationResponse(BaseModel):
    scenario_id: str
    device_id: str
    name: str
    action_type: str
    parameters: Dict[str, Any]
    duration_minutes: float
    estimated_cost_usd: float
    overhead_io_penalty_pct: float
    safety_envelope_passed: bool
    violation_reasons: List[str]
    residual_risk_score: float
    assumptions: List[str]
    timeline_timestamps: List[datetime]
    baseline_q50: List[float]
    counterfactual_q50: List[float]
    hard_limit: float
    is_simulated_estimate: bool = True

# Recommendations
class RecommendationItem(BaseModel):
    id: str
    device_id: str
    action_type: str
    title: str
    rationale: str
    rank: int
    utility_score: float
    estimated_runway_gain_hours: float
    hard_constraints_checked: bool
    approval_status: str
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime

class RecommendationApprovalRequest(BaseModel):
    notes: Optional[str] = None

# Alerts
class AlertItem(BaseModel):
    id: str
    device_id: str
    category: str
    severity: str
    title: str
    message: str
    status: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None

# Experiments
class ExperimentCreate(BaseModel):
    name: str
    dataset_name: str
    model_type: str  # LightGBM, SeasonalNaive, Persistence
    horizon_hours: int = 72

class ExperimentItem(BaseModel):
    id: str
    name: str
    dataset_name: str
    model_type: str
    horizon_hours: int
    train_samples: int
    test_samples: int
    mae: float
    rmse: float
    pinball_loss: float
    interval_coverage: float
    mean_interval_width: float
    created_at: datetime
    manifest: Dict[str, Any]

# Reliability & Drift
class ReliabilityMetrics(BaseModel):
    model_version: str
    overall_interval_coverage: float
    target_nominal_coverage: float = 0.80
    mean_pinball_loss: float
    mean_mae_capacity_gb: float
    mean_mae_latency_ms: float
    drift_status: str
    active_drift_alerts: int
    last_evaluation_timestamp: datetime
    is_fallback_active: bool

# Datasets
class DatasetItem(BaseModel):
    id: str
    name: str
    dataset_type: str
    records_count: int
    missing_rate: float
    sampling_interval_s: int
    license: str
    description: str
    created_at: datetime

# Audit Logs
class AuditItem(BaseModel):
    id: int
    timestamp: datetime
    user: str
    action: str
    target_type: str
    target_id: str
    details: Dict[str, Any]
