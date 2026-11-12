from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from app.database import Base
from app.utils.datetime_utils import utc_now


# ==============================================================================
# PHASE A: MULTI-ORGANISATION & HIERARCHY
# ==============================================================================

class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    plan = Column(String(32), default="ENTERPRISE")
    default_currency = Column(String(8), default="USD")
    status = Column(String(24), default="ACTIVE")
    settings_json = Column(Text, default="{}")
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class OrganisationMember(Base):
    __tablename__ = "organisation_members"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(32), default="OPERATOR", nullable=False)
    department = Column(String(64), default="Platform Engineering")
    cost_centre = Column(String(64), default="CC-INFRA-01")
    status = Column(String(24), default="ACTIVE")  # ACTIVE, INVITED, SUSPENDED
    invited_by = Column(String(64), nullable=True)
    joined_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member_user"),
    )


class BusinessUnit(Base):
    __tablename__ = "business_units"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    code = Column(String(32), nullable=False)
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    cost_centre = Column(String(64), default="CC-DEFAULT")
    created_at = Column(DateTime, default=utc_now)


class Region(Base):
    __tablename__ = "regions"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    code = Column(String(32), nullable=False)
    residency_zone = Column(String(64), default="GLOBAL")
    created_at = Column(DateTime, default=utc_now)


class Site(Base):
    __tablename__ = "sites"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    business_unit_id = Column(String(64), ForeignKey("business_units.id"), nullable=True)
    region_id = Column(String(64), ForeignKey("regions.id"), nullable=True)
    name = Column(String(128), nullable=False)
    site_code = Column(String(32), nullable=False)
    address = Column(String(256), default="")
    tier_class = Column(String(32), default="PRIMARY")
    created_at = Column(DateTime, default=utc_now)


