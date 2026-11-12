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
    storage_type = Column(String(64), default="SAN")  # Local storage, NAS, SAN, Cloud storage, Backup storage, Object storage
    environment_location = Column(String(128), default="Primary Data Center")
    description = Column(Text, default="")
    notes = Column(Text, default="")
    last_telemetry_at = Column(DateTime, nullable=True)
    pool_id = Column(String(64), nullable=True)
    system_id = Column(String(64), nullable=True)
    organization_id = Column(String(64), default="org-primary-enterprise", nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    created_by = Column(String(64), default="system", nullable=False)
    updated_by = Column(String(64), default="system", nullable=False)
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
    total_capacity_bytes = Column(BigInteger, nullable=True)
    used_bytes = Column(BigInteger, nullable=False)
    free_bytes = Column(BigInteger, nullable=False)
    utilization_pct = Column(Float, nullable=False)
    read_iops = Column(Float, nullable=True)
    write_iops = Column(Float, nullable=True)
    throughput_mb_s = Column(Float, nullable=True)
    latency_p95_ms = Column(Float, nullable=True)
    read_latency_ms = Column(Float, nullable=True)
    write_latency_ms = Column(Float, nullable=True)
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
    model_version_id = Column(String(64), nullable=True)
    horizon_days = Column(Integer, nullable=True)
    daily_predictions_json = Column(Text, nullable=True)
    projected_capacity_breach = Column(Boolean, default=False)
    breach_timestamp = Column(DateTime, nullable=True)

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
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    created_by = Column(String(64), default="system_operator")
    updated_by = Column(String(64), default="system_operator")

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
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)

    device = relationship("Device", back_populates="recommendations")
    verifications = relationship("RecommendationVerification", back_populates="recommendation", cascade="all, delete-orphan")


