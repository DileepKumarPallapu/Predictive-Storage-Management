const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || (
  typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1"
    ? "/api/v1"
    : "http://localhost:8000/api/v1"
);

export interface SystemHealth {
  status: string;
  version: string;
  mode: string;
  database: string;
  collector_status: string;
  models_loaded: number;
  timestamp: string;
}

export interface DeviceSummary {
  id: string;
  name: string;
  tier: string;
  media_type: string;
  total_capacity_bytes: number;
  warning_threshold_pct: number;
  critical_threshold_pct: number;
  max_acceptable_latency_ms: number;
  min_free_reserve_pct: number;
  status: string;
  workload_profile: string;
  current_used_bytes: number;
  current_utilization_pct: number;
  current_read_iops: number;
  current_write_iops: number;
  current_latency_p95_ms: number;
  runway_hours_estimate: number;
  risk_level: string;
}

export interface TelemetryResponse {
  device_id: string;
  metric: string;
  total_capacity_bytes: number;
  is_synthetic: boolean;
  timestamps: string[];
  values: number[];
  units: string;
  missing_intervals: { from: string; to: string; missing_hours: number }[];
}

export interface ForecastResponse {
  device_id: string;
  target_metric: string;
  model_name: string;
  forecast_horizon_hours: number;
  generated_at: string;
  historical_cutoff: string;
  timestamps: string[];
  q10: number[];
  q50: number[];
  q90: number[];
  units: string;
  hard_constraint_value: number | null;
  interval_coverage: number;
  inference_latency_ms: number;
}

export interface RiskContributor {
  factor: string;
  impact_score: number;
}

export interface RiskResponse {
  device_id: string;
  computed_at: string;
  current_capacity_pct: number;
  runway_hours_estimate: number;
  runway_hours_lower_bound: number;
  runway_hours_upper_bound: number;
  risk_level: string;
  capacity_breach_prob_24h: number;
  capacity_breach_prob_72h: number;
  latency_breach_prob_24h: number;
  risk_contributors: RiskContributor[];
}

export interface ScenarioSimulationResponse {
  scenario_id: string;
  device_id: string;
  name: string;
  action_type: string;
  parameters: Record<string, any>;
  duration_minutes: number;
  estimated_cost_usd: number;
  overhead_io_penalty_pct: number;
  safety_envelope_passed: boolean;
  violation_reasons: string[];
  residual_risk_score: number;
  assumptions: string[];
  timeline_timestamps: string[];
  baseline_q50: number[];
  counterfactual_q50: number[];
  hard_limit: number;
  is_simulated_estimate: boolean;
}

export interface RecommendationItem {
  id: string;
  device_id: string;
  action_type: string;
  title: string;
  rationale: string;
  rank: number;
  utility_score: number;
  estimated_runway_gain_hours: number;
  hard_constraints_checked: boolean;
  approval_status: string;
  reviewed_by?: string;
  review_notes?: string;
  created_at: string;
}

export interface AlertItem {
  id: string;
  device_id: string;
  category: string;
  severity: string;
  title: string;
  message: string;
  status: string;
  triggered_at: string;
  resolved_at?: string;
}

export interface ExperimentItem {
  id: string;
  name: string;
  dataset_name: string;
  model_type: string;
  horizon_hours: number;
  train_samples: number;
  test_samples: number;
  mae: number;
  rmse: number;
  pinball_loss: number;
  interval_coverage: number;
  mean_interval_width: number;
  created_at: string;
  manifest: Record<string, any>;
}

export interface OracleWorkloadItem {
  id: string;
  name: string;
  target_device_id: string;
  tier: string;
  workload_type: string;
  priority: string;
  sla_max_latency_ms: number;
  sla_min_throughput_mb_s: number;
  owner_team: string;
  is_active: boolean;
  attribution_available: boolean;
  description: string;
  latest_telemetry?: {
    allocated_gb: number;
    read_iops: number;
    write_iops: number;
    throughput_mb_s: number;
    latency_p95_ms: number;
    queue_depth: number;
    data_freshness_timestamp: string;
  };
}

