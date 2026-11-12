const getInitialApiBase = (): string => {
  const envUrl = (import.meta as any).env?.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim() !== "") {
    const trimmed = envUrl.trim().replace(/\/+$/, "");
    return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
  }
  if (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
    return "/api/v1";
  }
  const host = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
  return `http://${host}:8000/api/v1`;
};

const API_BASE = getInitialApiBase();

export function getWebSocketUrl(token?: string | null, sinceSeq?: number | null, route?: string): string {
  let wsBase: string;
  if (API_BASE.startsWith("http://") || API_BASE.startsWith("https://")) {
    wsBase = API_BASE.replace(/^http/, "ws");
  } else {
    const proto = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = typeof window !== "undefined" ? window.location.host : "127.0.0.1:8000";
    wsBase = `${proto}//${host}${API_BASE}`;
  }
  const params = new URLSearchParams();
  if (token) params.set("token", token);
  if (sinceSeq !== null && sinceSeq !== undefined) params.set("since_seq", String(sinceSeq));
  if (route) params.set("route", route);
  const qs = params.toString();
  return `${wsBase}/realtime/ws${qs ? `?${qs}` : ""}`;
}

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
  version?: number;
  updated_at?: string;
  created_by?: string;
  updated_by?: string;
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
  trust_status?: string;
  status_reason?: string;
  max_metric_psi?: number;
}

export interface SentinelWorkloadMetricDrift {
  psi: number;
  ks_statistic: number;
  ks_p_value: number;
  severity: string;
  reference_distribution: { mean: number; std: number; median: number; p95: number };
  current_distribution: { mean: number; std: number; median: number; p95: number };
}

export interface SentinelForecastVsActualSample {
  timestamp: string;
  actual_used_gb: number;
  predicted_q50_gb: number;
  predicted_q10_gb: number;
  predicted_q90_gb: number;
  absolute_error_gb: number;
  within_interval: boolean;
}

export interface SentinelTrustAssessment {
  evaluation_id: string;
  device_id: string;
  evaluated_at: string;
  trust_status: 'HEALTHY' | 'WATCH' | 'DEGRADED' | 'INSUFFICIENT_EVIDENCE';
  status_reason: string;
  recommended_action: string;
  workload_data_drift: {
    detected: boolean;
    severity: string;
    max_psi: number;
    psi_threshold_moderate: number;
    psi_threshold_critical: number;
    drifted_metrics_count: number;
    drifted_metrics: string[];
    metrics_breakdown: Record<string, SentinelWorkloadMetricDrift>;
  };
  prediction_drift: {
    detected: boolean;
    prediction_psi: number;
    severity: string;
  };
  performance_reliability: {
    deterioration_detected: boolean;
    evaluated_mae_gb: number;
    evaluated_rmse_gb: number;
    evaluated_wape_pct: number;
    empirical_coverage_pct: number;
    target_nominal_coverage_pct: number;
    actual_samples_evaluated: number;
    forecast_vs_actual_samples: SentinelForecastVsActualSample[];
  };
  data_quality: {
    total_telemetry_samples: number;
    reference_window_samples: number;
    evaluation_window_samples: number;
    is_stale: boolean;
    latest_observation_age_hours: number;
    missing_intervals_detected: number;
    missing_intervals: Array<{ from: string; to: string; gap_hours: number }>;
  };
  safe_model_improvement: {
    recalibration_eligible: boolean;
    retraining_eligible: boolean;
    automatic_replacement_blocked: boolean;
    approval_required: string;
    validation_design: string;
    governance_note: string;
  };
}

