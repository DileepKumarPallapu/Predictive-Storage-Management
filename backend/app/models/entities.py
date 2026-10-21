from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, BigInteger, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.datetime_utils import utc_now

class Device(Base):
    __tablename__ = "devices"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    tier = Column(String(32), nullable=False)  # NVME_TIER1, SAS_TIER2, HDD_ARCHIVE, CLOUD_S3
    media_type = Column(String(32), nullable=False)  # NVMe SSD, Enterprise SAS, SATA HDD, Object Store
    total_capacity_bytes = Column(BigInteger, nullable=False)
    warning_threshold_pct = Column(Float, default=80.0)
    critical_threshold_pct = Column(Float, default=90.0)
    max_acceptable_latency_ms = Column(Float, default=20.0)
    min_free_reserve_pct = Column(Float, default=10.0)
    status = Column(String(32), default="HEALTHY")  # HEALTHY, WARNING, CRITICAL, MAINTENANCE
    workload_profile = Column(String(64), default="OLTP Database")
    pool_id = Column(String(64), nullable=True)
    system_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    telemetry = relationship("Telemetry", back_populates="device", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="device", cascade="all, delete-orphan")
    risks = relationship("RiskAssessment", back_populates="device", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="device", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    used_bytes = Column(BigInteger, nullable=False)
    free_bytes = Column(BigInteger, nullable=False)
    utilization_pct = Column(Float, nullable=False)
    read_iops = Column(Float, default=0.0)
    write_iops = Column(Float, default=0.0)
    throughput_mb_s = Column(Float, default=0.0)
    latency_p95_ms = Column(Float, default=0.0)
    queue_depth = Column(Float, default=1.0)
    is_synthetic = Column(Boolean, default=True)
    source_label = Column(String(64), default="synthetic_generator")

    device = relationship("Device", back_populates="telemetry")

    __table_args__ = (
        Index("idx_device_timestamp", "device_id", "timestamp"),
    )


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    model_name = Column(String(64), nullable=False)
    target_metric = Column(String(64), nullable=False)
    horizon_hours = Column(Integer, nullable=False)
    generated_at = Column(DateTime, default=utc_now)
    historical_cutoff = Column(DateTime, nullable=False)
    timestamps_json = Column(Text, nullable=False)
    q10_json = Column(Text, nullable=False)
    q50_json = Column(Text, nullable=False)
    q90_json = Column(Text, nullable=False)
    interval_coverage = Column(Float, default=0.80)
    inference_ms = Column(Float, default=0.0)

    device = relationship("Device", back_populates="forecasts")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    computed_at = Column(DateTime, default=utc_now)
    current_capacity_pct = Column(Float, nullable=False)
    runway_hours_estimate = Column(Float, nullable=False)
    runway_hours_lower = Column(Float, nullable=False)
    runway_hours_upper = Column(Float, nullable=False)
    risk_level = Column(String(32), default="NOMINAL")  # NOMINAL, WARNING, ELEVATED, CRITICAL
    capacity_breach_prob_24h = Column(Float, default=0.0)
    capacity_breach_prob_72h = Column(Float, default=0.0)
    latency_breach_prob_24h = Column(Float, default=0.0)
    contributors_json = Column(Text, default="[]")

    device = relationship("Device", back_populates="risks")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(String(64), primary_key=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    action_type = Column(String(64), nullable=False)
    parameters_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)
    created_by = Column(String(64), default="system_operator")

    device = relationship("Device", back_populates="scenarios")
    outcome = relationship("SimulatedOutcome", back_populates="scenario", uselist=False, cascade="all, delete-orphan")


class SimulatedOutcome(Base):
    __tablename__ = "simulated_outcomes"

    id = Column(String(64), primary_key=True)
    scenario_id = Column(String(64), ForeignKey("scenarios.id"), nullable=False, unique=True)
    duration_minutes = Column(Float, default=0.0)
    estimated_cost_usd = Column(Float, default=0.0)
    overhead_io_penalty_pct = Column(Float, default=0.0)
    safety_envelope_passed = Column(Boolean, default=True)
    violation_reasons_json = Column(Text, default="[]")
    residual_risk_score = Column(Float, default=0.0)
    trajectory_json = Column(Text, default="{}")
    assumptions_json = Column(Text, default="[]")

    scenario = relationship("Scenario", back_populates="outcome")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(64), primary_key=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)
    title = Column(String(128), nullable=False)
    rationale = Column(Text, nullable=False)
    rank = Column(Integer, default=1)
    utility_score = Column(Float, default=0.0)
    estimated_runway_gain_hours = Column(Float, default=0.0)
    hard_constraints_checked = Column(Boolean, default=True)
    approval_status = Column(String(32), default="PENDING_REVIEW")
    reviewed_by = Column(String(64), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    device = relationship("Device", back_populates="recommendations")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    category = Column(String(32), nullable=False)
    severity = Column(String(32), default="INFO")
    title = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(32), default="ACTIVE")
    triggered_at = Column(DateTime, default=utc_now)
    resolved_at = Column(DateTime, nullable=True)

    device = relationship("Device", back_populates="alerts")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    dataset_name = Column(String(128), nullable=False)
    model_type = Column(String(64), nullable=False)
    horizon_hours = Column(Integer, nullable=False)
    train_samples = Column(Integer, default=0)
    test_samples = Column(Integer, default=0)
    mae = Column(Float, default=0.0)
    rmse = Column(Float, default=0.0)
    pinball_loss = Column(Float, default=0.0)
    interval_coverage = Column(Float, default=0.0)
    mean_interval_width = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)
    manifest_json = Column(Text, default="{}")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    user = Column(String(64), default="operator@aegisstor.internal")
    action = Column(String(64), nullable=False)
    target_type = Column(String(64), nullable=False)
    target_id = Column(String(64), nullable=False)
    details_json = Column(Text, default="{}")