export interface OracleAttributionResponse {
  device_id: string;
  device_name: string;
  evaluation_window_hours: number;
  device_aggregate_used_gb: number;
  total_attributed_gb: number;
  residual_unattributed_gb: number;
  attribution_coverage_pct: number;
  reconciliation_status: string;
  workload_breakdown: Array<{
    workload_id: string;
    workload_name: string;
    workload_type: string;
    priority: string;
    current_allocated_gb: number;
    growth_delta_gb: number;
    current_iops: number;
    current_latency_p95_ms: number;
    attribution_method: string;
    attribution_confidence: number;
  }>;
  statistical_attribution: Array<{
    workload_id: string;
    workload_name: string;
    capacity_growth_share_pct: number;
    iops_contention_share_pct: number;
    composite_attribution_score: number;
    is_causally_proven: boolean;
    method: string;
  }>;
  scientific_disclaimer: string;
}

export interface OracleCapacityForensicsResponse {
  device_id: string;
  window_hours: number;
  current_used_gb: number;
  growth_delta_gb: number;
  growth_rate_gb_per_day: number;
  acceleration_gb_per_day2: number;
  growth_pattern: string;
  historical_timestamps: string[];
  historical_allocated_gb: number[];
  workload_trajectories: Record<string, { name: string; allocated_gb: number[] }>;
  changepoints_detected: Array<{
    timestamp: string;
    type: string;
    delta_gb: number;
    suspected_workload: string;
    confidence: number;
    description: string;
  }>;
  reserve_runway_projection: {
    safe_reserve_ceiling_gb: number;
    projected_days_to_breach: number | null;
    acceleration_adjusted: boolean;
  };
}

export interface OracleBottleneckResponse {
  device_id: string;
  hours: number;
  latency_p95_current_ms: number;
  sla_max_latency_ms: number;
  sla_breached: boolean;
  contention_index: number;
  contention_level: string;
  forensics_findings: Array<{
    signal: string;
    severity: string;
    evidence: string;
    contributing_workloads: string[];
  }>;
  concurrent_background_jobs: Array<{
    workload_id: string;
    workload_name: string;
    type: string;
    potential_contention: string;
  }>;
}

export interface OracleContentionGraphResponse {
  nodes: Array<{
    id: string;
    name: string;
    type: string;
    tier?: string;
    utilization_pct?: number;
    latency_p95_ms?: number;
    priority?: string;
    allocated_gb?: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    relationship: string;
    weight: number;
    contention_level: string;
    causal_status: string;
  }>;
  summary: {
    total_nodes: number;
    total_edges: number;
    suspected_contention_hotspots: number;
    graph_disclaimer: string;
  };
}

export interface OracleHypothesisItem {
  id: string;
  question: string;
  target_resource: string;
  workload_id?: string;
  status: string;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  confounding_variables: string[];
  proposed_evaluation_method: string;
  conclusion?: string;
  reviewer: string;
  evidence_references: string[];
  status_history: Array<{
    status: string;
    timestamp: string;
    reviewer: string;
    rationale: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface OracleBottleneckCaseItem {
  id: string;
  title: string;
  target_device_id: string;
  suspected_workload_id?: string;
  severity: string;
  status: string;
  evidence_summary: string;
  assigned_investigator?: string;
  resolution_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ReliabilityMetrics {
  model_version: string;
  overall_interval_coverage: number;
  target_nominal_coverage: number;
  mean_pinball_loss: number;
  mean_mae_capacity_gb: number;
  mean_mae_latency_ms: number;
  drift_status: string;
  active_drift_alerts: number;
  last_evaluation_timestamp: string;
  is_fallback_active: boolean;
}

export interface DatasetItem {
  id: string;
  name: string;
  dataset_type: string;
  records_count: number;
  missing_rate: number;
  sampling_interval_s: number;
  license: string;
  description: string;
  created_at: string;
}

export interface AuditItem {
  id: number;
  timestamp: string;
  user: string;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, any>;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

// Token storage helpers
export const authStorage = {
  getToken: () => localStorage.getItem("aegisstor_jwt"),
  setToken: (token: string) => localStorage.setItem("aegisstor_jwt", token),
  clearToken: () => localStorage.removeItem("aegisstor_jwt"),
};

// ==========================================
// FLOWSTATE CLIENT QUERY CACHE & DEDUPLICATION (Prompt 16.0)
// ==========================================
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

const queryCache = new Map<string, CacheEntry<any>>();
const inFlightRequests = new Map<string, Promise<any>>();

export interface FetchOptions extends RequestInit {
  ttlMs?: number; // Cache TTL in ms (default 10,000 ms for GET; 0 for mutations)
  forceFresh?: boolean;
}

export function invalidateApiCache(pattern?: string) {
  if (!pattern) {
    queryCache.clear();
  } else {
    for (const key of Array.from(queryCache.keys())) {
      if (key.includes(pattern)) {
        queryCache.delete(key);
      }
    }
  }
}

// Helper fetch wrapper with JWT, caching, in-flight deduplication, and error parsing
async function apiFetch<T>(endpoint: string, options?: FetchOptions): Promise<T> {
  const method = (options?.method || "GET").toUpperCase();
  const isGet = method === "GET";
  const ttlMs = options?.ttlMs ?? (isGet ? 10000 : 0);
  const cacheKey = `${method}:${endpoint}`;

  // 1. Invalidate cache on mutations
  if (!isGet) {
    invalidateApiCache(endpoint.split("/")[1] || "");
  }

  // 2. Return cached response if valid and not force-fresh
  if (isGet && !options?.forceFresh) {
    const cached = queryCache.get(cacheKey);
    if (cached && Date.now() < cached.expiresAt) {
      return cached.data as T;
    }

    // 3. Request deduplication: return existing in-flight promise
    const pending = inFlightRequests.get(cacheKey);
    if (pending) {
      return pending as Promise<T>;
    }
  }

  const token = authStorage.getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options?.headers as Record<string, string>),
  };

  const fetchPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });

      if (!res.ok) {
        let errData = null;
        let errMsg = `HTTP ${res.status}`;
        try {
          errData = await res.json();
          errMsg = errData.detail || errData.message || errMsg;
        } catch {
          errMsg = await res.text();
        }
        throw new ApiError(res.status, errMsg, errData);
      }

      const data = (await res.json()) as T;

      // Cache GET responses
      if (isGet && ttlMs > 0) {
        queryCache.set(cacheKey, {
          data,
          timestamp: Date.now(),
          expiresAt: Date.now() + ttlMs,
        });
      }

      return data;
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, err.message || "Network request failed");
    } finally {
      inFlightRequests.delete(cacheKey);
    }
  })();

  if (isGet) {
    inFlightRequests.set(cacheKey, fetchPromise);
  }

  return fetchPromise;
}

export interface RiskTimelineItem {
  id: string;
  timestamp: string;
  category: string;
  severity: string;
  title: string;
  device_id: string;
  is_forecasted: boolean;
}

export interface ExecutiveOverviewResponse {
  total_capacity_bytes: number;
  total_used_bytes: number;
  total_free_bytes: number;
  capacity_utilization_pct: number;
  estimated_reserve_runway_hours: number;
  monitored_device_count: number;
  highest_current_risk: {
    level: string;
    device_id: string;
  };
  last_successful_collection: string;
  data_mode_label: string;
  is_synthetic: boolean;
  risk_timeline: RiskTimelineItem[];
  top_recommendation?: {
    id: string;
    device_id: string;
    title: string;
    action_type: string;
    utility_score: number;
    estimated_runway_gain_hours: number;
    approval_status: string;
  };
}