class Environment(Base):
    __tablename__ = "environments"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    site_id = Column(String(64), ForeignKey("sites.id"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    env_type = Column(String(32), default="PRODUCTION")  # PRODUCTION, STAGING, DEV, DR
    created_at = Column(DateTime, default=utc_now)


class InfrastructureGroup(Base):
    __tablename__ = "infrastructure_groups"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    environment_id = Column(String(64), ForeignKey("environments.id"), nullable=True)
    name = Column(String(128), nullable=False)
    department = Column(String(64), default="Storage Operations")
    cost_centre = Column(String(64), default="CC-STORAGE")
    created_at = Column(DateTime, default=utc_now)


class StorageCluster(Base):
    __tablename__ = "storage_clusters"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    site_id = Column(String(64), ForeignKey("sites.id"), nullable=False, index=True)
    environment_id = Column(String(64), ForeignKey("environments.id"), nullable=True)
    name = Column(String(128), nullable=False)
    vendor = Column(String(64), default="Enterprise SAN")
    cluster_type = Column(String(32), default="BLOCK")
    status = Column(String(24), default="HEALTHY")
    created_at = Column(DateTime, default=utc_now)


class StorageHost(Base):
    __tablename__ = "storage_hosts"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    cluster_id = Column(String(64), ForeignKey("storage_clusters.id"), nullable=False, index=True)
    hostname = Column(String(128), nullable=False)
    os_family = Column(String(64), default="Linux")
    status = Column(String(24), default="HEALTHY")
    created_at = Column(DateTime, default=utc_now)


class StoragePoolEntity(Base):
    __tablename__ = "storage_pools_v2"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    host_id = Column(String(64), ForeignKey("storage_hosts.id"), nullable=True)
    cluster_id = Column(String(64), ForeignKey("storage_clusters.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    tier = Column(String(32), default="NVME_TIER1")
    total_capacity_bytes = Column(BigInteger, default=0)
    used_bytes = Column(BigInteger, default=0)
    status = Column(String(24), default="HEALTHY")
    created_at = Column(DateTime, default=utc_now)


class StorageVolume(Base):
    __tablename__ = "storage_volumes"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    pool_id = Column(String(64), ForeignKey("storage_pools_v2.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    name = Column(String(128), nullable=False)
    total_capacity_bytes = Column(BigInteger, default=0)
    used_bytes = Column(BigInteger, default=0)
    status = Column(String(24), default="HEALTHY")
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    department = Column(String(64), default="Core Infrastructure")
    cost_centre = Column(String(64), default="CC-STORAGE")
    created_at = Column(DateTime, default=utc_now)


class ResourceAssignment(Base):
    __tablename__ = "resource_assignments"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    resource_type = Column(String(32), nullable=False)
    resource_id = Column(String(64), nullable=False, index=True)
    assigned_to_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    department = Column(String(64), default="Operations")
    cost_centre = Column(String(64), default="CC-OPS")
    assigned_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# PHASE B: INFRASTRUCTURE TOPOLOGY
# ==============================================================================

class AssetRelationship(Base):
    __tablename__ = "asset_relationships"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    source_type = Column(String(48), nullable=False)
    source_id = Column(String(64), nullable=False, index=True)
    target_type = Column(String(48), nullable=False)
    target_id = Column(String(64), nullable=False, index=True)
    relationship_type = Column(String(48), nullable=False)  # CONTAINS, HOSTS, SERVES, DEPENDS_ON, REPLICATES_TO
    discovery_source = Column(String(24), default="MANUAL", nullable=False)  # MANUAL | DISCOVERED
    verified = Column(Boolean, default=True)
    metadata_json = Column(Text, default="{}")
    created_by = Column(String(64), default="system")
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "source_type", "source_id", "target_type", "target_id", "relationship_type",
            name="uq_asset_rel_edge",
        ),
    )


class RelationshipHistory(Base):
    __tablename__ = "relationship_history"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    relationship_id = Column(String(64), nullable=False, index=True)
    action = Column(String(32), nullable=False)  # CREATED, UPDATED, DELETED
    actor = Column(String(64), nullable=False)
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# PHASE C: APPLICATION & BUSINESS SERVICE DEPENDENCIES
# ==============================================================================

class ApplicationEntity(Base):
    __tablename__ = "applications"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    department = Column(String(64), default="Engineering")
    criticality = Column(String(24), default="TIER_1")  # TIER_1, TIER_2, TIER_3
    environment = Column(String(32), default="PRODUCTION")
    description = Column(Text, default="")
    availability_objective_pct = Column(Float, default=99.9)
    created_at = Column(DateTime, default=utc_now)


class BusinessService(Base):
    __tablename__ = "business_services"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    department = Column(String(64), default="Business Operations")
    criticality = Column(String(24), default="MISSION_CRITICAL")  # MISSION_CRITICAL, HIGH, MEDIUM, LOW
    description = Column(Text, default="")
    sla_target_pct = Column(Float, nullable=True)
    contractual_sla_supplied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)


class ApplicationDependency(Base):
    __tablename__ = "application_dependencies"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    application_id = Column(String(64), ForeignKey("applications.id"), nullable=False, index=True)
    depends_on_type = Column(String(32), nullable=False)  # DEVICE, VOLUME, CLUSTER, APPLICATION
    depends_on_id = Column(String(64), nullable=False, index=True)
    dependency_role = Column(String(64), default="PRIMARY_STORAGE")
    discovery_source = Column(String(24), default="MANUAL")
    verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class ServiceResourceRelationship(Base):
    __tablename__ = "service_resource_relationships"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    service_id = Column(String(64), ForeignKey("business_services.id"), nullable=False, index=True)
    resource_type = Column(String(32), nullable=False)  # APPLICATION, DEVICE, VOLUME
    resource_id = Column(String(64), nullable=False, index=True)
    impact_weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# PHASE D: SERVICE RELIABILITY (SLI / SLO) & ENTERPRISE INCIDENTS
# ==============================================================================

class SLIDefinition(Base):
    __tablename__ = "sli_definitions"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    service_id = Column(String(64), ForeignKey("business_services.id"), nullable=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    name = Column(String(128), nullable=False)
    metric_type = Column(String(48), nullable=False)  # CAPACITY_HEADROOM, READ_LATENCY, WRITE_LATENCY, TELEMETRY_FRESHNESS, BACKUP_FRESHNESS, AVAILABILITY_SIGNAL
    unit = Column(String(24), default="pct")
    evaluation_window_days = Column(Integer, default=30)
    warning_threshold = Column(Float, nullable=False)
    critical_threshold = Column(Float, nullable=False)
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class SLORecord(Base):
    __tablename__ = "slo_records"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    sli_id = Column(String(64), ForeignKey("sli_definitions.id"), nullable=False, index=True)
    service_id = Column(String(64), ForeignKey("business_services.id"), nullable=True, index=True)
    name = Column(String(128), nullable=False)
    target_pct = Column(Float, default=99.9)
    is_contractual_sla = Column(Boolean, default=False)
    contractual_sla_approved_by = Column(String(64), nullable=True)
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    status = Column(String(24), default="ACTIVE")
    created_at = Column(DateTime, default=utc_now)


class SLOEvaluation(Base):
    __tablename__ = "slo_evaluations"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    slo_id = Column(String(64), ForeignKey("slo_records.id"), nullable=False, index=True)
    actual_sli_value = Column(Float, nullable=True)
    compliance_pct = Column(Float, nullable=True)
    error_budget_remaining_pct = Column(Float, nullable=True)
    burn_rate = Column(Float, nullable=True)
    breached = Column(Boolean, default=False)
    insufficient_data = Column(Boolean, default=False)
    details_json = Column(Text, default="{}")
    evaluated_at = Column(DateTime, default=utc_now, index=True)


class EnterpriseIncident(Base):
    __tablename__ = "enterprise_incidents"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(64), nullable=False)
    severity = Column(String(16), default="SEV-3", nullable=False)  # SEV-1, SEV-2, SEV-3, SEV-4
    status = Column(String(24), default="OPEN", nullable=False)  # DETECTED, OPEN, ACKNOWLEDGED, INVESTIGATING, MITIGATING, RESOLVED, CLOSED
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    linked_device_id = Column(String(64), ForeignKey("devices.id"), nullable=True, index=True)
    linked_service_id = Column(String(64), ForeignKey("business_services.id"), nullable=True)
    linked_alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    severity_policy_reason = Column(Text, default="")
    evidence_json = Column(Text, default="{}")
    mitigation_notes = Column(Text, default="")
    resolution_notes = Column(Text, default="")
    version = Column(Integer, default=1, nullable=False)
    created_by = Column(String(64), default="system")
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)


class IncidentTimelineEvent(Base):
    __tablename__ = "incident_timeline"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    incident_id = Column(String(64), ForeignKey("enterprise_incidents.id"), nullable=False, index=True)
    event_type = Column(String(48), nullable=False)
    actor_username = Column(String(64), nullable=False)
    note = Column(Text, default="")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now, index=True)


class IncidentPostmortem(Base):
    __tablename__ = "incident_postmortems"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    incident_id = Column(String(64), ForeignKey("enterprise_incidents.id"), unique=True, nullable=False, index=True)
    impact_summary = Column(Text, nullable=False)
    timeline_summary = Column(Text, default="")
    root_cause_findings = Column(Text, default="")
    contributing_factors = Column(Text, default="")
    detection_method = Column(String(128), default="Telemetry / SLO Monitor")
    resolution_summary = Column(Text, default="")
    preventive_actions = Column(Text, default="")
    follow_up_owner = Column(String(64), nullable=True)
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# PHASE E: ITSM INTEGRATION FRAMEWORK
# ==============================================================================

class ITSMIntegration(Base):
    __tablename__ = "itsm_integrations"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)  # SERVICENOW, JIRA_SM, WEBHOOK
    name = Column(String(128), nullable=False)
    endpoint_url = Column(String(512), default="")
    auth_type = Column(String(32), default="BEARER")
    secret_encrypted_or_ref = Column(String(512), default="")
    status = Column(String(24), default="NOT_CONFIGURED")  # NOT_CONFIGURED, CONFIGURED, CONNECTED, ERROR
    field_mapping_json = Column(Text, default="{}")
    priority_mapping_json = Column(Text, default="{}")
    policy_json = Column(Text, default="{}")
    last_tested_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class ExternalTicketMapping(Base):
    __tablename__ = "external_ticket_mappings"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    integration_id = Column(String(64), ForeignKey("itsm_integrations.id"), nullable=False, index=True)
    incident_id = Column(String(64), ForeignKey("enterprise_incidents.id"), nullable=False, index=True)
    external_ticket_id = Column(String(128), nullable=False)
    external_status = Column(String(48), default="OPEN")
    idempotency_key = Column(String(128), unique=True, nullable=False)
    response_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