class RecommendationVerification(Base):
    __tablename__ = "recommendation_verifications"

    id = Column(String(64), primary_key=True)
    recommendation_id = Column(String(64), ForeignKey("recommendations.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)
    predicted_used_bytes = Column(BigInteger, default=0)
    measured_used_bytes = Column(BigInteger, default=0)
    discrepancy_bytes = Column(BigInteger, default=0)
    discrepancy_pct = Column(Float, default=0.0)
    predicted_runway_hours = Column(Float, default=0.0)
    measured_runway_hours = Column(Float, default=0.0)
    verification_status = Column(String(32), default="VERIFIED_WITHIN_TOLERANCE")
    rollback_recommended = Column(Boolean, default=False)
    details_json = Column(Text, default="{}")
    verified_at = Column(DateTime, default=utc_now)

    recommendation = relationship("Recommendation", back_populates="verifications")



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
    acknowledged_by = Column(String(64), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_details = Column(Text, nullable=True)
    supporting_evidence_json = Column(Text, default="{}")

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
    user_id = Column(String(64), nullable=True, index=True)
    user_role = Column(String(32), nullable=True)
    outcome = Column(String(32), default="SUCCESS")
    action = Column(String(64), nullable=False)
    target_type = Column(String(64), nullable=False)
    target_id = Column(String(64), nullable=False)
    organization_id = Column(String(64), default="org-primary-enterprise", nullable=False, index=True)
    client_ip = Column(String(64), default="127.0.0.1")
    prev_hash = Column(String(64), nullable=True)
    entry_hash = Column(String(64), nullable=True)
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
    organization_id = Column(String(64), default="org-primary-enterprise", nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)



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
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    name = Column(String(128), nullable=False)
    model_type = Column(String(64), nullable=False)  # RandomForestRegressor, HistGradientBoostingRegressor, etc.
    version_tag = Column(String(32), nullable=False)
    feature_schema_json = Column(Text, default="[]")
    feature_version = Column(String(32), default="v2.0")
    artifact_path = Column(String(512), nullable=True)
    target_metric = Column(String(64), default="used_bytes")
    train_samples_count = Column(Integer, default=0)
    validation_samples = Column(Integer, default=0)
    train_start_at = Column(DateTime, nullable=True)
    train_end_at = Column(DateTime, nullable=True)
    mae = Column(Float, default=0.0)
    rmse = Column(Float, default=0.0)
    interval_coverage = Column(Float, default=0.80)
    is_active = Column(Boolean, default=True)
    status = Column(String(32), default="TRAINED")
    error_message = Column(Text, nullable=True)
    trained_by = Column(String(64), default="system")
    trained_at = Column(DateTime, default=utc_now)

    metrics = relationship("ModelMetric", back_populates="model_version", cascade="all, delete-orphan")


class ModelTrustEvaluation(Base):
    __tablename__ = "model_trust_evaluations"

    id = Column(String(64), primary_key=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    evaluated_at = Column(DateTime, default=utc_now)
    trust_status = Column(String(32), nullable=False)  # HEALTHY, WATCH, DEGRADED, INSUFFICIENT_EVIDENCE
    status_reason = Column(Text, nullable=False)
    data_drift_detected = Column(Boolean, default=False)
    prediction_drift_detected = Column(Boolean, default=False)
    performance_degraded = Column(Boolean, default=False)
    max_metric_psi = Column(Float, default=0.0)
    evaluated_mae_gb = Column(Float, default=0.0)
    evaluated_rmse_gb = Column(Float, default=0.0)
    empirical_coverage_pct = Column(Float, default=0.0)
    recommended_action = Column(String(64), default="NO_ACTION_REQUIRED")
    details_json = Column(Text, default="{}")


class VaultBackupRecord(Base):
    __tablename__ = "vault_backup_records"

    id = Column(String(64), primary_key=True)
    created_at = Column(DateTime, default=utc_now)
    created_by = Column(String(64), default="operator@aegisstor.internal")
    format_version = Column(String(32), default="AEGISSTOR_VAULT_V1")
    database_size_bytes = Column(BigInteger, default=0)
    files_count = Column(Integer, default=3)
    checksum_status = Column(String(32), default="VERIFIED_VALID")
    restoration_status = Column(String(32), default="UNTESTED")
    last_test_rto_seconds = Column(Float, nullable=True)
    last_test_rpo_hours = Column(Float, nullable=True)
    last_test_timestamp = Column(DateTime, nullable=True)
    manifest_json = Column(Text, default="{}")


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


# ============================================================================
# PHOENIX: SAFE SELF-HEALING & INCIDENT ORCHESTRATION ENTITIES
# ============================================================================

class PhoenixIncident(Base):
    __tablename__ = "phoenix_incidents"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    category = Column(String(64), nullable=False)  # CAPACITY_EXHAUSTION, LATENCY_SATURATION, IOPS_THROTTLING, POOL_UNBALANCE, FAILOVER_DEGRADATION, WORKLOAD_HOTSPOT
    severity = Column(String(32), nullable=False)  # SEV1_CRITICAL, SEV2_HIGH, SEV3_MEDIUM, SEV4_LOW
    status = Column(String(32), nullable=False, default="DETECTED")  # 14 lifecycle states
    target_device_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    affected_devices_json = Column(Text, default="[]")
    pool_id = Column(String(64), nullable=True)
    
    # Provenance and evidence classification
    evidence_type = Column(String(32), default="PREDICTED")  # PREDICTED, OBSERVED, SIMULATED, RESOLVED, INSUFFICIENT_EVIDENCE
    detection_timestamp = Column(DateTime, default=utc_now)
    projected_breach_timestamp = Column(DateTime, nullable=True)
    time_to_breach_hours = Column(Float, nullable=True)
    confidence_score = Column(Float, default=0.85)
    model_version = Column(String(64), default="Conformal-Quantile-v1.8")
    
    # Structured evidence and hypothesis tracking
    symptoms_json = Column(Text, default="[]")
    hypotheses_json = Column(Text, default="[]")  # [{hypothesis, status: CONFIRMED_OBSERVATION|SUPPORTED_HYPOTHESIS|UNCONFIRMED_HYPOTHESIS}]
    evidence_payload_json = Column(Text, default="{}")
    forecast_reference_id = Column(Integer, nullable=True)
    risk_reference_id = Column(Integer, nullable=True)
    
    # Active resolution and runbook linkage
    active_proposal_id = Column(String(64), nullable=True)
    assigned_engineer = Column(String(64), default="unassigned")
    escalation_reason = Column(String(256), nullable=True)
    resolution_summary = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PhoenixRunbook(Base):
    __tablename__ = "phoenix_runbooks"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    version = Column(String(32), default="1.0.0")
    category = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    preconditions_json = Column(Text, default="[]")
    steps_json = Column(Text, default="[]")
    rollback_steps_json = Column(Text, default="[]")
    safety_constraints_json = Column(Text, default="{}")
    verification_criteria_json = Column(Text, default="{}")
    estimated_duration_minutes = Column(Integer, default=15)
    is_automated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class PhoenixPolicy(Base):
    __tablename__ = "phoenix_policies"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    version = Column(String(32), default="1.0.0")
    min_free_reserve_pct = Column(Float, default=10.0)
    max_latency_ms = Column(Float, default=20.0)
    max_bandwidth_mb_s = Column(Float, default=6400.0)
    max_telemetry_age_seconds = Column(Integer, default=3600)
    allowed_action_types_json = Column(Text, default="[]")
    require_human_approval = Column(Boolean, default=True)
    allow_shadow_mode_only = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class PhoenixActionProposal(Base):
    __tablename__ = "phoenix_action_proposals"

    id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("phoenix_incidents.id"), nullable=False, index=True)
    runbook_id = Column(String(64), ForeignKey("phoenix_runbooks.id"), nullable=True)
    action_type = Column(String(64), nullable=False)
    target_resource_id = Column(String(64), nullable=False)
    parameters_json = Column(Text, default="{}")
    
    # Pre-execution simulation & policy evaluation
    simulation_run_id = Column(String(64), nullable=True)
    simulation_outcome_json = Column(Text, default="{}")
    policy_verdict = Column(String(32), default="REQUIRES_HUMAN_REVIEW")  # ALLOWED_FOR_SIMULATION, REQUIRES_HUMAN_REVIEW, REJECTED_BY_POLICY, INSUFFICIENT_EVIDENCE
    policy_violations_json = Column(Text, default="[]")
    recommendation_score = Column(Float, default=0.85)
    
    # Human approval tracking (proposal mutation resets approval)
    approval_status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED, INVALIDATED
    approved_by = Column(String(64), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_rationale = Column(Text, nullable=True)
    proposal_hash = Column(String(64), nullable=False)  # SHA256 of parameters and action to verify immutability
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PhoenixExecutionRecord(Base):
    __tablename__ = "phoenix_execution_records"

    id = Column(String(64), primary_key=True, index=True)
    proposal_id = Column(String(64), ForeignKey("phoenix_action_proposals.id"), nullable=False, index=True)
    incident_id = Column(String(64), ForeignKey("phoenix_incidents.id"), nullable=False, index=True)
    idempotency_token = Column(String(64), unique=True, nullable=False, index=True)
    execution_mode = Column(String(32), default="MODE_A_SIMULATE")  # MODE_A_SIMULATE, MODE_B_DIAGNOSTIC_READONLY, MODE_C_CONTROLLED_EXECUTION
    status = Column(String(32), default="EXECUTING")  # EXECUTING, SUCCESS, FAILED, ABORTED
    current_step_index = Column(Integer, default=0)
    total_steps = Column(Integer, default=1)
    step_logs_json = Column(Text, default="[]")
    execution_result_json = Column(Text, default="{}")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)


class PhoenixRecoveryVerification(Base):
    __tablename__ = "phoenix_recovery_verifications"

    id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("phoenix_incidents.id"), nullable=False, index=True)
    proposal_id = Column(String(64), ForeignKey("phoenix_action_proposals.id"), nullable=True)
    execution_id = Column(String(64), ForeignKey("phoenix_execution_records.id"), nullable=True)
    status = Column(String(32), default="INCONCLUSIVE")  # RECOVERY_SATISFIED, PARTIALLY_VERIFIED, INCONCLUSIVE, UNSUCCESSFUL
    observation_window_hours = Column(Float, default=24.0)
    baseline_metrics_json = Column(Text, default="{}")
    observed_metrics_json = Column(Text, default="{}")
    threshold_checks_json = Column(Text, default="[]")
    secondary_degradation_detected = Column(Boolean, default=False)
    residual_risk_score = Column(Float, default=0.0)
    verification_notes = Column(Text, default="")
    verified_at = Column(DateTime, default=utc_now)


# ============================================================================
# ATLAS: REALITY CALIBRATION & EVIDENCE INTELLIGENCE ENTITIES (Prompt 9.0)
# ============================================================================

class AtlasCalibrationConfig(Base):
    __tablename__ = "atlas_calibration_configs"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    version = Column(String(32), default="1.0.0")
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    target_metric = Column(String(64), default="utilization_pct")
    calibration_window_days = Column(Integer, default=14)
    evaluation_window_days = Column(Integer, default=7)
    parameter_overrides_json = Column(Text, default="{}")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class AtlasCalibrationRun(Base):
    __tablename__ = "atlas_calibration_runs"

    id = Column(String(64), primary_key=True, index=True)
    config_id = Column(String(64), ForeignKey("atlas_calibration_configs.id"), nullable=False, index=True)
    simulator_version = Column(String(64), default="DigitalTwin-v4.0")
    calibration_status = Column(String(64), default="CALIBRATED_FOR_SPECIFIED_CONDITIONS")
    # Statuses: NOT_CALIBRATED, CALIBRATION_IN_PROGRESS, CALIBRATED_FOR_SPECIFIED_CONDITIONS, CALIBRATION_DEGRADATION_DETECTED, INSUFFICIENT_EVIDENCE
    training_mae = Column(Float, default=0.0)
    training_rmse = Column(Float, default=0.0)
    evaluation_mae = Column(Float, default=0.0)
    evaluation_rmse = Column(Float, default=0.0)
    bias = Column(Float, default=0.0)
    relative_error = Column(Float, default=0.0)
    sample_count = Column(Integer, default=0)
    condition_scope_json = Column(Text, default="{}")
    calibration_report_json = Column(Text, default="{}")
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)


class AtlasDiscrepancyRecord(Base):
    __tablename__ = "atlas_discrepancy_records"

    id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("atlas_calibration_runs.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    metric_name = Column(String(64), nullable=False)
    evaluation_timestamp = Column(DateTime, nullable=False, index=True)
    observed_value = Column(Float, nullable=False)
    simulated_value = Column(Float, nullable=False)
    residual = Column(Float, nullable=False)  # observed - simulated
    relative_error = Column(Float, nullable=False)
    workload_regime = Column(String(64), default="NORMAL_BALANCED")
    is_outlier = Column(Boolean, default=False)
    notes = Column(String(256), default="")


class AtlasActionEffectEvidence(Base):
    __tablename__ = "atlas_action_effect_evidence"

    id = Column(String(64), primary_key=True, index=True)
    action_type = Column(String(64), nullable=False, index=True)
    target_device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    evidence_category = Column(String(64), default="SIMULATION_COUNTERFACTUAL")
    # Categories: SIMULATION_COUNTERFACTUAL, CONTROLLED_EXPERIMENT, OBSERVED_OPERATIONAL_OUTCOME, ASSUMPTION_SUPPORTED
    sample_size = Column(Integer, default=1)
    primary_effect_mean = Column(Float, default=0.0)
    primary_effect_std = Column(Float, default=0.0)
    side_effects_json = Column(Text, default="{}")
    confounding_factors_json = Column(Text, default="[]")
    is_causally_verified = Column(Boolean, default=False)
    evaluation_status = Column(String(64), default="ESTIMATED")
    last_evaluated_at = Column(DateTime, default=utc_now)


class AtlasExperiment(Base):
    __tablename__ = "atlas_experiments"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    experiment_type = Column(String(64), default="SIM_TO_REAL_COMPARISON")
    # Types: FORECAST_BACKTEST, SIM_TO_REAL_COMPARISON, WORKLOAD_REPLAY, MODEL_CALIBRATION, ACTION_DURATION_BENCHMARK, INTERVENTION_EFFECT_VALIDATION
    status = Column(String(32), default="CREATED")  # CREATED, RUNNING, COMPLETED, FAILED, CANCELLED
    objective = Column(Text, nullable=False)
    hypothesis = Column(Text, nullable=False)
    dataset_id = Column(String(64), nullable=True)
    target_device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    configuration_json = Column(Text, default="{}")
    safety_restrictions_json = Column(Text, default="{}")
    results_json = Column(Text, default="{}")
    limitations_json = Column(Text, default="[]")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class AtlasFidelityAssessment(Base):
    __tablename__ = "atlas_fidelity_assessments"

    id = Column(String(64), primary_key=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    simulator_version = Column(String(64), default="DigitalTwin-v4.0")
    assessment_status = Column(String(64), default="MODERATE_FIDELITY")
    # Statuses: HIGH_FIDELITY, MODERATE_FIDELITY, LIMITED_SCOPE, DEGRADED, UNKNOWN
    prediction_fidelity_score = Column(Float, default=85.0)
    workload_coverage_score = Column(Float, default=80.0)
    data_quality_score = Column(Float, default=90.0)
    calibration_recency_score = Column(Float, default=88.0)
    action_effect_evidence_score = Column(Float, default=75.0)
    overall_fidelity_score = Column(Float, default=83.6)
    evaluated_conditions_json = Column(Text, default="{}")
    out_of_scope_warnings_json = Column(Text, default="[]")
    evaluated_at = Column(DateTime, default=utc_now)


class AtlasEvidenceGap(Base):
    __tablename__ = "atlas_evidence_gaps"

    id = Column(String(64), primary_key=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    metric_name = Column(String(64), nullable=False)
    workload_regime = Column(String(64), nullable=False)
    gap_description = Column(Text, nullable=False)
    impact_level = Column(String(32), default="MEDIUM")  # HIGH, MEDIUM, LOW
    uncertainty_score = Column(Float, default=0.65)
    candidate_experiment_json = Column(Text, default="{}")
    voe_rank = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now)


# =========================================================================
# AEGISSTOR ORACLE — Workload Attribution & Bottleneck Intelligence Models
# =========================================================================

class OracleWorkload(Base):
    """
    Known application, service, or background tenant running on storage resources.
    Captures attribution capability flag to prevent fabricating unmeasured contributions.
    """
    __tablename__ = "oracle_workloads"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    target_device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    tier = Column(String(32), default="NVME_TIER1")
    workload_type = Column(String(64), default="TRANSACTIONAL")  # TRANSACTIONAL, BATCH_ETL, BACKUP, STREAMING, RESIDUAL
    priority = Column(String(32), default="P0_CRITICAL")        # P0_CRITICAL, P1_HIGH, P2_NORMAL, P3_BACKGROUND
    sla_max_latency_ms = Column(Float, default=15.0)
    sla_min_throughput_mb_s = Column(Float, default=50.0)
    owner_team = Column(String(128), default="storage-sre@aegisstor.internal")
    is_active = Column(Boolean, default=True)
    attribution_available = Column(Boolean, default=True)      # When False, report "Workload attribution unavailable"
    description = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)


class OracleWorkloadTelemetry(Base):
    """
    Time-series attribution records per workload.
    Stores direct I/O measurements (IOPS, bytes read/write, queue depth, tail latency).
    """
    __tablename__ = "oracle_workload_telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workload_id = Column(String(64), ForeignKey("oracle_workloads.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    allocated_bytes = Column(Float, default=0.0)
    read_bytes_sec = Column(Float, default=0.0)
    write_bytes_sec = Column(Float, default=0.0)
    read_iops = Column(Float, default=0.0)
    write_iops = Column(Float, default=0.0)
    latency_p95_ms = Column(Float, default=1.0)
    avg_io_size_kb = Column(Float, default=32.0)
    queue_depth = Column(Float, default=1.0)
    is_synthetic = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_oracle_tel_dev_ts", "device_id", "timestamp"),
        Index("idx_oracle_tel_wl_ts", "workload_id", "timestamp"),
    )


class OracleHypothesis(Base):
    """
    Structured investigation hypothesis.
    Tracks lifecycle, supporting vs contradicting observations, and reviewer signoff.
    Never states causation without experimental or verified counterfactual evidence.
    """
    __tablename__ = "oracle_hypotheses"

    id = Column(String(64), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    target_resource = Column(String(64), nullable=False, index=True)
    workload_id = Column(String(64), nullable=True)
    status = Column(String(64), default="DRAFT")
    # Statuses: DRAFT, EVIDENCE_GATHERING, READY_FOR_TESTING, UNDER_EVALUATION,
    #           SUPPORTED_WITHIN_CONDITIONS, NOT_SUPPORTED, INCONCLUSIVE, CLOSED
    supporting_evidence_json = Column(Text, default="[]")
    contradicting_evidence_json = Column(Text, default="[]")
    confounding_variables_json = Column(Text, default="[]")
    proposed_evaluation_method = Column(String(128), default="CONTROLLED_REPLAY_SIMULATION")
    conclusion = Column(Text, nullable=True)
    reviewer = Column(String(128), default="lead_sre@aegisstor.internal")
    evidence_references_json = Column(Text, default="[]")
    status_history_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now)


class OracleBottleneckCase(Base):
    """
    Transparent bottleneck investigation queue item.
    Combines symptom observations, affected topology, evidence quality, and next recommended test.
    """
    __tablename__ = "oracle_bottleneck_cases"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    symptom_type = Column(String(64), nullable=False)
    # Types: TAIL_LATENCY_SPIKE, QUEUE_SATURATION, THROUGHPUT_COLLAPSE, CAPACITY_ACCELERATION, RESOURCE_CONTENTION
    target_device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    involved_workloads_json = Column(Text, default="[]")
    measurement_window = Column(String(64), default="LAST_24_HOURS")
    severity = Column(String(32), default="ELEVATED")  # CRITICAL, ELEVATED, MODERATE, LOW
    evidence_quality_score = Column(Float, default=0.75)  # 0.0 to 1.0
    supporting_evidence_json = Column(Text, default="[]")
    conflicting_evidence_json = Column(Text, default="[]")
    status = Column(String(32), default="ACTIVE")      # ACTIVE, INVESTIGATING, MITIGATED, DISMISSED, DEFERRED
    assigned_to = Column(String(128), nullable=True)
    recommended_test = Column(Text, default="Run counterfactual workload throttling simulation")
    detected_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now)