class DatasetSource(Base):
    __tablename__ = "dataset_sources"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    dataset_type = Column(String(32), nullable=False)
    records_count = Column(Integer, default=0)
    missing_rate = Column(Float, default=0.0)
    sampling_interval_s = Column(Integer, default=3600)
    license = Column(String(128), default="Apache-2.0 / Academic Evaluation")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), default="OPERATOR")
    is_active = Column(Boolean, default=True)


class WorkloadEvent(Base):
    __tablename__ = "workload_events"

    id = Column(String(64), primary_key=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)  # ETL_BURST, RAID_SCRUB, BACKUP_BURST, WORKLOAD_SHIFT
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    intensity_factor = Column(Float, default=1.5)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    model_type = Column(String(64), nullable=False)
    version_tag = Column(String(32), nullable=False)
    feature_schema_json = Column(Text, default="[]")
    target_metric = Column(String(64), default="used_bytes")
    train_samples_count = Column(Integer, default=0)
    mae = Column(Float, default=0.0)
    rmse = Column(Float, default=0.0)
    interval_coverage = Column(Float, default=0.80)
    is_active = Column(Boolean, default=True)
    trained_at = Column(DateTime, default=utc_now)


# =====================================================================
# AEGISSTOR OMEGA FLEET & GOVERNANCE MODELS
# =====================================================================

class StorageSystem(Base):
    __tablename__ = "storage_systems"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    system_type = Column(String(64), nullable=False)  # ALL_FLASH_ARRAY, HYBRID_SAN, OBJECT_STORAGE_CLUSTER
    vendor_family = Column(String(64), default="Enterprise SDS")
    interconnect_type = Column(String(64), default="NVMe-oF / PCIe Gen4")
    total_bus_bandwidth_mb_s = Column(Float, default=12800.0)
    max_iops_capacity = Column(Float, default=1500000.0)
    status = Column(String(32), default="HEALTHY")
    created_at = Column(DateTime, default=utc_now)