export interface SentinelTrustHistoryItem {
  id: string;
  device_id: string;
  evaluated_at?: string;
  trust_status: 'HEALTHY' | 'WATCH' | 'DEGRADED' | 'INSUFFICIENT_EVIDENCE';
  status_reason: string;
  data_drift_detected: boolean;
  prediction_drift_detected: boolean;
  performance_degraded: boolean;
  max_metric_psi: number;
  evaluated_mae_gb: number;
  evaluated_rmse_gb: number;
  empirical_coverage_pct: number;
  recommended_action: string;
  details: Record<string, any>;
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

export interface VaultBackupItem {
  id: string;
  created_at: string;
  created_by: string;
  format_version: string;
  database_size_bytes: number;
  database_size_mb: number;
  files_count: number;
  checksum_status: string;
  restoration_status: string;
  last_test_rto_seconds: number | null;
  last_test_rpo_hours: number | null;
  last_test_timestamp: string | null;
  manifest: any;
}

export interface VaultTestRestoreResult {
  status: string;
  backup_id: string;
  measured_rto_seconds: number;
  target_rto_seconds: number;
  rto_sla_met: boolean;
  measured_rpo_hours: number;
  target_rpo_hours: number;
  rpo_sla_met: boolean;
  integrity_check_passed: boolean;
  verified_tables: Record<string, number>;
  tested_at: string;
  safety_guarantee: string;
  error?: string;
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

// Token & CSRF storage helpers
function getCookieValue(name: string): string | null {
  if (typeof document === "undefined") return null;
  const parts = document.cookie.split(";").map((c) => c.trim());
  for (const part of parts) {
    if (part.startsWith(`${name}=`)) {
      return decodeURIComponent(part.slice(name.length + 1));
    }
  }
  return null;
}

export const authStorage = {
  getToken: () => localStorage.getItem("aegisstor_jwt"),
  setToken: (token: string) => localStorage.setItem("aegisstor_jwt", token),
  getCsrfToken: () => getCookieValue("aegisstor_csrf") || localStorage.getItem("aegisstor_csrf"),
  setCsrfToken: (token: string) => {
    if (token) localStorage.setItem("aegisstor_csrf", token);
  },
  clearToken: () => {
    localStorage.removeItem("aegisstor_jwt");
    localStorage.removeItem("aegisstor_csrf");
  },
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
  const csrfToken = !isGet ? authStorage.getCsrfToken() : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    ...(options?.headers as Record<string, string>),
  };