class OracleCounterfactualExperiment(Base):
    """
    Controlled what-if workload simulation log.
    Strictly isolated: simulations never execute real physical mutations or claim proven real causation.
    """
    __tablename__ = "oracle_counterfactual_experiments"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    target_device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    workload_id = Column(String(64), nullable=False)
    intervention_type = Column(String(64), default="THROTTLE_INTENSITY")
    # Types: THROTTLE_INTENSITY, RESCHEDULE_WINDOW, REBALANCE_TIER, EXPAND_BANDWIDTH
    parameter_changes_json = Column(Text, default="{}")
    baseline_metrics_json = Column(Text, default="{}")
    simulated_metrics_json = Column(Text, default="{}")
    is_causally_proven = Column(Boolean, default=False)
    causality_disclaimer = Column(
        Text,
        default="Simulated counterfactual outcome. Observational attribution does not establish physical causation without real controlled measurement."
    )
    simulator_version = Column(String(64), default="DigitalTwin-Oracle-v5.0")
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# AEGISSTOR GAUNTLET — INDEPENDENT VALIDATION & EVIDENCE WORKBENCH (Prompt 18.0)
# ==============================================================================

class GauntletSuite(Base):
    """
    Catalog of documented, reproducible evaluation benchmark suites.
    Defines objectives, required datasets, baseline methods, constraints, and acceptance criteria.
    """
    __tablename__ = "gauntlet_suites"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    version = Column(String(32), default="1.0.0")
    category = Column(String(64), nullable=False)  # CAPACITY_FORECAST, PERFORMANCE_FORECAST, STORAGE_DECISION_QUALITY, ROBUSTNESS_SAFETY
    objective = Column(Text, nullable=False)
    supported_capabilities_json = Column(Text, default="[]")
    required_dataset = Column(String(128), default="enterprise-telemetry-primary")
    baseline_methods_json = Column(Text, default="[]")
    test_scenarios_json = Column(Text, default="[]")
    expected_outputs_json = Column(Text, default="[]")
    safety_constraints_json = Column(Text, default="[]")
    acceptance_criteria_json = Column(Text, default="[]")
    known_limitations = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class GauntletRun(Base):
    """
    Versioned record of an executed benchmark experiment with reproducible manifest and SHA-256 hash.
    Preserves historical records; never silently overwrites prior results.
    """
    __tablename__ = "gauntlet_runs"

    id = Column(String(64), primary_key=True, index=True)
    suite_id = Column(String(64), ForeignKey("gauntlet_suites.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    status = Column(String(32), default="QUEUED")  # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    manifest_json = Column(Text, nullable=False)   # Full versioned run manifest
    manifest_sha256 = Column(String(64), nullable=False, index=True)
    dataset_id = Column(String(64), nullable=False)
    dataset_checksum = Column(String(64), default="")
    evaluation_period_json = Column(Text, default="{}")
    split_ratio_json = Column(Text, default='{"train": 0.70, "val": 0.15, "test": 0.15}')
    models_evaluated_json = Column(Text, default="[]")
    baselines_evaluated_json = Column(Text, default="[]")
    parameters_json = Column(Text, default="{}")
    results_json = Column(Text, default="{}")
    exit_status = Column(String(32), default="SUCCESS")  # SUCCESS, CRITERIA_MET, CRITERIA_UNMET, ABORTED
    reproducibility_package_path = Column(String(255), nullable=True)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)
    execution_seconds = Column(Float, default=0.0)


class GauntletClaim(Base):
    """
    Central ledger connecting technical project claims to verifiable artifacts and run outputs.
    Guarantees that unverified or insufficiently supported claims are never marked as verified.
    """
    __tablename__ = "gauntlet_claims"

    id = Column(String(64), primary_key=True, index=True)
    claim_text = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)  # FEATURE_IMPLEMENTATION, TEST_PASS, FORECAST_ACCURACY, OPERATIONAL_SAFETY, SIMULATOR_FIDELITY, INTERVENTION_QUALITY
    verification_status = Column(String(64), default="DRAFT")
    # Statuses: DRAFT, AWAITING_EVIDENCE, SUPPORTED_WITHIN_TESTED_CONDITIONS,
    #           PARTIALLY_SUPPORTED, CONTRADICTED_BY_EVIDENCE, UNVERIFIED, RETIRED
    supporting_run_ids_json = Column(Text, default="[]")
    relevant_model_versions_json = Column(Text, default="[]")
    relevant_test_ids_json = Column(Text, default="[]")
    evidence_artifacts_json = Column(Text, default="[]")
    applicable_scope = Column(Text, default="")
    known_limitations = Column(Text, default="")
    last_verified_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class GauntletFailure(Base):
    """
    Transparent failure and anomaly record.
    Preserves negative test outcomes, out-of-distribution shocks, and rejection events without overwriting.
    """
    __tablename__ = "gauntlet_failures"

    id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), nullable=True, index=True)
    failure_category = Column(String(64), nullable=False)
    # Categories: OUT_OF_BOUNDS_ERROR, TEMPORAL_LEAKAGE, TELEMETRY_DROPOUT,
    #             INTERCONNECT_SATURATION, INFEASIBLE_ACTION, REPRODUCTION_DRIFT, TEST_ASSERTION_FAILURE
    exact_configuration_json = Column(Text, default="{}")
    error_summary = Column(Text, nullable=False)
    detailed_logs = Column(Text, default="")
    inputs_and_versions_json = Column(Text, default="{}")
    reproduction_steps = Column(Text, default="")
    expected_behavior = Column(Text, default="")
    actual_behavior = Column(Text, default="")
    severity = Column(String(32), default="MEDIUM")  # CRITICAL, HIGH, MEDIUM, LOW
    resolution_state = Column(String(32), default="OPEN")  # OPEN, INVESTIGATING, MITIGATED, RESOLVED, ACCEPTED_LIMITATION
    follow_up_verification = Column(Text, default="")
    recorded_at = Column(DateTime, default=utc_now)


