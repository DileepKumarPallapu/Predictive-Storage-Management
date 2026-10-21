from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MetricCategory(str, Enum):
    OBSERVED_MEASUREMENT = "OBSERVED_MEASUREMENT"
    MODEL_PREDICTION = "MODEL_PREDICTION"
    STATISTICAL_UNCERTAINTY = "STATISTICAL_UNCERTAINTY"
    SIMULATED_OUTCOME = "SIMULATED_OUTCOME"
    UNVERIFIED_ASSUMPTION = "UNVERIFIED_ASSUMPTION"

class IntervalStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DEGRADED = "DEGRADED"

class ReliabilityStatus(str, Enum):
    RELIABLE = "RELIABLE"
    STALE_DATA = "STALE_DATA"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    ZERO_OR_NEGATIVE_GROWTH = "ZERO_OR_NEGATIVE_GROWTH"
    HIGH_VARIANCE_UNSTABLE = "HIGH_VARIANCE_UNSTABLE"
    ALREADY_BREACHED = "ALREADY_BREACHED"
    FALLBACK_ACTIVE = "FALLBACK_ACTIVE"

class ForecastContract(BaseModel):
    """
    Standard typed contract shared across ML service, risk engine,
    digital twin simulator, and API clients.
    """
    device_id: str
    target_metric: str
    metric_units: str
    category: MetricCategory = MetricCategory.MODEL_PREDICTION
    created_at: datetime
    latest_observation_at: datetime
    prediction_horizon_hours: int
    
    # Point estimates and uncertainty
    timestamps: List[datetime]
    median_point_estimate: List[float]
    lower_bound: Optional[List[float]] = None
    upper_bound: Optional[List[float]] = None
    interval_status: IntervalStatus = IntervalStatus.AVAILABLE
    nominal_coverage: float = 0.80
    empirical_coverage: Optional[float] = None
    mean_interval_width: Optional[float] = None
    
    # Metadata and provenance
    model_name: str
    model_version: str
    dataset_identifier: str
    evaluation_status: str
    data_freshness_status: str
    inference_latency_ms: float
    known_limitations: List[str] = Field(default_factory=list)

class CapacityRunwayResult(BaseModel):
    """
    Structured output from Capacity Reserve Runway Engine.
    """
    device_id: str
    evaluated_at: datetime
    total_capacity_bytes: int
    current_used_bytes: int
    current_free_bytes: int
    current_utilization_pct: float
    configured_critical_threshold_pct: float
    configured_warning_threshold_pct: float
    
    # Growth metrics
    growth_rate_1h_bytes: float
    growth_rate_24h_bytes: float
    growth_rate_daily_gb: float
    
    # Estimated breach horizons
    estimated_runway_hours: float
    runway_lower_bound_hours: float
    runway_upper_bound_hours: float
    earliest_breach_timestamp: Optional[datetime] = None
    breach_status: str
    
    # Sensitivity analysis
    sensitivity_optimistic_hours: float   # 20% lower growth rate
    sensitivity_expected_hours: float     # Median projected growth
    sensitivity_pessimistic_hours: float  # 30% higher growth rate
    
    # Reliability & limitations
    reliability_status: ReliabilityStatus
    is_runway_reliable: bool
    unreliability_reason: Optional[str] = None
    assumptions: List[str]
    limitations: List[str]

class PerformanceRiskResult(BaseModel):
    """
    Structured output from Performance Risk Engine.
    """
    device_id: str
    evaluated_at: datetime
    
    # Metric values (observed vs limits)
    current_latency_p95_ms: float
    max_acceptable_latency_ms: float
    current_queue_depth: float
    max_acceptable_queue_depth: float
    current_total_iops: float
    max_supported_iops: float
    current_throughput_mb_s: float
    max_bus_throughput_mb_s: float
    
    # Risk evaluations
    latency_risk_level: str
    queue_saturation_risk: str
    throughput_headroom_pct: float
    
    # Probability calibration status
    is_calibrated_probability: bool = False
    estimated_violation_probability_24h: float
    estimated_violation_probability_72h: float
    calibration_method: str = "Empirical Gaussian Copula"
    
    # Coupling analysis
    capacity_latency_coupling_penalty_ms: float
    coupling_explanation: str
    
    reasons_for_potential_inaccuracy: List[str]