class StoragePool(Base):
    __tablename__ = "storage_pools"

    id = Column(String(64), primary_key=True)
    system_id = Column(String(64), ForeignKey("storage_systems.id"), nullable=False)
    name = Column(String(128), nullable=False)
    tier = Column(String(32), nullable=False)  # NVME_TIER1, SAS_TIER2, HDD_ARCHIVE, CLOUD_S3
    redundancy_policy = Column(String(64), default="RAID10")
    total_raw_bytes = Column(BigInteger, nullable=False)
    usable_capacity_bytes = Column(BigInteger, nullable=False)
    allocated_bytes = Column(BigInteger, default=0)
    overcommit_ratio = Column(Float, default=1.0)
    status = Column(String(32), default="HEALTHY")
    created_at = Column(DateTime, default=utc_now)


class ResourceRelationship(Base):
    __tablename__ = "resource_relationships"

    id = Column(String(64), primary_key=True)
    source_id = Column(String(64), nullable=False, index=True)
    source_type = Column(String(32), nullable=False)  # DEVICE, POOL, SYSTEM, WORKLOAD
    target_id = Column(String(64), nullable=False, index=True)
    target_type = Column(String(32), nullable=False)
    relationship_type = Column(String(64), nullable=False)  # POOL_MEMBER, SHARED_BUS_CONCURRENCY, REPLICATION_TARGET, TIERING_PARTNER, BACKUP_DEPENDENCY
    provenance = Column(String(32), default="DISCOVERED")  # DISCOVERED, USER_DEFINED, INFERRED
    confidence_score = Column(Float, default=1.0)  # 0.0 to 1.0
    contention_weight = Column(Float, default=0.5)  # coupling strength for performance degradation
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)


class WorkloadDependency(Base):
    __tablename__ = "workload_dependencies"

    id = Column(String(64), primary_key=True)
    workload_name = Column(String(128), nullable=False)
    primary_device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    secondary_device_id = Column(String(64), nullable=True)
    criticality = Column(String(32), default="PRODUCTION")  # MISSION_CRITICAL, PRODUCTION, BATCH_ANALYTICS, COLD_ARCHIVE
    sla_max_latency_ms = Column(Float, default=15.0)
    sla_min_throughput_mb_s = Column(Float, default=100.0)
    io_pattern = Column(String(64), default="RANDOM_WRITE_DOMINANT")
    cross_volume_lock = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)


class OutcomeLedgerRecord(Base):
    __tablename__ = "outcome_ledger_records"

    id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    evaluation_window_hours = Column(Integer, default=24)
    forecasted_used_pct = Column(Float, nullable=False)
    simulated_used_pct = Column(Float, nullable=False)
    observed_used_pct = Column(Float, nullable=False)
    forecast_error_mae = Column(Float, default=0.0)
    action_taken = Column(String(64), default="NO_ACTION")
    counterfactual_outcome_class = Column(String(64), nullable=False)  # CORRECT_PREVENTIVE_SUCCESS, UNNECESSARY_INTERVENTION, MISSED_BREACH, INEFFECTIVE_INTERVENTION
    runway_hours_gained = Column(Float, default=0.0)
    decision_cost_usd = Column(Float, default=0.0)
    net_decision_loss = Column(Float, default=0.0)
    metadata_json = Column(Text, default="{}")


class GovernancePromotionGate(Base):
    __tablename__ = "governance_promotion_gates"

    id = Column(String(64), primary_key=True)
    candidate_model_name = Column(String(128), nullable=False)
    baseline_model_name = Column(String(128), nullable=False)
    candidate_version = Column(String(32), nullable=False)
    candidate_mae = Column(Float, default=0.0)
    baseline_mae = Column(Float, default=0.0)
    candidate_decision_loss = Column(Float, default=0.0)
    baseline_decision_loss = Column(Float, default=0.0)
    candidate_calibration_error = Column(Float, default=0.0)
    baseline_calibration_error = Column(Float, default=0.0)
    hard_safety_check_passed = Column(Boolean, default=True)
    gate_verdict = Column(String(32), default="PROMOTED")  # PROMOTED, REJECTED, CANARY_TRIAL
    verdict_rationale = Column(Text, default="")
    evaluated_at = Column(DateTime, default=utc_now)
    evaluated_by = Column(String(64), default="aegisstor_governance_engine")