class GauntletReproduction(Base):
    """
    One-click reproduction comparison record.
    Tracks numerical differences between original run and reproduced run within defined tolerances.
    """
    __tablename__ = "gauntlet_reproductions"

    id = Column(String(64), primary_key=True, index=True)
    original_run_id = Column(String(64), ForeignKey("gauntlet_runs.id"), nullable=False, index=True)
    reproduced_run_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="REPRODUCED_WITHIN_TOLERANCE")
    # Statuses: REPRODUCED_WITHIN_TOLERANCE, REPRODUCED_WITH_DRIFT, FAILED_TO_REPRODUCE, INCONCLUSIVE
    metric_deltas_json = Column(Text, default="{}")
    max_relative_drift_pct = Column(Float, default=0.0)
    tolerance_threshold_pct = Column(Float, default=3.0)
    reproduction_report_md = Column(Text, default="")
    verified_by = Column(String(128), default="automated_verifier")
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# AEGISSTOR SOVEREIGN — PRIVACY-CONSCIOUS FEDERATED STORAGE INTELLIGENCE (19.0)
# ==============================================================================

class SovereignSite(Base):
    """
    Participating storage site in the Sovereign federated intelligence network.
    Maintains local telemetry isolation, local model configuration, and reliability state.
    """
    __tablename__ = "sovereign_sites"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    region = Column(String(64), nullable=False)
    workload_type = Column(String(64), nullable=False)
    # Types: OLTP_WRITE_HEAVY, ANALYTICS_READ_HEAVY, EDGE_LOW_VOLUME, BACKUP_STREAM_SHIFT
    associated_device_id = Column(String(64), ForeignKey("devices.id"), nullable=True)
    local_sample_count = Column(Integer, default=0)
    local_model_version = Column(String(64), default="v1.0.0-local")
    reliability_score = Column(Float, default=0.85)  # 0.0 to 1.0
    validation_rmse = Column(Float, default=0.0)
    status = Column(String(32), default="ACTIVE")  # ACTIVE, TRAINING, DROPOUT, SUSPENDED
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class SovereignRound(Base):
    """
    Coordinator-managed federated training round.
    Coordinates local training dispatch, model update collection, validation, and aggregation.
    """
    __tablename__ = "sovereign_rounds"

    id = Column(String(64), primary_key=True, index=True)
    round_number = Column(Integer, nullable=False, index=True)
    global_model_version = Column(String(64), nullable=False)
    aggregation_strategy = Column(String(64), default="FED_AVG")
    # Strategies: FED_AVG, RELIABILITY_AWARE, PERSONALIZED, DIFFERENTIAL_PRIVACY
    participating_sites_json = Column(Text, default="[]")
    status = Column(String(32), default="COMPLETED")  # INITIATED, COLLECTING, AGGREGATING, COMPLETED, ABORTED
    total_samples = Column(Integer, default=0)
    global_mae = Column(Float, default=0.0)
    global_rmse = Column(Float, default=0.0)
    rejection_count = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)