# ==============================================================================
# PHASE F & G: FINOPS, COST INTELLIGENCE & PROCUREMENT
# ==============================================================================

class BillingRecord(Base):
    __tablename__ = "billing_records"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    provider = Column(String(64), nullable=False)
    billing_account = Column(String(128), default="default")
    resource_id = Column(String(128), nullable=False, index=True)
    service_name = Column(String(128), default="Block Storage")
    region = Column(String(64), default="global")
    billing_period = Column(String(16), nullable=False, index=True)  # YYYY-MM
    currency = Column(String(8), default="USD")
    billed_cost = Column(Float, nullable=False)
    effective_cost = Column(Float, nullable=True)
    quantity = Column(Float, default=0.0)
    pricing_unit = Column(String(32), default="GB-Month")
    tags_json = Column(Text, default="{}")
    cost_centre = Column(String(64), default="UNALLOCATED")
    source_reference = Column(String(128), default="manual")
    focus_version = Column(String(16), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class CostAllocationRule(Base):
    __tablename__ = "cost_allocations"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    target_type = Column(String(32), nullable=False)  # DEVICE, SITE, CLUSTER, APPLICATION
    target_id = Column(String(64), nullable=False, index=True)
    department = Column(String(64), nullable=False)
    cost_centre = Column(String(64), nullable=False)
    allocation_pct = Column(Float, default=100.0)
    created_by = Column(String(64), default="system")
    created_at = Column(DateTime, default=utc_now)


class StorageBudget(Base):
    __tablename__ = "budgets"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    scope_type = Column(String(32), default="ORGANISATION")
    scope_id = Column(String(64), nullable=False)
    period = Column(String(16), nullable=False)  # YYYY-MM or YYYY
    currency = Column(String(8), default="USD")
    budget_amount = Column(Float, nullable=False)
    created_by = Column(String(64), default="system")
    created_at = Column(DateTime, default=utc_now)


class ProcurementPlan(Base):
    __tablename__ = "procurement_plans"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    storage_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    vendor = Column(String(128), default="Enterprise Storage Vendor")
    product_type = Column(String(64), default="NVMe Expansion Shelf")
    lead_time_days = Column(Integer, default=30)
    min_order_tb = Column(Float, default=10.0)
    requested_capacity_tb = Column(Float, nullable=False)
    estimated_cost = Column(Float, nullable=True)
    currency = Column(String(8), default="USD")
    suggested_decision_date = Column(DateTime, nullable=True)
    status = Column(String(24), default="PROPOSED")  # DRAFT, PROPOSED, APPROVED, REJECTED
    prepared_by = Column(String(64), nullable=False)
    approved_by = Column(String(64), nullable=True)
    rationale = Column(Text, default="")
    uncertainty_notes = Column(Text, default="")
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


# ==============================================================================
# PHASE H: BACKUP, REPLICATION & DISASTER RECOVERY
# ==============================================================================

class BackupResource(Base):
    __tablename__ = "backup_resources"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    provider = Column(String(64), default="Enterprise Snapshot / S3")
    schedule_cron = Column(String(64), default="0 2 * * *")
    retention_days = Column(Integer, default=30)
    replication_target_site_id = Column(String(64), ForeignKey("sites.id"), nullable=True)
    status = Column(String(24), default="CONFIGURED")
    created_at = Column(DateTime, default=utc_now)


class BackupEvent(Base):
    __tablename__ = "backup_events"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    backup_resource_id = Column(String(64), ForeignKey("backup_resources.id"), nullable=False, index=True)
    status = Column(String(24), nullable=False)  # SUCCESS, FAILED, RUNNING
    backup_size_bytes = Column(BigInteger, default=0)
    completed_at = Column(DateTime, default=utc_now, index=True)
    source_label = Column(String(64), default="backup_agent")


class ReplicationEvent(Base):
    __tablename__ = "replication_events"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    backup_resource_id = Column(String(64), ForeignKey("backup_resources.id"), nullable=False, index=True)
    source_site_id = Column(String(64), nullable=True)
    target_site_id = Column(String(64), nullable=True)
    lag_seconds = Column(Float, nullable=False)
    status = Column(String(24), default="SYNCING")
    recorded_at = Column(DateTime, default=utc_now, index=True)


class RecoveryObjective(Base):
    __tablename__ = "recovery_objectives"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    service_id = Column(String(64), ForeignKey("business_services.id"), nullable=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    rpo_minutes = Column(Integer, default=60)
    rto_minutes = Column(Integer, default=30)
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    procedure_doc = Column(Text, default="")
    last_tested_at = Column(DateTime, nullable=True)
    last_test_passed = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class RecoverySimulationPlan(Base):
    __tablename__ = "recovery_plans"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    scenario_type = Column(String(48), nullable=False)  # SITE_OUTAGE, REPLICATION_INTERRUPTION, BACKUP_RESTORE, ALTERNATE_SITE, CAPACITY_SHORTAGE
    target_site_id = Column(String(64), nullable=True)
    assumptions_json = Column(Text, default="{}")
    results_json = Column(Text, default="{}")
    rpo_achievable = Column(Boolean, default=False)
    rto_achievable = Column(Boolean, default=False)
    approval_status = Column(String(24), default="DRAFT")
    created_by = Column(String(64), nullable=False)
    approved_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# PHASE I: GOVERNANCE & POLICY MANAGEMENT (NIST CSF 2.0 MAPPED)
# ==============================================================================

class GovernancePolicy(Base):
    __tablename__ = "governance_policies"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    policy_code = Column(String(48), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, default="")
    category = Column(String(48), nullable=False)  # ACCESS_MANAGEMENT, DATA_SECURITY, STORAGE_CAPACITY, BACKUP_REQUIREMENTS, RESOURCE_OWNERSHIP, etc.
    nist_control_ref = Column(String(64), default="PR.DS-01")
    scope_type = Column(String(32), default="DEVICE")
    condition_json = Column(Text, default="{}")
    severity = Column(String(24), default="HIGH")
    required_action = Column(Text, default="")
    owner_user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    effective_date = Column(DateTime, default=utc_now)
    review_date = Column(DateTime, nullable=True)
    approval_status = Column(String(24), default="APPROVED")
    created_at = Column(DateTime, default=utc_now)


class PolicyEvaluation(Base):
    __tablename__ = "policy_evaluations"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    policy_id = Column(String(64), ForeignKey("governance_policies.id"), nullable=False, index=True)
    resource_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False)  # COMPLIANT, NON_COMPLIANT, NOT_EVALUATED, INSUFFICIENT_EVIDENCE, EXEMPT_WITH_APPROVAL
    evidence_json = Column(Text, default="{}")
    evaluated_at = Column(DateTime, default=utc_now, index=True)


class PolicyException(Base):
    __tablename__ = "policy_exceptions"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    policy_id = Column(String(64), ForeignKey("governance_policies.id"), nullable=False, index=True)
    resource_id = Column(String(64), nullable=False)
    justification = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    approval_status = Column(String(24), default="PENDING")  # PENDING, APPROVED, REJECTED
    requested_by = Column(String(64), nullable=False)
    approved_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now)