export const api = {
  getHealth: () => apiFetch<SystemHealth>("/health"),
  getOverview: () => apiFetch<ExecutiveOverviewResponse>("/overview"),
  setOperatingMode: (mode: string) =>
    apiFetch<{ message: string; mode: string }>("/system/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  getDevices: (tier?: string, status?: string, search?: string) => {
    const params = new URLSearchParams();
    if (tier) params.append("tier", tier);
    if (status) params.append("status", status);
    if (search) params.append("search", search);
    return apiFetch<DeviceSummary[]>(`/devices?${params.toString()}`);
  },

  getDevice: (id: string) => apiFetch<DeviceSummary>(`/devices/${id}`),

  updateThresholds: (id: string, payload: any) =>
    apiFetch(`/devices/${id}/thresholds`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  getTelemetry: (deviceId: string, metric = "used_bytes", hours = 720) =>
    apiFetch<TelemetryResponse>(
      `/devices/${deviceId}/telemetry?metric=${metric}&hours=${hours}`
    ),

  getForecast: (
    deviceId: string,
    metric = "used_bytes",
    model = "lightgbm_quantile",
    horizon = 72
  ) =>
    apiFetch<ForecastResponse>(
      `/devices/${deviceId}/forecasts?target_metric=${metric}&model_type=${model}&horizon_hours=${horizon}`
    ),

  getRisks: (deviceId: string) =>
    apiFetch<RiskResponse>(`/devices/${deviceId}/risks`),

  getReserveRunway: (deviceId: string) =>
    apiFetch<any>(`/devices/${deviceId}/reserve-runway`),

  getRiskAssessment: (deviceId: string) =>
    apiFetch<any>(`/devices/${deviceId}/risk-assessment`),

  evaluatePlanning: (deviceId: string) =>
    apiFetch<any>("/planning/evaluate", {
      method: "POST",
      body: JSON.stringify({ device_id: deviceId }),
    }),

  listScenarios: (deviceId?: string) =>
    apiFetch<any[]>(`/scenarios${deviceId ? `?device_id=${deviceId}` : ""}`),

  getScenario: (scenarioId: string) =>
    apiFetch<any>(`/scenarios/${scenarioId}`),

  rerunScenario: (scenarioId: string, seed = 42) =>
    apiFetch<ScenarioSimulationResponse>(`/scenarios/${scenarioId}/run?seed=${seed}`, {
      method: "POST",
    }),

  getScenarioResults: (scenarioId: string) =>
    apiFetch<any>(`/scenarios/${scenarioId}/results`),

  createScenario: (payload: {
    device_id: string;
    name: string;
    action_type: string;
    parameters: Record<string, any>;
  }) =>
    apiFetch<ScenarioSimulationResponse>("/scenarios", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getRecommendations: (deviceId: string) =>
    apiFetch<RecommendationItem[]>(`/devices/${deviceId}/recommendations`),

  approveRecommendation: (id: string, notes?: string) =>
    apiFetch(`/recommendations/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  rejectRecommendation: (id: string, notes?: string) =>
    apiFetch(`/recommendations/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  getExperiments: () => apiFetch<ExperimentItem[]>("/experiments"),
  getAblationStudies: () => apiFetch<any>("/experiments/ablations"),

  runExperiment: (payload: {
    name: string;
    dataset_name: string;
    model_type: string;
    horizon_hours: number;
  }) =>
    apiFetch<ExperimentItem>("/experiments", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getModelReliability: () =>
    apiFetch<ReliabilityMetrics>("/models/reliability"),

  getAlerts: (category?: string, severity?: string, status?: string) => {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (severity) params.append("severity", severity);
    if (status) params.append("status", status);
    return apiFetch<AlertItem[]>(`/alerts?${params.toString()}`);
  },

  acknowledgeAlert: (id: string) =>
    apiFetch(`/alerts/${id}/acknowledge`, { method: "POST" }),

  resolveAlert: (id: string) =>
    apiFetch(`/alerts/${id}/resolve`, { method: "POST" }),

  getDatasets: () => apiFetch<DatasetItem[]>("/datasets"),

  getSettings: () => apiFetch<any>("/settings"),

  getAuditTrail: () => apiFetch<AuditItem[]>("/audit"),

  // Authentication & RBAC methods
  login: async (username: string, password: string) => {
    const data = await apiFetch<{
      access_token: string;
      token_type: string;
      user_id: string;
      username: string;
      role: string;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    if (data.access_token) {
      authStorage.setToken(data.access_token);
    }
    return data;
  },

  getCurrentUser: () =>
    apiFetch<{
      id: string;
      username: string;
      email: string;
      role: string;
      is_active: boolean;
    }>("/auth/me"),

  logout: () => {
    authStorage.clearToken();
  },

  // ==========================================
  // AEGISSTOR OMEGA FLEET INTELLIGENCE API
  // ==========================================
  getOmegaTopology: () => apiFetch<any>("/omega/topology"),
  getOmegaFleetRisk: () => apiFetch<any>("/omega/fleet-risk"),
  getOmegaDecisionEvaluation: (deviceId = "vol-nvme-tier1-db", horizonHours = 72) =>
    apiFetch<any>(`/omega/decision-evaluation?device_id=${deviceId}&horizon_hours=${horizonHours}`),
  getOmegaAdaptiveMonitoring: (simulationDays = 30) =>
    apiFetch<any>(`/omega/adaptive-monitoring?simulation_days=${simulationDays}`),
  simulateOmegaFleetPlan: (plan: {
    source_device_id: string;
    destination_device_id: string;
    migration_size_gb: number;
    bandwidth_cap_mb_s: number;
  }) =>
    apiFetch<any>("/omega/fleet-plan", {
      method: "POST",
      body: JSON.stringify(plan),
    }),
  getOmegaOutcomeLedger: (limit = 50) =>
    apiFetch<any>(`/omega/outcome-ledger?limit=${limit}`),
  getOmegaGovernance: () => apiFetch<any>("/omega/governance"),
  evaluateOmegaCandidate: (candidate: any) =>
    apiFetch<any>("/omega/governance/evaluate", {
      method: "POST",
      body: JSON.stringify(candidate),
    }),

  // ==========================================
  // AEGISSTOR JURASSIC RESILIENCE LAB API
  // ==========================================
  getJurassicCommandCenter: () => apiFetch<any>("/jurassic/command-center"),
  getJurassicScenarios: (family?: string) => {
    const params = family ? `?family=${family}` : "";
    return apiFetch<any[]>(`/jurassic/scenarios${params}`);
  },
  getJurassicScenario: (id: string) => apiFetch<any>(`/jurassic/scenarios/${id}`),
  createJurassicScenario: (scenario: any) =>
    apiFetch<any>("/jurassic/scenarios", {
      method: "POST",
      body: JSON.stringify(scenario),
    }),
  runJurassicExperiment: (scenarioId: string, targetDeviceId?: string) =>
    apiFetch<any>("/jurassic/experiments/run", {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenarioId, target_device_id: targetDeviceId }),
    }),
  getJurassicExperiments: (limit = 20) =>
    apiFetch<any[]>(`/jurassic/experiments?limit=${limit}`),
  getJurassicExperimentDetails: (id: string) =>
    apiFetch<any>(`/jurassic/experiments/${id}`),
  getJurassicFallbackStates: () => apiFetch<any>("/jurassic/fallback-states"),
  getJurassicReportUrl: (experimentId: string, format: "markdown" | "csv" = "markdown") =>
    `${API_BASE}/jurassic/experiments/${experimentId}/report?format=${format}`,

  // ==========================================
  // AEGISSTOR PHOENIX INCIDENT ORCHESTRATION API
  // ==========================================
  getPhoenixIncidents: (params?: { severity?: string; status?: string; category?: string; device_id?: string }) => {
    const query = new URLSearchParams();
    if (params?.severity) query.append("severity", params.severity);
    if (params?.status) query.append("status", params.status);
    if (params?.category) query.append("category", params.category);
    if (params?.device_id) query.append("device_id", params.device_id);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return apiFetch<any[]>(`/phoenix/incidents${qs}`);
  },
  scanPhoenixIncidents: () =>
    apiFetch<any>("/phoenix/incidents/scan", {
      method: "POST",
    }),
  getPhoenixIncident: (id: string) => apiFetch<any>(`/phoenix/incidents/${id}`),
  transitionPhoenixIncident: (id: string, target_state: string, reason?: string) =>
    apiFetch<any>(`/phoenix/incidents/${id}/transition`, {
      method: "POST",
      body: JSON.stringify({ target_state, reason }),
    }),
  getPhoenixRunbooks: (category?: string) => {
    const qs = category ? `?category=${category}` : "";
    return apiFetch<any[]>(`/phoenix/runbooks${qs}`);
  },
  getPhoenixPolicies: () => apiFetch<any>("/phoenix/policies"),
  createPhoenixProposal: (incidentId: string, payload: any) =>
    apiFetch<any>(`/phoenix/incidents/${incidentId}/proposals`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approvePhoenixProposal: (proposalId: string, reviewerId: string, rationale: string) =>
    apiFetch<any>(`/phoenix/proposals/${proposalId}/approve`, {
      method: "POST",
      body: JSON.stringify({ reviewer_id: reviewerId, rationale }),
    }),
  executePhoenixProposal: (
    proposalId: string,
    idempotencyToken: string,
    executionMode = "MODE_A_SIMULATE"
  ) =>
    apiFetch<any>(`/phoenix/proposals/${proposalId}/execute`, {
      method: "POST",
      body: JSON.stringify({ idempotency_token: idempotencyToken, execution_mode: executionMode }),
    }),
  verifyPhoenixRecovery: (incidentId: string, payload: any = {}) =>
    apiFetch<any>(`/phoenix/incidents/${incidentId}/verify`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPhoenixEvidenceGraph: (incidentId: string) =>
    apiFetch<any>(`/phoenix/incidents/${incidentId}/evidence-graph`),
  getPhoenixRepeatedPatterns: () =>
    apiFetch<any>("/phoenix/analytics/repeated-patterns"),
  getPhoenixExecutions: () => apiFetch<any[]>("/phoenix/executions"),

  // ==========================================
  // AEGISSTOR ATLAS REALITY CALIBRATION API (Prompt 9.0)
  // ==========================================
  getAtlasOverview: () => apiFetch<any>("/atlas/overview"),
  getAtlasCalibrationConfigs: (deviceId?: string) => {
    const qs = deviceId ? `?device_id=${deviceId}` : "";
    return apiFetch<any[]>(`/atlas/calibration/configs${qs}`);
  },
  runAtlasCalibration: (payload: { device_id: string; config_id?: string; simulator_version?: string }) =>
    apiFetch<any>("/atlas/calibration/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAtlasCalibrationRuns: () => apiFetch<any[]>("/atlas/calibration/runs"),
  getAtlasDiscrepancy: (runId: string) => apiFetch<any>(`/atlas/discrepancy/${runId}`),
  getAtlasActionEffects: (deviceId?: string) => {
    const qs = deviceId ? `?device_id=${deviceId}` : "";
    return apiFetch<any[]>(`/atlas/action-effects${qs}`);
  },
  getAtlasFidelity: (deviceId: string) => apiFetch<any>(`/atlas/fidelity/${deviceId}`),
  evaluateAtlasGatedPlan: (payload: { device_id: string; candidates?: any[] }) =>
    apiFetch<any>("/atlas/evidence-gated-plan", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAtlasExperiments: () => apiFetch<any[]>("/atlas/experiments"),
  createAtlasExperiment: (payload: any) =>
    apiFetch<any>("/atlas/experiments", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAtlasVoeGaps: (deviceId?: string) => {
    const qs = deviceId ? `?device_id=${deviceId}` : "";
    return apiFetch<any[]>(`/atlas/voe-gaps${qs}`);
  },

  // ==========================================
  // AEGISSTOR ORACLE WORKLOAD ATTRIBUTION API (Prompt 15.0)
  // ==========================================
  getOracleWorkloads: (targetDeviceId?: string) => {
    const qs = targetDeviceId ? `?target_device_id=${targetDeviceId}` : "";
    return apiFetch<any[]>(`/oracle/workloads${qs}`);
  },
  getOracleAttribution: (deviceId: string, hours = 72) =>
    apiFetch<any>(`/oracle/attribution/${deviceId}?hours=${hours}`),
  getOracleCapacityForensics: (deviceId: string, windowHours = 168) =>
    apiFetch<any>(`/oracle/capacity-forensics/${deviceId}?window_hours=${windowHours}`),
  getOracleBottlenecks: (deviceId: string, hours = 72) =>
    apiFetch<any>(`/oracle/bottlenecks/${deviceId}?hours=${hours}`),
  getOracleContentionGraph: (deviceId?: string) => {
    const qs = deviceId ? `?target_device_id=${deviceId}` : "";
    return apiFetch<any>(`/oracle/contention-graph${qs}`);
  },
  getOracleCases: (status?: string, deviceId?: string) => {
    const params = new URLSearchParams();
    if (status) params.append("status", status);
    if (deviceId) params.append("target_device_id", deviceId);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return apiFetch<any[]>(`/oracle/cases${qs}`);
  },
  updateOracleCase: (caseId: string, payload: { status: string; notes?: string; investigator?: string }) =>
    apiFetch<any>(`/oracle/cases/${caseId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getOracleHypotheses: (targetResource?: string) => {
    const qs = targetResource ? `?target_resource=${targetResource}` : "";
    return apiFetch<any[]>(`/oracle/hypotheses${qs}`);
  },
  createOracleHypothesis: (payload: any) =>
    apiFetch<any>("/oracle/hypotheses", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateOracleHypothesisStatus: (hypothesisId: string, payload: { new_status: string; rationale: string; reviewer: string; conclusion?: string }) =>
    apiFetch<any>(`/oracle/hypotheses/${hypothesisId}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  runOracleCounterfactual: (payload: { target_device_id: string; workload_id: string; intervention_type: string; parameters?: any; horizon_hours?: number }) =>
    apiFetch<any>("/oracle/counterfactual/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getOracleCounterfactualExperiments: (deviceId?: string) => {
    const qs = deviceId ? `?target_device_id=${deviceId}` : "";
    return apiFetch<any[]>(`/oracle/counterfactual/experiments${qs}`);
  },
  getOracleInvestigationReport: (deviceId: string, hypothesisId?: string) => {
    const qs = hypothesisId ? `?hypothesis_id=${hypothesisId}` : "";
    return apiFetch<any>(`/oracle/report/${deviceId}${qs}`);
  },
};