class SovereignUpdate(Base):
    """
    Encapsulated model parameter update submitted by a local site.
    Contains weights, update magnitude, and sample count without exposing raw telemetry.
    """
    __tablename__ = "sovereign_updates"

    id = Column(String(64), primary_key=True, index=True)
    round_id = Column(String(64), ForeignKey("sovereign_rounds.id"), nullable=False, index=True)
    site_id = Column(String(64), ForeignKey("sovereign_sites.id"), nullable=False, index=True)
    model_version = Column(String(64), nullable=False)
    sample_count = Column(Integer, nullable=False)
    weights_json = Column(Text, nullable=False)
    bias = Column(Float, default=0.0)
    update_norm = Column(Float, default=0.0)
    is_accepted = Column(Boolean, default=True)
    rejection_reason = Column(String(255), nullable=True)
    assigned_weight = Column(Float, default=0.0)
    metrics_json = Column(Text, default="{}")
    submitted_at = Column(DateTime, default=utc_now)


class SovereignGlobalModel(Base):
    """
    Global federated storage forecasting model artifact generated by coordinator aggregation.
    """
    __tablename__ = "sovereign_global_models"

    id = Column(String(64), primary_key=True, index=True)
    version = Column(String(64), nullable=False, unique=True, index=True)
    round_number = Column(Integer, nullable=False)
    weights_json = Column(Text, nullable=False)
    bias = Column(Float, default=0.0)
    aggregation_strategy = Column(String(64), default="FED_AVG")
    evaluation_summary_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)