# =====================================================================
# AEGISSTOR JURASSIC RESILIENCE LAB MODELS
# =====================================================================

class JurassicScenario(Base):
    __tablename__ = "jurassic_scenarios"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    scenario_family = Column(String(64), nullable=False)  # CAPACITY_DISTURBANCE, PERFORMANCE_DISTURBANCE, TEMPORAL_DISTURBANCE, TELEMETRY_DISTURBANCE, COMPOUND_DISTURBANCE
    description = Column(Text, default="")
    target_device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    seed = Column(Integer, default=42)
    simulation_duration_hours = Column(Integer, default=168)
    initial_capacity_pct = Column(Float, default=70.0)
    capacity_growth_gb_day = Column(Float, default=45.0)
    burst_events_json = Column(Text, default="[]")
    read_iops_base = Column(Float, default=10000.0)
    write_iops_base = Column(Float, default=8000.0)
    latency_noise_ms = Column(Float, default=0.5)
    telemetry_drop_rate = Column(Float, default=0.0)
    telemetry_delay_s = Column(Integer, default=0)
    chaos_faults_json = Column(Text, default="[]")
    is_preset = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    created_by = Column(String(64), default="resilience_architect")


class JurassicExperiment(Base):
    __tablename__ = "jurassic_experiments"

    id = Column(String(64), primary_key=True)
    scenario_id = Column(String(64), ForeignKey("jurassic_scenarios.id"), nullable=False, index=True)
    status = Column(String(32), default="CREATED")  # CREATED, QUEUED, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED
    target_device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    model_version = Column(String(64), default="LightGBM-Conformal-Quantile-v1.8")
    dataset_identifier = Column(String(64), default="ds-synthetic-enterprise-v1")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    current_step_hour = Column(Integer, default=0)
    total_steps_hours = Column(Integer, default=168)
    final_fallback_state = Column(String(64), default="STATE_1_HEALTHY_EVIDENCE")  # STATE_1 to STATE_5
    fallback_transitions_json = Column(Text, default="[]")
    fault_events_json = Column(Text, default="[]")
    telemetry_history_json = Column(Text, default="[]")
    forecast_evaluations_json = Column(Text, default="[]")
    drift_detected = Column(Boolean, default=False)
    drift_details_json = Column(Text, default="{}")
    resilience_score = Column(Float, default=100.0)
    resilience_breakdown_json = Column(Text, default="{}")
    forensics_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)


class JurassicFaultEvent(Base):
    __tablename__ = "jurassic_fault_events"

    id = Column(String(64), primary_key=True)
    experiment_id = Column(String(64), ForeignKey("jurassic_experiments.id"), nullable=False, index=True)
    injection_hour = Column(Integer, nullable=False)
    duration_hours = Column(Integer, nullable=False)
    fault_type = Column(String(64), nullable=False)
    target_module = Column(String(64), nullable=False)
    expected_symptom = Column(String(256), default="")
    recovery_condition = Column(String(256), default="")
    actual_outcome = Column(String(256), default="")
    test_passed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class JurassicDriftRecord(Base):
    __tablename__ = "jurassic_drift_records"

    id = Column(String(64), primary_key=True)
    experiment_id = Column(String(64), ForeignKey("jurassic_experiments.id"), nullable=False, index=True)
    evaluation_step_hour = Column(Integer, nullable=False)
    metric_name = Column(String(64), nullable=False)
    drift_statistic = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    drift_status = Column(String(64), default="NO_DETECTED_SHIFT")  # NO_DETECTED_SHIFT, POSSIBLE_SHIFT, CONFIRMED_EVALUATION_MISMATCH, INSUFFICIENT_DATA
    p_value = Column(Float, nullable=True)
    explanation = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)


class JurassicResilienceReport(Base):
    __tablename__ = "jurassic_resilience_reports"

    id = Column(String(64), primary_key=True)
    experiment_id = Column(String(64), ForeignKey("jurassic_experiments.id"), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    scenario_name = Column(String(128), nullable=False)
    summary_markdown = Column(Text, nullable=False)
    csv_metrics_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)



