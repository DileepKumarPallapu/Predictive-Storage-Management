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