class SovereignExperiment(Base):
    """
    Reproducible federated learning experiment comparison manifest and tournament results.
    """
    __tablename__ = "sovereign_experiments"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    config_json = Column(Text, nullable=False)
    tournament_results_json = Column(Text, nullable=False)
    manifest_json = Column(Text, nullable=False)
    manifest_sha256 = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# MODULE 1-12 PERSISTENT ENTERPRISE MODELS (AUTH, INGESTION, QUALITY, ML, REPORTS, SETTINGS)
# ==============================================================================

class RevokedToken(Base):
    """Stores invalidated JWT tokens upon user logout."""
    __tablename__ = "revoked_tokens"

    id = Column(String(64), primary_key=True, index=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    revoked_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=True)


class IngestionJob(Base):
    """Records CSV imports, manual entries, collector batches, and row-level validation diagnostics."""
    __tablename__ = "ingestion_jobs"

    id = Column(String(64), primary_key=True, index=True)
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    source_type = Column(String(32), nullable=False)  # CSV_UPLOAD, MANUAL_ENTRY, API_COLLECTOR, HISTORICAL_IMPORT
    filename = Column(String(255), nullable=True)
    status = Column(String(32), default="COMPLETED")  # COMPLETED, PARTIAL, FAILED
    total_rows = Column(Integer, default=0)
    accepted_rows = Column(Integer, default=0)
    rejected_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    errors_json = Column(Text, default="[]")
    idempotency_key = Column(String(128), nullable=True, index=True)
    uploaded_by = Column(String(64), default="system")
    created_at = Column(DateTime, default=utc_now, index=True)


class DataQualityResult(Base):
    """Persists deterministic preprocessing and data quality assessments without modifying raw telemetry."""
    __tablename__ = "data_quality_results"

    id = Column(String(64), primary_key=True, index=True)
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    ingestion_job_id = Column(String(64), ForeignKey("ingestion_jobs.id"), nullable=True)
    total_records_received = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    rejected_records = Column(Integer, default=0)
    duplicate_records = Column(Integer, default=0)
    missing_field_stats_json = Column(Text, default="{}")
    outlier_count = Column(Integer, default=0)
    data_completeness_pct = Column(Float, default=100.0)
    latest_telemetry_timestamp = Column(DateTime, nullable=True)
    preprocessing_decisions_json = Column(Text, default="[]")
    evaluated_at = Column(DateTime, default=utc_now, index=True)