# ==============================================================================
# PHASE J & K: FORECAST OUTCOME & DECISION FEEDBACK
# ==============================================================================

class ForecastOutcomeRecord(Base):
    __tablename__ = "forecast_outcome_records"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    forecast_id = Column(Integer, ForeignKey("forecasts.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    model_version_id = Column(String(64), nullable=True)
    horizon_days = Column(Integer, default=7)
    workload_regime = Column(String(48), default="STEADY")
    predicted_q50_bytes = Column(BigInteger, nullable=False)
    actual_used_bytes = Column(BigInteger, nullable=False)
    abs_error_bytes = Column(BigInteger, nullable=False)
    within_interval = Column(Boolean, default=True)
    evaluated_at = Column(DateTime, default=utc_now, index=True)


class DecisionOutcomeRecord(Base):
    __tablename__ = "decision_outcome_records"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.id"), nullable=False, index=True)
    action_type = Column(String(48), nullable=False)
    status = Column(String(24), default="PLANNED")  # PLANNED, APPROVED, VERIFIED_COMPLETED
    expected_capacity_delta_bytes = Column(BigInteger, default=0)
    actual_capacity_delta_bytes = Column(BigInteger, nullable=True)
    expected_cost_delta = Column(Float, default=0.0)
    actual_cost_delta = Column(Float, nullable=True)
    expected_runway_days = Column(Float, default=0.0)
    actual_runway_days = Column(Float, nullable=True)
    verified_by = Column(String(64), nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)
    verified_at = Column(DateTime, nullable=True)