  const fetchPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        credentials: "include",
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
        if (
          res.status === 401 &&
          typeof window !== "undefined" &&
          !endpoint.startsWith("/auth/login") &&
          !endpoint.startsWith("/auth/setup") &&
          !endpoint.startsWith("/auth/forgot-password") &&
          !endpoint.startsWith("/auth/reset-password") &&
          !endpoint.startsWith("/auth/me")
        ) {
          authStorage.clearToken();
          invalidateApiCache();
          window.dispatchEvent(new CustomEvent("aegisstor:auth-expired"));
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

export interface ReplayTraceItem {
  id: string;
  filename: string;
  format: string;
  size_bytes: number;
  is_active: boolean;
}

export interface ReplayStatus {
  has_trace: boolean;
  active_trace_id: string | null;
  active_trace_name: string | null;
  current_frame_index: number;
  total_frames: number;
  progress_pct: number;
  is_playing: boolean;
  playback_speed: number;
  current_timestamp: string | null;
  start_timestamp: string | null;
  end_timestamp: string | null;
  volume_count: number;
  available_traces: ReplayTraceItem[];
}

export const api = {
  getHealth: () => apiFetch<SystemHealth>("/health"),
  getOverview: () => apiFetch<ExecutiveOverviewResponse>("/overview"),
  setOperatingMode: (mode: string) =>
    apiFetch<{ message: string; mode: string; diagnostics?: any }>("/system/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  // Trace Replay Pipeline Controls
  getReplayStatus: () => apiFetch<ReplayStatus>("/replay/status"),
  controlReplay: (action: string, value?: any) =>
    apiFetch<ReplayStatus>("/replay/control", {
      method: "POST",
      body: JSON.stringify({ action, value }),
    }),
  listReplayTraces: () => apiFetch<ReplayTraceItem[]>("/replay/traces"),

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

  getSentinelTrust: (deviceId: string = "vol-nvme-tier1-db", evalHours: number = 168, refHours: number = 336) => {
    const params = new URLSearchParams({
      device_id: deviceId,
      evaluation_window_hours: evalHours.toString(),
      reference_window_hours: refHours.toString(),
    });
    return apiFetch<SentinelTrustAssessment>(`/sentinel/trust?${params.toString()}`);
  },

  getSentinelTrustHistory: (deviceId: string = "vol-nvme-tier1-db", limit: number = 20) =>
    apiFetch<SentinelTrustHistoryItem[]>(`/sentinel/trust/history?device_id=${deviceId}&limit=${limit}`),

  recalibrateSentinelModel: (payload: { device_id: string; adjustment_factor_gamma?: number; notes?: string }) =>
    apiFetch<{ status: string; conformal_adjustment_factor_gamma: number; recalibrated_at: string }>(
      "/sentinel/model/recalibrate",
      { method: "POST", body: JSON.stringify(payload) }
    ),

  evaluateRetrainCandidate: (payload: { device_id: string; candidate_model_type?: string }) =>
    apiFetch<{
      device_id: string;
      candidate_model: string;
      validation_design: string;
      production_model: any;
      candidate_evaluation: any;
      governance_decision: any;
    }>("/sentinel/model/retrain-evaluation", { method: "POST", body: JSON.stringify(payload) }),


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
  getSetupStatus: () =>
    apiFetch<{
      setup_required: boolean;
      active_admin_count: number;
      total_user_count: number;
    }>("/auth/setup-status", { forceFresh: true }),

  setupFirstAdmin: (payload: { username: string; email: string; password: string }) =>
    apiFetch<any>("/auth/setup", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: async (username: string, password: string) => {
    invalidateApiCache();
    const data = await apiFetch<{
      access_token: string;
      token_type: string;
      csrf_token?: string;
      user_id: string;
      username: string;
      email?: string;
      role: string;
      landing_route?: string;
      permissions?: string[];
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    if (data.access_token) {
      authStorage.setToken(data.access_token);
    }
    if (data.csrf_token) {
      authStorage.setCsrfToken(data.csrf_token);
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
      landing_route?: string;
      permissions?: string[];
      last_login_at?: string | null;
      failed_login_attempts?: number;
      locked_until?: string | null;
      password_changed_at?: string | null;
    }>("/auth/me", { forceFresh: true }),

  logout: async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch {
      // Clear local session even if backend token already expired
    }
    authStorage.clearToken();
    invalidateApiCache();
  },

  forgotPassword: (identifier: string) =>
    apiFetch<{ message: string; reset_token?: string; expires_in_minutes?: number }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    }),

  resetPassword: (token: string, new_password: string) =>
    apiFetch<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
    }),

  changePassword: (current_password: string, new_password: string) =>
    apiFetch<{ message: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),

  listSessions: () =>
    apiFetch<{ sessions: any[]; count: number }>("/auth/sessions", { forceFresh: true }),

  revokeSession: (sessionId: string) =>
    apiFetch<{ message: string }>(`/auth/sessions/${sessionId}`, { method: "DELETE" }),

  getLoginHistory: () =>
    apiFetch<{ attempts: any[]; count: number }>("/auth/login-history", { forceFresh: true }),

  getMyPermissions: () =>
    apiFetch<{ role: string; permissions: string[]; landing_route: string }>("/auth/permissions", { forceFresh: true }),

  verifyAuditChain: () =>
    apiFetch<any>("/auth/audit/verify-chain", { forceFresh: true }),

  getOperatorDashboard: () =>
    apiFetch<any>("/operator/dashboard", { forceFresh: true }),

  assignAlert: (alertId: string, assigned_to: string, notes = "") =>
    apiFetch<any>(`/alerts/${alertId}/assign`, {
      method: "POST",
      body: JSON.stringify({ assigned_to, notes }),
    }),

  submitRecommendation: (recId: string, notes = "") =>
    apiFetch<any>(`/recommendations/${recId}/submit`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  // ==========================================
  // MODULE 1-12 ENTERPRISE PLATFORM ENDPOINTS
  // ==========================================
  listUsers: () => apiFetch<any[]>("/users", { forceFresh: true }),
  createUser: (payload: { username: string; email: string; password: string; role: string }) =>
    apiFetch<any>("/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (userId: string, payload: { email?: string; role?: string; is_active?: boolean }) =>
    apiFetch<any>(`/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  revokeUserSessions: (userId: string) =>
    apiFetch<any>(`/users/${userId}/revoke-sessions`, { method: "POST" }),
  triggerUserReset: (userId: string) =>
    apiFetch<any>(`/users/${userId}/trigger-reset`, { method: "POST" }),
  getUserAudit: (userId: string) =>
    apiFetch<any>(`/users/${userId}/audit`, { forceFresh: true }),
  getPermissionCatalog: () =>
    apiFetch<{
      roles: any[];
      permissions: any[];
      role_matrix: Record<string, string[]>;
    }>("/permissions/catalog", { forceFresh: true }),
  updateRolePermissions: (roleName: string, permissions: string[]) =>
    apiFetch<any>(`/permissions/roles/${roleName}`, {
      method: "PUT",
      body: JSON.stringify({ permissions }),
    }),

  createStorage: (payload: any) =>
    apiFetch<DeviceSummary>("/storage", { method: "POST", body: JSON.stringify(payload) }),
  updateStorage: (storageId: string, payload: any) =>
    apiFetch<DeviceSummary>(`/storage/${storageId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteStorage: (storageId: string, confirm = true) =>
    apiFetch<any>(`/storage/${storageId}?confirm=${confirm}`, { method: "DELETE" }),

  getCsvTemplateUrl: () => `${API_BASE}/ingestion/template`,
  previewCsvImport: (csvContent: string, defaultStorageId?: string) => {
    const fd = new FormData();
    fd.append("csv_content", csvContent);
    if (defaultStorageId) fd.append("default_storage_id", defaultStorageId);
    const token = authStorage.getToken();
    const csrf = authStorage.getCsrfToken();
    return fetch(`${API_BASE}/ingestion/csv/preview`, {
      method: "POST",
      credentials: "include",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      },
      body: fd,
    }).then((r) => r.json());
  },
  commitCsvImport: (csvContent: string, defaultStorageId?: string) => {
    const fd = new FormData();
    fd.append("csv_content", csvContent);
    if (defaultStorageId) fd.append("default_storage_id", defaultStorageId);
    const token = authStorage.getToken();
    const csrf = authStorage.getCsrfToken();
    return fetch(`${API_BASE}/ingestion/csv/import`, {
      method: "POST",
      credentials: "include",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      },
      body: fd,
    }).then((r) => r.json());
  },
  manualTelemetryEntry: (payload: any) =>
    apiFetch<any>("/ingestion/manual", { method: "POST", body: JSON.stringify(payload) }),
  getIngestionJobs: (storageId?: string) =>
    apiFetch<any[]>(`/ingestion/jobs${storageId ? `?storage_id=${storageId}` : ""}`),
  getIngestionJobErrors: (jobId: string) =>
    apiFetch<any>(`/ingestion/jobs/${jobId}/errors?format=json`, { forceFresh: true }),
  getDataQuality: (storageId: string) =>
    apiFetch<any>(`/data-quality/${storageId}`),

  trainStorageModels: (storageId: string) =>
    apiFetch<any>(`/models/train/${storageId}`, { method: "POST" }),
  getStorageModels: (storageId: string) =>
    apiFetch<any>(`/models/${storageId}`),
  generateCapacityForecast: (storageId: string, horizonDays: 7 | 30 | 90 = 30) =>
    apiFetch<any>(`/forecasts/generate/${storageId}?horizon_days=${horizonDays}`, { method: "POST" }),
  getSavedForecasts: (storageId: string) =>
    apiFetch<any[]>(`/forecasts/${storageId}`),
  getCapacityRunway: (storageId: string, safetyThresholdPct?: number) =>
    apiFetch<any>(`/forecasts/${storageId}/runway${safetyThresholdPct ? `?safety_threshold_pct=${safetyThresholdPct}` : ""}`),
  getStoragePerformance: (storageId: string, startDate?: string, endDate?: string) => {
    const p = new URLSearchParams();
    if (startDate) p.append("start_date", startDate);
    if (endDate) p.append("end_date", endDate);
    const qs = p.toString() ? `?${p.toString()}` : "";
    return apiFetch<any>(`/performance/${storageId}${qs}`);
  },
  evaluateAlerts: (storageId?: string) =>
    apiFetch<any>(storageId ? `/alerts/evaluate/${storageId}` : "/alerts/evaluate", { method: "POST" }),
  reopenAlert: (alertId: string) =>
    apiFetch<any>(`/alerts/${alertId}/reopen`, { method: "POST" }),
  compareDigitalTwinScenarios: (scenarioIds: string[]) =>
    apiFetch<any>("/digital-twin/compare", { method: "POST", body: JSON.stringify({ scenario_ids: scenarioIds }) }),
  updateDigitalTwinScenario: (scenarioId: string, payload: any) =>
    apiFetch<any>(`/digital-twin/scenarios/${scenarioId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteDigitalTwinScenario: (scenarioId: string) =>
    apiFetch<any>(`/digital-twin/scenarios/${scenarioId}`, { method: "DELETE" }),
  generateRecommendationsForStorage: (storageId: string) =>
    apiFetch<any>(`/recommendations/generate/${storageId}`, { method: "POST" }),
  generateReportUrl: (reportType: string, format: "json" | "csv" | "pdf", storageId?: string) => {
    const p = new URLSearchParams({ report_type: reportType, format });
    if (storageId) p.append("storage_id", storageId);
    return `${API_BASE}/reports/generate?${p.toString()}`;
  },
  downloadAuthenticatedReport: async (reportType: string, format: "csv" | "pdf", storageId?: string, startDate?: string, endDate?: string) => {
    const p = new URLSearchParams({ report_type: reportType, format });
    if (storageId) p.append("storage_id", storageId);
    if (startDate) p.append("start_date", startDate);
    if (endDate) p.append("end_date", endDate);
    const token = authStorage.getToken();
    const res = await fetch(`${API_BASE}/reports/generate?${p.toString()}`, {
      credentials: "include",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!res.ok) {
      throw new ApiError(res.status, `Failed to export ${format.toUpperCase()} report (HTTP ${res.status})`);
    }
    return res.blob();
  },
  previewReportJson: (reportType: string, storageId?: string, startDate?: string, endDate?: string) => {
    const p = new URLSearchParams({ report_type: reportType, format: "json" });
    if (storageId) p.append("storage_id", storageId);
    if (startDate) p.append("start_date", startDate);
    if (endDate) p.append("end_date", endDate);
    return apiFetch<any>(`/reports/generate?${p.toString()}`, { forceFresh: true });
  },
  generateReportJson: (reportType: string, storageId?: string) =>
    apiFetch<any>("/reports/generate", { method: "POST", body: JSON.stringify({ report_type: reportType, format: "json", storage_id: storageId }) }),
  getReportHistory: () => apiFetch<any[]>("/reports/history"),
  updateSettings: (payload: any) =>
    apiFetch<any>("/settings", { method: "PUT", body: JSON.stringify(payload) }),

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

  // ==========================================
  // AEGISSTOR GAUNTLET WORKBENCH (Prompt 18.0)
  // ==========================================
  getGauntletOverview: () => apiFetch<any>("/gauntlet/overview"),
  getGauntletCatalog: () => apiFetch<any[]>("/gauntlet/catalog"),
  runGauntletBenchmark: (payload: { suite_id: string; device_id: string; parameters?: any }) =>
    apiFetch<any>("/gauntlet/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getGauntletRuns: (suiteId?: string) => {
    const qs = suiteId ? `?suite_id=${suiteId}` : "";
    return apiFetch<any[]>(`/gauntlet/runs${qs}`);
  },
  getGauntletRun: (runId: string) => apiFetch<any>(`/gauntlet/runs/${runId}`),
  getGauntletTournament: (deviceId?: string) => {
    const qs = deviceId ? `?device_id=${deviceId}` : "";
    return apiFetch<any>(`/gauntlet/tournament${qs}`);
  },
  getGauntletClaims: () => apiFetch<any[]>("/gauntlet/claims"),
  createGauntletClaim: (payload: any) =>
    apiFetch<any>("/gauntlet/claims", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getGauntletFailures: () => apiFetch<any[]>("/gauntlet/failures"),
  reproduceGauntletRun: (runId: string, payload?: { tolerance_pct: number }) =>
    apiFetch<any>(`/gauntlet/reproduce/${runId}`, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }),
  getGauntletReproductions: () => apiFetch<any[]>("/gauntlet/reproductions"),
  getGauntletExportMarkdownUrl: () => `${API_BASE}/gauntlet/export/markdown`,
  getGauntletExportCsvUrl: () => `${API_BASE}/gauntlet/export/csv`,

  // ==========================================
  // AEGISSTOR SOVEREIGN FEDERATION (Prompt 19.0)
  // ==========================================
  getSovereignOverview: () => apiFetch<any>("/sovereign/overview"),
  getSovereignSites: () => apiFetch<any[]>("/sovereign/sites"),
  registerSovereignSite: (payload: any) =>
    apiFetch<any>("/sovereign/sites", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getSovereignRounds: () => apiFetch<any[]>("/sovereign/rounds"),
  runSovereignRound: (payload: { round_number: number; aggregation_strategy: string; participating_site_ids?: string[]; dp_noise_sigma?: number; dp_clip_norm?: number }) =>
    apiFetch<any>("/sovereign/rounds/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getSovereignTournament: () => apiFetch<any>("/sovereign/tournament"),
  getSovereignPrivacyAudit: () => apiFetch<any>("/sovereign/privacy-audit"),
  runSovereignStressTest: () =>
    apiFetch<any>("/sovereign/stress-test", {
      method: "POST",
    }),
  getSovereignExportMarkdownUrl: () => `${API_BASE}/sovereign/export/markdown`,

  // ==========================================
  // AEGISSTOR VAULT (Disaster Recovery & Backup)
  // ==========================================
  getVaultBackups: () =>
    apiFetch<{ status: string; backups_count: number; backups: VaultBackupItem[] }>("/vault/backups"),
  createVaultBackup: (notes?: string) =>
    apiFetch<{ status: string; backup: any }>("/vault/backups", {
      method: "POST",
      body: JSON.stringify({ notes: notes || "" }),
    }),
  verifyVaultBackupIntegrity: (backupId: string) =>
    apiFetch<{ backup_id: string; checksum_status: string; verified_files: Record<string, boolean>; error?: string }>(
      `/vault/backups/${backupId}/integrity`
    ),
  testVaultIsolatedRestore: (backupId: string) =>
    apiFetch<VaultTestRestoreResult>(`/vault/backups/${backupId}/test-restore`, {
      method: "POST",
    }),
  restoreVaultProduction: (backupId: string, confirmationToken: string) =>
    apiFetch<any>(`/vault/backups/${backupId}/restore-production`, {
      method: "POST",
      body: JSON.stringify({ confirmation_token: confirmationToken }),
    }),

  // ==========================================
  // PATENT-GRADE REAL BACKEND PIPELINE (V2 & OPS)
  // ==========================================
  getStorageTopology: () => apiFetch<any>("/storage/topology", { forceFresh: true }),

  // Connectors & Collectors
  getConnectorTypes: () => apiFetch<{ status: string; permission_mode: string; supported_types: string[] }>("/connectors/types"),
  getConnectors: () => apiFetch<{ connectors: any[]; count: number }>("/connectors", { forceFresh: true }),
  registerConnector: (payload: {
    name: string;
    connector_type: string;
    endpoint_url?: string;
    target_storage_id?: string;
    config?: Record<string, any>;
    is_enabled?: boolean;
  }) =>
    apiFetch<any>("/connectors", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateConnector: (connectorId: string, payload: Record<string, any>) =>
    apiFetch<any>(`/connectors/${connectorId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteConnector: (connectorId: string) =>
    apiFetch<any>(`/connectors/${connectorId}`, {
      method: "DELETE",
    }),
  testConnector: (connectorId: string) =>
    apiFetch<any>(`/connectors/${connectorId}/test`, {
      method: "POST",
    }),
  collectFromConnector: (connectorId: string, payload?: { persist_to_storage_id?: string; mountpoint_filter?: string }) =>
    apiFetch<any>(`/connectors/${connectorId}/collect`, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }),

  // API Keys & Retention
  getApiKeys: () => apiFetch<{ api_keys: any[] }>("/admin/api-keys", { forceFresh: true }),
  createApiKey: (name: string, role: string = "OPERATOR") =>
    apiFetch<any>("/admin/api-keys", {
      method: "POST",
      body: JSON.stringify({ name, role }),
    }),
  revokeApiKey: (keyId: string) =>
    apiFetch<any>(`/admin/api-keys/${keyId}`, {
      method: "DELETE",
    }),
  runRetention: (retentionDays?: number, dryRun: boolean = true) =>
    apiFetch<any>("/admin/retention/run", {
      method: "POST",
      body: JSON.stringify({ retention_days: retentionDays, dry_run: dryRun }),
    }),

  // Telemetry Record Inspector & Explicit Demo Synthetic Generator
  getTelemetryRecords: (storageId?: string, isSynthetic?: boolean, limit: number = 100, offset: number = 0) => {
    const p = new URLSearchParams();
    if (storageId) p.append("storage_id", storageId);
    if (isSynthetic !== undefined) p.append("is_synthetic", String(isSynthetic));
    p.append("limit", String(limit));
    p.append("offset", String(offset));
    return apiFetch<any>(`/telemetry/records?${p.toString()}`, { forceFresh: true });
  },
  generateSyntheticDemo: (storageId: string, hours: number = 96, regime: string = "STABLE_GROWTH") =>
    apiFetch<any>("/telemetry/synthetic/generate", {
      method: "POST",
      body: JSON.stringify({ storage_id: storageId, hours, regime }),
    }),

  // 9-Factor Data Reliability Engine
  getDataReliability: (storageId: string) => apiFetch<any>(`/reliability/data/${storageId}`, { forceFresh: true }),
  evaluateDataReliability: (storageId: string, weights?: Record<string, number>) =>
    apiFetch<any>(`/reliability/data/${storageId}`, {
      method: "POST",
      body: JSON.stringify({ weights }),
    }),

  // Workload Regime & Drift Engine
  getWorkloadRegime: (storageId: string) => apiFetch<any>(`/workload-regime/${storageId}`, { forceFresh: true }),
  analyzeWorkloadRegime: (storageId: string) =>
    apiFetch<any>(`/workload-regime/${storageId}`, {
      method: "POST",
    }),

  // V2 Champion-Challenger ML & Multi-Horizon Split Conformal Forecasts
  getV2ModelsByFamily: () => apiFetch<any>("/v2/models/by-family", { forceFresh: true }),
  getV2ModelsForStorage: (storageId: string) => apiFetch<any>(`/v2/models/${storageId}`, { forceFresh: true }),
  getV2FleetReliability: () => apiFetch<any>("/v2/models/reliability", { forceFresh: true }),
  trainV2ChampionChallenger: (storageId: string) =>
    apiFetch<any>(`/v2/models/train/${storageId}`, {
      method: "POST",
    }),
  trainV2ChampionChallengerAsync: (storageId: string) =>
    apiFetch<any>(`/v2/models/train-async/${storageId}`, {
      method: "POST",
    }),
  getBackgroundJobStatus: (jobId: string) => apiFetch<any>(`/jobs/${jobId}`, { forceFresh: true }),
  generateV2Forecast: (storageId: string, horizonDays: number = 30, persist: boolean = true) =>
    apiFetch<any>(`/v2/forecasts/generate/${storageId}`, {
      method: "POST",
      body: JSON.stringify({ horizon_days: horizonDays, persist }),
    }),
  getV2ForecastHistory: (storageId: string, limit: number = 15) =>
    apiFetch<any>(`/v2/forecasts/${storageId}?limit=${limit}`, { forceFresh: true }),
  runScheduledForecasts: (horizonDays: number = 30) =>
    apiFetch<any>(`/v2/forecasts/schedule?horizon_days=${horizonDays}`, {
      method: "POST",
    }),

  // Probabilistic Capacity Risk Engine
  getCapacityRisk: (storageId: string, horizonDays: number = 30, safetyThresholdPct?: number) => {
    const p = new URLSearchParams({ horizon_days: String(horizonDays) });
    if (safetyThresholdPct !== undefined) p.append("safety_threshold_pct", String(safetyThresholdPct));
    return apiFetch<any>(`/risk/capacity/${storageId}?${p.toString()}`, { forceFresh: true });
  },
  evaluateCapacityRisk: (storageId: string, horizonDays: number = 30, safetyThresholdPct?: number) =>
    apiFetch<any>(`/risk/capacity/${storageId}`, {
      method: "POST",
      body: JSON.stringify({ horizon_days: horizonDays, safety_threshold_pct: safetyThresholdPct }),
    }),

  // Multi-Volume Performance Compare & Constrained Decision Optimizer
  compareStoragePerformance: (storageIds?: string[]) => {
    const qs = storageIds && storageIds.length ? `?storage_ids=${encodeURIComponent(storageIds.join(","))}` : "";
    return apiFetch<any>(`/performance/compare${qs}`, { forceFresh: true });
  },
  optimizeInterventions: (storageId: string, payload: Record<string, any>) =>
    apiFetch<any>(`/digital-twin/optimize/${storageId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Alert Escalation & Recommendation Completion Lifecycle
  escalateAlert: (alertId: string, escalationTier: string = "L2_STORAGE_SRE", reason?: string) =>
    apiFetch<any>(`/alerts/${alertId}/escalate`, {
      method: "POST",
      body: JSON.stringify({ escalation_tier: escalationTier, reason }),
    }),
  completeRecommendation: (recId: string, notes?: string) =>
    apiFetch<any>(`/recommendations/${recId}/complete`, {
      method: "POST",
      body: JSON.stringify({ notes: notes || "Confirmed completed by operator (non-execution advisory)." }),
    }),
  failRecommendation: (recId: string, notes?: string) =>
    apiFetch<any>(`/recommendations/${recId}/fail`, {
      method: "POST",
      body: JSON.stringify({ notes: notes || "Marked failed during operational verification." }),
    }),
  listAllRecommendations: (storageId?: string) => {
    const qs = storageId ? `?storage_id=${encodeURIComponent(storageId)}` : "";
    return apiFetch<{ recommendations: any[]; count: number }>(`/recommendations${qs}`, { forceFresh: true });
  },
  generateRecommendations: (storageId: string) =>
    apiFetch<any>(`/recommendations/generate/${storageId}`, { method: "POST" }),
  getLiveHostTelemetry: () => apiFetch<any>("/telemetry/live-host", { forceFresh: true }),
  scrapePrometheus: (endpointUrl: string, timeoutSeconds: number = 3.0) =>
    apiFetch<any>("/telemetry/prometheus/scrape", {
      method: "POST",
      body: JSON.stringify({ endpoint_url: endpointUrl, timeout_seconds: timeoutSeconds }),
    }),

  // ==========================================
  // REAL-TIME SYNC, PRESENCE, NOTIFICATIONS & TASKS
  // ==========================================
  replayRealtimeEvents: (sinceSeq: number = 0, limit: number = 100) =>
    apiFetch<{ since_seq: number; latest_seq: number; events: any[] }>(
      `/realtime/events?since_seq=${sinceSeq}&limit=${limit}`,
      { forceFresh: true },
    ),
  getLivePresence: () =>
    apiFetch<{ online_count: number; active_connections: number; users: any[] }>(
      "/realtime/presence",
      { forceFresh: true },
    ),
  getSharedActivity: (limit: number = 40) =>
    apiFetch<{ items: any[]; count: number }>(`/realtime/activity?limit=${limit}`, { forceFresh: true }),
  listNotifications: (unreadOnly: boolean = false) =>
    apiFetch<{ unread_count: number; notifications: any[] }>(
      `/notifications?unread_only=${unreadOnly}`,
      { forceFresh: true },
    ),
  markNotificationRead: (notifId: string) =>
    apiFetch<{ status: string; id: string }>(`/notifications/${notifId}/read`, { method: "POST" }),
  markAllNotificationsRead: () =>
    apiFetch<{ status: string; marked_count: number }>("/notifications/read-all", { method: "POST" }),
  listTasks: (statusFilter?: string, assignedToMe: boolean = false) => {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status_filter", statusFilter);
    if (assignedToMe) params.set("assigned_to_me", "true");
    const qs = params.toString();
    return apiFetch<{ tasks: any[]; count: number }>(`/tasks${qs ? `?${qs}` : ""}`, { forceFresh: true });
  },
  createTask: (payload: {
    title: string;
    description?: string;
    priority?: string;
    assigned_to_user_id: string;
    linked_device_id?: string;
    linked_alert_id?: string;
    due_date?: string;
  }) => apiFetch<any>("/tasks", { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (
    taskId: string,
    payload: {
      status?: string;
      priority?: string;
      assigned_to_user_id?: string;
      description?: string;
      expected_version?: number;
    },
  ) => apiFetch<any>(`/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  addTaskComment: (taskId: string, body: string) =>
    apiFetch<any>(`/tasks/${taskId}/comments`, { method: "POST", body: JSON.stringify({ body }) }),

  // Control Plane Foundation (Sprint 1)
  listControlPlaneConnectors: () =>
    apiFetch<{ organization_id: string; connectors: any[] }>("/control-plane/connectors", { forceFresh: true }),
  getControlPlaneConnector: (connectorId: string) =>
    apiFetch<any>(`/control-plane/connectors/${connectorId}`, { forceFresh: true }),
  registerControlPlaneConnector: (payload: {
    name: string;
    provider: string;
    version?: string;
    credential_ref: string;
    metadata?: Record<string, any>;
  }) => apiFetch<any>("/control-plane/connectors", { method: "POST", body: JSON.stringify(payload) }),
  registerControlPlaneCapability: (
    connectorId: string,
    payload: { action_key: string; is_supported?: boolean; dry_run_mode: string; constraints?: Record<string, any> },
  ) =>
    apiFetch<any>(`/control-plane/connectors/${connectorId}/capabilities`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  checkControlPlaneConnectorHealth: (connectorId: string) =>
    apiFetch<any>(`/control-plane/connectors/${connectorId}/health-check`, { method: "POST" }),
  listControlPlaneActionDefinitions: () =>
    apiFetch<{ definitions: any[] }>("/control-plane/action-definitions", { forceFresh: true }),
  updateControlPlaneActionPolicy: (
    actionId: string,
    payload: { requires_approval?: boolean; risk_level?: string; is_active?: boolean },
  ) =>
    apiFetch<any>(`/control-plane/action-definitions/${actionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listControlPlaneActions: (status?: string) =>
    apiFetch<{ organization_id: string; actions: any[] }>(
      `/control-plane/actions${status ? `?status=${encodeURIComponent(status)}` : ""}`,
      { forceFresh: true },
    ),
  createControlPlaneAction: (payload: {
    connector_id: string;
    operation: string;
    resource_type: string;
    resource_id: string;
    resource_version?: number;
    parameters?: Record<string, any>;
    idempotency_key?: string;
  }) => apiFetch<any>("/control-plane/actions", { method: "POST", body: JSON.stringify(payload) }),
  getControlPlaneActionDetail: (actionId: string) =>
    apiFetch<any>(`/control-plane/actions/${actionId}`, { forceFresh: true }),
  runControlPlanePreflight: (actionId: string) =>
    apiFetch<any>(`/control-plane/actions/${actionId}/preflight`, { method: "POST" }),
  submitControlPlaneApproval: (actionId: string) =>
    apiFetch<any>(`/control-plane/actions/${actionId}/submit-approval`, { method: "POST" }),
  approveControlPlaneAction: (actionId: string, comment = "", expectedVersion?: number) =>
    apiFetch<any>(`/control-plane/actions/${actionId}/approve`, {
      method: "POST",
      body: JSON.stringify({ comment, expected_version: expectedVersion }),
    }),
  rejectControlPlaneAction: (actionId: string, comment = "", expectedVersion?: number) =>
    apiFetch<any>(`/control-plane/actions/${actionId}/reject`, {
      method: "POST",
      body: JSON.stringify({ comment, expected_version: expectedVersion }),
    }),
  cancelControlPlaneAction: (actionId: string, reason = "Cancelled", expectedVersion?: number) =>
    apiFetch<any>(`/control-plane/actions/${actionId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason, expected_version: expectedVersion }),
    }),
  executeControlPlaneAction: (actionId: string) =>
    apiFetch<any>(`/control-plane/actions/${actionId}/execute`, { method: "POST" }),
  listControlPlaneLocks: () =>
    apiFetch<{ locks: any[] }>("/control-plane/locks", { forceFresh: true }),
  listControlPlaneAudit: () =>
    apiFetch<{ events: any[] }>("/control-plane/audit", { forceFresh: true }),
};