class ModelMetric(Base):
    """Chronological holdout validation metrics for trained ML models."""
    __tablename__ = "model_metrics"

    id = Column(String(64), primary_key=True, index=True)
    model_version_id = Column(String(64), ForeignKey("model_versions.id"), nullable=False, index=True)
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    mae = Column(Float, nullable=False)
    rmse = Column(Float, nullable=False)
    r2_score = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    mase = Column(Float, nullable=True)
    pinball_loss = Column(Float, nullable=True)
    interval_coverage = Column(Float, nullable=True)
    mean_interval_width = Column(Float, nullable=True)
    vs_baseline_status = Column(String(32), default="UNKNOWN")
    residual_std = Column(Float, default=0.0)
    is_selected = Column(Boolean, default=False)
    selection_reason = Column(Text, default="")
    evaluated_at = Column(DateTime, default=utc_now)

    model_version = relationship("ModelVersion", back_populates="metrics")


class ReportHistory(Base):
    """Tracks generated reports, filters, format (JSON/CSV/PDF), and metadata."""
    __tablename__ = "report_history"

    id = Column(String(64), primary_key=True, index=True)
    report_type = Column(String(64), nullable=False, index=True)
    format = Column(String(16), nullable=False)  # JSON, CSV, PDF
    storage_id = Column(String(64), nullable=True)
    filters_json = Column(Text, default="{}")
    generated_by = Column(String(64), default="system")
    row_count = Column(Integer, default=0)
    summary_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now, index=True)


class ApplicationSetting(Base):
    """Persisted system configuration thresholds, forecast settings, and retention rules."""
    __tablename__ = "application_settings"

    key = Column(String(64), primary_key=True, index=True)
    value_json = Column(Text, nullable=False)
    category = Column(String(32), default="general")
    version = Column(Integer, default=1, nullable=False)
    updated_by = Column(String(64), default="system")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ApiKey(Base):
    """Hashed API keys for authenticated external collectors and agents."""
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    key_prefix = Column(String(16), nullable=False)
    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    role = Column(String(32), default="OPERATOR")
    organization_id = Column(String(64), default="org-primary-enterprise")
    created_by = Column(String(64), default="admin")
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class TelemetryConnector(Base):
    """Registered telemetry adapter configurations (Linux Host, Prometheus, HTTP Agent, etc.)."""
    __tablename__ = "telemetry_connectors"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    connector_type = Column(String(32), nullable=False)  # LINUX_HOST, PROMETHEUS, CSV_HISTORICAL, HTTP_API
    endpoint_url = Column(String(512), nullable=True)
    config_json = Column(Text, default="{}")
    target_storage_id = Column(String(64), ForeignKey("devices.id"), nullable=True)
    is_enabled = Column(Boolean, default=True)
    last_status = Column(String(32), default="CONFIGURED")  # CONFIGURED, CONNECTED, ERROR, STALE
    last_error = Column(Text, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class DataReliabilityProfile(Base):
    """Stores the 9 transparent data reliability factors and weighted 0..1 score."""
    __tablename__ = "data_reliability_profiles"

    id = Column(String(64), primary_key=True, index=True)
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    reliability_score = Column(Float, nullable=False)  # 0.0 to 1.0
    reliability_tier = Column(String(16), nullable=False)  # HIGH, MEDIUM, LOW
    is_stale = Column(Boolean, default=False)
    last_successful_timestamp = Column(DateTime, nullable=True)
    completeness_score = Column(Float, default=1.0)
    freshness_score = Column(Float, default=1.0)
    continuity_score = Column(Float, default=1.0)
    duplicate_rate_score = Column(Float, default=1.0)
    invalid_rate_score = Column(Float, default=1.0)
    capacity_consistency_score = Column(Float, default=1.0)
    missing_metric_score = Column(Float, default=1.0)
    source_availability_score = Column(Float, default=1.0)
    historical_stability_score = Column(Float, default=1.0)
    weights_json = Column(Text, default="{}")
    explanation_json = Column(Text, default="{}")
    uncertainty_multiplier = Column(Float, default=1.0)
    evaluated_at = Column(DateTime, default=utc_now, index=True)


class WorkloadRegimeEvent(Base):
    """Persisted statistical workload regime classifications, changepoints, and drift events."""
    __tablename__ = "workload_regime_events"

    id = Column(String(64), primary_key=True, index=True)
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    regime_label = Column(String(48), nullable=False)
    event_type = Column(String(48), nullable=False)  # REGIME_CLASSIFICATION, CHANGEPOINT_BURST, DISTRIBUTION_DRIFT, INTERRUPTION
    severity = Column(String(16), default="INFO")
    confidence = Column(Float, default=0.0)
    supporting_metrics_json = Column(Text, default="{}")
    explanation = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=utc_now, index=True)


class BackgroundJob(Base):
    """Tracks asynchronous ML model training and scheduled forecast jobs."""
    __tablename__ = "background_jobs"

    id = Column(String(64), primary_key=True, index=True)
    job_type = Column(String(48), nullable=False)  # ML_TRAIN_CHAMPION_CHALLENGER, FORECAST_SCHEDULED
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    status = Column(String(24), default="QUEUED")  # QUEUED, VALIDATING_DATA, PREPARING_FEATURES, TRAINING, EVALUATING, SAVING_MODEL, COMPLETED, FAILED, CANCELLED
    stage = Column(String(32), default="QUEUED")
    progress_pct = Column(Integer, default=0)
    result_json = Column(Text, default="{}")
    error_message = Column(Text, nullable=True)
    triggered_by = Column(String(64), default="system")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime, nullable=True)


class CapacityRiskEvaluation(Base):
    """Stores probabilistic capacity exhaustion & safety-threshold crossing risk assessments."""
    __tablename__ = "capacity_risk_evaluations"

    id = Column(String(64), primary_key=True, index=True)
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    forecast_id = Column(Integer, ForeignKey("forecasts.id"), nullable=True)
    horizon_days = Column(Integer, default=30)
    current_utilization_pct = Column(Float, nullable=False)
    forecasted_utilization_pct = Column(Float, nullable=False)
    remaining_safe_capacity_bytes = Column(BigInteger, nullable=False)
    safety_threshold_crossing_date = Column(DateTime, nullable=True)
    exhaustion_date = Column(DateTime, nullable=True)
    threshold_crossing_probability = Column(Float, nullable=False)
    expected_shortfall_bytes = Column(BigInteger, default=0)
    adverse_p90_utilization_pct = Column(Float, nullable=False)
    data_reliability_score = Column(Float, default=1.0)
    details_json = Column(Text, default="{}")
    evaluated_at = Column(DateTime, default=utc_now, index=True)


class Role(Base):
    """System & administrator-configurable IAM roles."""
    __tablename__ = "roles"

    name = Column(String(32), primary_key=True, index=True)
    description = Column(Text, default="")
    is_system = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class Permission(Base):
    """Canonical central permission catalog keys."""
    __tablename__ = "permissions"

    key = Column(String(64), primary_key=True, index=True)
    module = Column(String(48), nullable=False, index=True)
    description = Column(Text, default="")


class RolePermission(Base):
    """Dynamic role-to-permission assignments persisted in the database."""
    __tablename__ = "role_permissions"

    id = Column(String(64), primary_key=True, index=True)
    role_name = Column(String(32), ForeignKey("roles.name"), nullable=False, index=True)
    permission_key = Column(String(64), ForeignKey("permissions.key"), nullable=False, index=True)
    is_allowed = Column(Boolean, default=True)


class UserSession(Base):
    """Persistent authenticated user sessions supporting expiration and immediate revocation."""
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    session_token_hash = Column(String(128), unique=True, index=True, nullable=False)
    csrf_token_hash = Column(String(128), nullable=True)
    role_at_issue = Column(String(32), nullable=False)
    client_ip = Column(String(64), default="127.0.0.1")
    user_agent = Column(String(256), default="")
    is_revoked = Column(Boolean, default=False, index=True)
    revoked_reason = Column(String(128), nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_seen_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)


class PasswordResetToken(Base):
    """Single-use expiring SHA-256 hashed password reset tokens."""
    __tablename__ = "password_reset_tokens"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_by = Column(String(64), default="self_service")
    created_at = Column(DateTime, default=utc_now)


class LoginAttempt(Base):
    """Records authentication attempts (both successes and failures) for security auditing."""
    __tablename__ = "login_attempts"

    id = Column(String(64), primary_key=True, index=True)
    identifier = Column(String(128), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    success = Column(Boolean, default=False)
    failure_reason = Column(String(128), nullable=True)
    client_ip = Column(String(64), default="127.0.0.1")
    user_agent = Column(String(256), default="")
    attempted_at = Column(DateTime, default=utc_now, index=True)


class OperationalAssignment(Base):
    """Tracks alert / recommendation assignments and human workflow ownership."""
    __tablename__ = "operational_assignments"

    id = Column(String(64), primary_key=True, index=True)
    target_type = Column(String(32), nullable=False, index=True)  # ALERT, RECOMMENDATION, STORAGE
    target_id = Column(String(64), nullable=False, index=True)
    assigned_to_user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    assigned_by = Column(String(64), nullable=False)
    status = Column(String(32), default="ASSIGNED")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)


class OutboxEvent(Base):
    """Transactional outbox ensuring real-time events are committed atomically and replayable via cursor."""
    __tablename__ = "outbox_events"

    seq_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id = Column(String(64), unique=True, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    event_version = Column(Integer, default=1, nullable=False)
    organization_id = Column(String(64), default="org-primary-enterprise", nullable=False, index=True)
    actor_user_id = Column(String(64), nullable=True)
    actor_username = Column(String(64), nullable=True)
    actor_role = Column(String(32), nullable=True)
    resource_type = Column(String(48), nullable=False, index=True)
    resource_id = Column(String(64), nullable=False, index=True)
    entity_version = Column(Integer, nullable=True)
    changed_fields_json = Column(Text, default="[]")
    payload_json = Column(Text, default="{}")
    required_permission = Column(String(64), nullable=True)
    target_user_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, index=True)
    published_at = Column(DateTime, nullable=True)
    delivery_error = Column(Text, nullable=True)


class UserNotification(Base):
    """Persistent per-user notifications for real-time bell, unread counters, and reconnect recovery."""
    __tablename__ = "user_notifications"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False)
    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    resource_type = Column(String(48), nullable=False)
    resource_id = Column(String(64), nullable=False)
    severity = Column(String(24), default="INFO")  # INFO, WARNING, CRITICAL, SUCCESS
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)


class OperationalTask(Base):
    """Persistent collaborative operational task assigned between Admin and Operator."""
    __tablename__ = "operational_tasks"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), default="org-primary-enterprise", nullable=False, index=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, default="")
    priority = Column(String(24), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(32), default="ASSIGNED", index=True)  # ASSIGNED, ACKNOWLEDGED, IN_PROGRESS, WAITING, COMPLETED, CANCELLED
    assigned_to_user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    created_by_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    linked_device_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    linked_alert_id = Column(String(64), nullable=True)
    due_date = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_by = Column(String(64), default="system")
    updated_by = Column(String(64), default="system")
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime, nullable=True)


class TaskComment(Base):
    """Persistent progress comment thread on an OperationalTask."""
    __tablename__ = "task_comments"

    id = Column(String(64), primary_key=True, index=True)
    task_id = Column(String(64), ForeignKey("operational_tasks.id"), nullable=False, index=True)
    author_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    author_username = Column(String(64), nullable=False)
    author_role = Column(String(32), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, index=True)


class UserPresence(Base):
    """Authenticated live WebSocket presence state per active session."""
    __tablename__ = "user_presence"

    session_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    username = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False)
    current_route = Column(String(128), default="/")
    is_online = Column(Boolean, default=True, nullable=False, index=True)
    connected_at = Column(DateTime, default=utc_now)
    last_heartbeat_at = Column(DateTime, default=utc_now, index=True)
    disconnected_at = Column(DateTime, nullable=True)


import app.models.enterprise_entities  # noqa: E402, F401
import app.models.control_plane_entities  # noqa: E402, F401









