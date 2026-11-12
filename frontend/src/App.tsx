import React, { useState, useEffect, Suspense, lazy } from 'react';
import { Sidebar, PageId } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { CommandPalette } from './components/CommandPalette';
import { AuthModal } from './components/AuthModal';
import { OnboardingModal } from './components/OnboardingModal';
import { FlowstatePageSkeleton } from './components/FlowstatePageSkeleton';
import { ReplayControlBar } from './components/ReplayControlBar';
import { PresentationModeProvider } from './context/PresentationModeContext';
import { OperatingModeProvider, useOperatingMode } from './context/OperatingModeContext';
import { RealtimeProvider } from './context/RealtimeContext';
import { api } from './api/client';

// Route-Based Code Splitting via React.lazy
const PageExecutiveOverview = lazy(() => import('./pages/PageExecutiveOverview').then(m => ({ default: m.PageExecutiveOverview })));
const PageStorageFleet = lazy(() => import('./pages/PageStorageFleet').then(m => ({ default: m.PageStorageFleet })));
const PageDeviceIntelligence = lazy(() => import('./pages/PageDeviceIntelligence').then(m => ({ default: m.PageDeviceIntelligence })));
const PageStorageDigitalTwin = lazy(() => import('./pages/PageStorageDigitalTwin').then(m => ({ default: m.PageStorageDigitalTwin })));
const PageInterventionStudio = lazy(() => import('./pages/PageInterventionStudio').then(m => ({ default: m.PageInterventionStudio })));
const PageTelemetryExplorer = lazy(() => import('./pages/PageTelemetryExplorer').then(m => ({ default: m.PageTelemetryExplorer })));
const PageMLPredictionLab = lazy(() => import('./pages/PageMLPredictionLab').then(m => ({ default: m.PageMLPredictionLab })));
const PageExperimentWorkbench = lazy(() => import('./pages/PageExperimentWorkbench').then(m => ({ default: m.PageExperimentWorkbench })));
const PageModelReliability = lazy(() => import('./pages/PageModelReliability').then(m => ({ default: m.PageModelReliability })));
const PageAlertsIncidents = lazy(() => import('./pages/PageAlertsIncidents').then(m => ({ default: m.PageAlertsIncidents })));
const PageDatasetsQuality = lazy(() => import('./pages/PageDatasetsQuality').then(m => ({ default: m.PageDatasetsQuality })));
const PageSettingsAudit = lazy(() => import('./pages/PageSettingsAudit').then(m => ({ default: m.PageSettingsAudit })));
const PageDataIngestion = lazy(() => import('./pages/PageDataIngestion').then(m => ({ default: m.PageDataIngestion })));
const PageMLModelCentre = lazy(() => import('./pages/PageMLModelCentre').then(m => ({ default: m.PageMLModelCentre })));
const PageReports = lazy(() => import('./pages/PageReports').then(m => ({ default: m.PageReports })));
const PageAuditLogs = lazy(() => import('./pages/PageAuditLogs').then(m => ({ default: m.PageAuditLogs })));
const PageUserManagement = lazy(() => import('./pages/PageUserManagement').then(m => ({ default: m.PageUserManagement })));
const PageStorageTopology = lazy(() => import('./pages/PageStorageTopology').then(m => ({ default: m.PageStorageTopology })));
const PageLiveTelemetry = lazy(() => import('./pages/PageLiveTelemetry').then(m => ({ default: m.PageLiveTelemetry })));
const PageWorkloadIntelligence = lazy(() => import('./pages/PageWorkloadIntelligence').then(m => ({ default: m.PageWorkloadIntelligence })));
const PageCapacityRiskCentre = lazy(() => import('./pages/PageCapacityRiskCentre').then(m => ({ default: m.PageCapacityRiskCentre })));
const PageDecisionOptimisation = lazy(() => import('./pages/PageDecisionOptimisation').then(m => ({ default: m.PageDecisionOptimisation })));
const PageApprovalCentre = lazy(() => import('./pages/PageApprovalCentre').then(m => ({ default: m.PageApprovalCentre })));
const PageTaskCentre = lazy(() => import('./pages/PageTaskCentre').then(m => ({ default: m.PageTaskCentre })));
const PageIntegrationManagement = lazy(() => import('./pages/PageIntegrationManagement').then(m => ({ default: m.PageIntegrationManagement })));
const PageAuthPortal = lazy(() => import('./pages/PageAuthPortal').then(m => ({ default: m.PageAuthPortal })));
const PageOperatorDashboard = lazy(() => import('./pages/PageOperatorDashboard').then(m => ({ default: m.PageOperatorDashboard })));
const PageViewerDashboard = lazy(() => import('./pages/PageViewerDashboard').then(m => ({ default: m.PageViewerDashboard })));
const PageAccessDenied = lazy(() => import('./pages/PageAccessDenied').then(m => ({ default: m.PageAccessDenied })));
const PageControlPlane = lazy(() => import('./pages/PageControlPlane').then(m => ({ default: m.PageControlPlane })));

import type { AuthPortalMode } from './pages/PageAuthPortal';

const PAGE_TITLES: Record<PageId, string> = {
  admin: 'Administrator Workspace',
  operator: 'Operator Command Workspace',
  viewer: 'Viewer Summary Workspace',
  'access-denied': 'Access Denied (403)',
  overview: 'Overview',
  fleet: 'Storage Systems',
  topology: 'Storage Topology',
  'live-telemetry': 'Live Monitoring',
  ingestion: 'Import Data',
  datasets: 'Data Quality',
  workload: 'Workload Patterns',
  'ml-centre': 'Forecasting Models',
  'ml-lab': 'Capacity Forecasts',
  'risk-centre': 'Capacity Risk',
  telemetry: 'Performance Trends',
  twin: 'Digital Twin (Simulation)',
  optimizer: 'Optimisation',
  interventions: 'Recommendations',
  approvals: 'Approvals',
  tasks: 'Tasks',
  alerts: 'Alerts',
  reports: 'Reports',
  audit: 'Activity Log',
  integrations: 'Data Sources & Connections',
  'control-plane': 'Control Plane',
  settings: 'Settings',
  intelligence: 'Device Details',
  users: 'Users & Roles',
  reliability: 'Forecast Accuracy',
  experiments: 'Ablation Studies',
};

const PAGE_REQUIRED_PERMISSION: Partial<Record<PageId, string>> = {
  admin: 'users.read',
  operator: 'storage.read',
  viewer: 'storage.read',
  overview: 'storage.read',
  fleet: 'storage.read',
  topology: 'storage.read',
  intelligence: 'storage.read',
  'live-telemetry': 'telemetry.read',
  telemetry: 'performance.read',
  ingestion: 'ingestion.preview',
  datasets: 'quality.read',
  workload: 'workload.read',
  'ml-centre': 'models.read',
  'ml-lab': 'forecasts.read',
  'risk-centre': 'risk.read',
  twin: 'digital_twin.read',
  optimizer: 'optimisation.read',
  interventions: 'recommendations.read',
  approvals: 'approvals.read',
  tasks: 'alerts.read',
  alerts: 'alerts.read',
  reports: 'reports.read',
  audit: 'audit.read',
  integrations: 'integrations.read',
  'control-plane': 'control_plane.read',
  settings: 'settings.update',
  users: 'users.read',
  reliability: 'models.read',
  experiments: 'models.read',
};

const PATH_TO_PAGE: Record<string, PageId> = {
  '/admin': 'admin',
  '/operator': 'operator',
  '/viewer': 'viewer',
  '/overview': 'overview',
  '/fleet': 'fleet',
  '/storage': 'fleet',
  '/topology': 'topology',
  '/live-telemetry': 'live-telemetry',
  '/ingestion': 'ingestion',
  '/datasets': 'datasets',
  '/data-quality': 'datasets',
  '/workload': 'workload',
  '/models': 'ml-centre',
  '/ml-centre': 'ml-centre',
  '/forecasts': 'ml-lab',
  '/ml-lab': 'ml-lab',
  '/risk': 'risk-centre',
  '/risk-centre': 'risk-centre',
  '/telemetry': 'telemetry',
  '/twin': 'twin',
  '/optimizer': 'optimizer',
  '/interventions': 'interventions',
  '/recommendations': 'interventions',
  '/approvals': 'approvals',
  '/alerts': 'alerts',
  '/reports': 'reports',
  '/audit': 'audit',
  '/integrations': 'integrations',
  '/settings': 'settings',
  '/users': 'users',
  '/intelligence': 'intelligence',
  '/reliability': 'reliability',
  '/access-denied': 'access-denied',
};

const AUTH_PATHS: Record<string, AuthPortalMode> = {
  '/login': 'login',
  '/forgot-password': 'forgot-password',
  '/reset-password': 'reset-password',
  '/setup': 'setup',
};

function defaultPageForRole(role: string): PageId {
  const r = (role || '').toUpperCase();
  if (r === 'ADMIN') return 'admin';
  if (r === 'OPERATOR') return 'operator';
  if (r === 'VIEWER') return 'viewer';
  return 'overview';
}

const AppContent: React.FC = () => {
  const initialPath = typeof window !== 'undefined' ? window.location.pathname.toLowerCase() : '/';
  const [authStatus, setAuthStatus] = useState<'loading' | 'unauthenticated' | 'authenticated'>('loading');
  const [setupRequired, setSetupRequired] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<AuthPortalMode>(AUTH_PATHS[initialPath] || 'login');
  const [currentUser, setCurrentUser] = useState<{
    username: string;
    role: string;
    email?: string;
    permissions: string[];
    landingRoute: string;
  } | null>(null);
  const [deniedInfo, setDeniedInfo] = useState<{ route: string; requiredPermission?: string } | null>(null);

  const [currentPage, setCurrentPage] = useState<PageId>(PATH_TO_PAGE[initialPath] || 'overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [isLightTheme, setIsLightTheme] = useState<boolean>(() => {
    const v2Key = 'aegisstor_light_default_v2';
    if (!localStorage.getItem(v2Key)) {
      localStorage.setItem(v2Key, 'true');
      localStorage.setItem('aegisstor_theme', 'light');
      return true;
    }
    return localStorage.getItem('aegisstor_theme') !== 'dark';
  });
  const { operatingMode, setOperatingMode, liveDiagnostics } = useOperatingMode();
  const [activeAlertsCount, setActiveAlertsCount] = useState<number>(0);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('vol-nvme-tier1-db');

  // Modals state
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [isAuthOpen, setIsAuthOpen] = useState<boolean>(false);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState<boolean>(() => {
    return !localStorage.getItem('aegisstor_onboarding_completed');
  });

  const navigateUrl = (path: string, replace = false) => {
    if (typeof window === 'undefined') return;
    if (window.location.pathname !== path) {
      if (replace) window.history.replaceState({}, '', path);
      else window.history.pushState({}, '', path);
    }
  };

  const navigateToPage = (page: PageId, permsArg?: string[], roleArg?: string) => {
    const perms = new Set(permsArg ?? currentUser?.permissions ?? []);
    const reqPerm = PAGE_REQUIRED_PERMISSION[page];
    if (reqPerm && perms.size > 0 && !perms.has(reqPerm)) {
      setDeniedInfo({ route: `/${page}`, requiredPermission: reqPerm });
      setCurrentPage('access-denied');
      navigateUrl('/access-denied');
      return;
    }
    // Prevent non-viewers or non-admins from accidentally hitting role-locked home paths without permission
    if (page === 'admin' && (roleArg ?? currentUser?.role)?.toUpperCase() !== 'ADMIN' && !perms.has('users.read')) {
      setDeniedInfo({ route: '/admin', requiredPermission: 'users.read' });
      setCurrentPage('access-denied');
      navigateUrl('/access-denied');
      return;
    }
    setDeniedInfo(null);
    setCurrentPage(page);
    navigateUrl(`/${page}`);
  };

  const handleAuthModeChange = (mode: AuthPortalMode) => {
    setAuthMode(mode);
    navigateUrl(`/${mode}`);
  };

  const checkHealth = async () => {
    try {
      const alerts = await api.getAlerts(undefined, undefined, 'ACTIVE');
      setActiveAlertsCount(alerts.length);
    } catch {
      // Unauthenticated or empty alerts
    }
  };

  const checkAuth = async () => {
    try {
      const status = await api.getSetupStatus();
      if (status.setup_required) {
        setSetupRequired(true);
        setAuthStatus('unauthenticated');
        setCurrentUser(null);
        setAuthMode('setup');
        navigateUrl('/setup', true);
        return;
      }
      setSetupRequired(false);
    } catch {
      // Backend setup-status check failed; continue to auth verification
    }

    try {
      const profile = await api.getCurrentUser();
      const perms = profile.permissions || [];
      const userObj = {
        username: profile.username,
        role: profile.role,
        email: profile.email,
        permissions: perms,
        landingRoute: profile.landing_route || `/${defaultPageForRole(profile.role)}`,
      };
      setCurrentUser(userObj);
      setAuthStatus('authenticated');
      const requestedPath = typeof window !== 'undefined' ? window.location.pathname.toLowerCase() : '/';
      const mappedPage = PATH_TO_PAGE[requestedPath];
      if (mappedPage && mappedPage !== 'access-denied') {
        navigateToPage(mappedPage, perms, profile.role);
      } else {
        const home = defaultPageForRole(profile.role);
        setCurrentPage(home);
        navigateUrl(`/${home}`, true);
      }
      await checkHealth();
    } catch {
      setCurrentUser(null);
      setAuthStatus('unauthenticated');
      const requestedPath = typeof window !== 'undefined' ? window.location.pathname.toLowerCase() : '/';
      if (AUTH_PATHS[requestedPath]) {
        setAuthMode(AUTH_PATHS[requestedPath]);
      } else {
        setAuthMode('login');
        navigateUrl('/login', true);
      }
    }
  };

  const currentUserRef = React.useRef(currentUser);
  currentUserRef.current = currentUser;

  useEffect(() => {
    checkAuth();

    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    const handleAuthExpired = () => {
      setCurrentUser(null);
      setAuthStatus('unauthenticated');
      setAuthMode('login');
      navigateUrl('/login', true);
    };
    const handlePopState = () => {
      const p = window.location.pathname.toLowerCase();
      if (AUTH_PATHS[p]) {
        setAuthMode(AUTH_PATHS[p]);
      } else if (PATH_TO_PAGE[p] && currentUserRef.current) {
        navigateToPage(PATH_TO_PAGE[p], currentUserRef.current.permissions, currentUserRef.current.role);
      }
    };

    const handleRealtimeEvent = (e: Event) => {
      const evt = (e as CustomEvent<any>).detail;
      if (!evt?.event_type) return;
      if (evt.event_type.startsWith('alert.') || evt.event_type.startsWith('storage.')) {
        checkHealth();
      }
      if (evt.event_type === 'permissions.updated' || evt.event_type === 'user.updated') {
        api.getCurrentUser().then((profile) => {
          setCurrentUser((prev) =>
            prev
              ? {
                  ...prev,
                  role: profile.role,
                  permissions: profile.permissions || [],
                }
              : prev,
          );
        }).catch(() => {});
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    window.addEventListener('aegisstor:auth-expired', handleAuthExpired);
    window.addEventListener('popstate', handlePopState);
    window.addEventListener('aegisstor:realtime-event', handleRealtimeEvent);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown);
      window.removeEventListener('aegisstor:auth-expired', handleAuthExpired);
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('aegisstor:realtime-event', handleRealtimeEvent);
    };
  }, []);

  useEffect(() => {
    if (isLightTheme) {
      document.documentElement.classList.add('light-theme');
      document.documentElement.classList.remove('dark');
      document.documentElement.style.colorScheme = 'light';
      localStorage.setItem('aegisstor_theme', 'light');
    } else {
      document.documentElement.classList.remove('light-theme');
      document.documentElement.classList.add('dark');
      document.documentElement.style.colorScheme = 'dark';
      localStorage.setItem('aegisstor_theme', 'dark');
    }
  }, [isLightTheme]);

  const handleAuthenticated = async () => {
    const profile = await api.getCurrentUser();
    const perms = profile.permissions || [];
    setCurrentUser({
      username: profile.username,
      role: profile.role,
      email: profile.email,
      permissions: perms,
      landingRoute: profile.landing_route || `/${defaultPageForRole(profile.role)}`,
    });
    setAuthStatus('authenticated');
    const home = defaultPageForRole(profile.role);
    setCurrentPage(home);
    navigateUrl(`/${home}`);
    await checkHealth();
  };

  const handleLogout = async () => {
    await api.logout();
    setCurrentUser(null);
    setAuthStatus('unauthenticated');
    setAuthMode('login');
    navigateUrl('/login');
  };

  const handleModeChange = async (newMode: string) => {
    await setOperatingMode(newMode as any);
  };

  const handleToggleTheme = () => {
    setIsLightTheme((prev) => !prev);
  };

  const handleCloseOnboarding = () => {
    setIsOnboardingOpen(false);
    localStorage.setItem('aegisstor_onboarding_completed', 'true');
  };

  const handleNavigateToDevice = (devId: string) => {
    setSelectedDeviceId(devId);
    navigateToPage('intelligence');
  };

  const handleNavigateToTwin = (devId: string) => {
    setSelectedDeviceId(devId);
    navigateToPage('twin');
  };

  const handleOperatorDeepLink = (tab: string, devId?: string) => {
    if (devId) setSelectedDeviceId(devId);
    const tabMap: Record<string, PageId> = {
      devices: 'fleet',
      fleet: 'fleet',
      ingestion: 'ingestion',
      telemetry: 'live-telemetry',
      'data-quality': 'datasets',
      models: 'ml-centre',
      forecasts: 'ml-lab',
      risk: 'risk-centre',
      twin: 'twin',
      alerts: 'alerts',
      reports: 'reports',
      recommendations: 'interventions',
      approvals: 'approvals',
    };
    navigateToPage(tabMap[tab] || (tab as PageId));
  };

  if (authStatus === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-canvas)] text-xs text-[var(--text-secondary)]">
        Verifying AEGISSTOR security session...
      </div>
    );
  }

  if (authStatus === 'unauthenticated' || !currentUser || setupRequired) {
    return (
      <Suspense fallback={<FlowstatePageSkeleton />}>
        <PageAuthPortal
          mode={authMode}
          onNavigateMode={handleAuthModeChange}
          onAuthenticated={handleAuthenticated}
          setupRequired={setupRequired}
          onSetupComplete={() => setSetupRequired(false)}
        />
      </Suspense>
    );
  }

  return (
    <RealtimeProvider authenticated={authStatus === 'authenticated'} currentRoute={`/${currentPage}`}>
      <div className={`min-h-screen flex ${isLightTheme ? 'light-theme' : ''} bg-transparent text-[var(--text-primary)] transition-colors duration-200`}>
      {/* Sidebar Navigation (Permission-Filtered Role Sections) */}
      <Sidebar
        currentPage={currentPage}
        onSelectPage={(p) => navigateToPage(p)}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeAlertsCount={activeAlertsCount}
        currentUserRole={currentUser.role}
        userPermissions={currentUser.permissions}
        onOpenOnboarding={() => setIsOnboardingOpen(true)}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Top Command Bar */}
        <TopBar
          currentMode={operatingMode}
          onModeChange={handleModeChange}
          isLightTheme={isLightTheme}
          onToggleTheme={handleToggleTheme}
          activeAlertsCount={activeAlertsCount}
          onOpenAlerts={() => navigateToPage('alerts')}
          onOpenSearch={() => setIsSearchOpen(true)}
          onOpenAuth={() => setIsAuthOpen(true)}
          onOpenTour={() => setIsOnboardingOpen(true)}
          currentUser={currentUser}
          currentPageLabel={PAGE_TITLES[currentPage] || 'Operations Overview'}
          onToggleMobileMenu={() => setMobileMenuOpen((prev) => !prev)}
        />

        {/* Trace Replay Control Bar */}
        <ReplayControlBar />

        {/* Live Passive Host Status / Diagnostic Banner */}
        {operatingMode === 'live' && (
          <div className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] px-4 sm:px-6 py-2 flex items-center justify-between text-xs animate-in fade-in">
            <div className="flex items-center gap-2 text-[var(--text-secondary)]">
              <span className="w-2 h-2 rounded-full bg-[var(--status-success)] animate-pulse" />
              <span className="font-bold text-[var(--text-primary)]">Live Passive Mode Active:</span>
              <span>Reading host drive (C:\) with strict zero-mutation guarantees.</span>
              {liveDiagnostics && !liveDiagnostics.prometheus_operational && (
                <span className="text-[var(--status-warning)] hidden md:inline ml-2 font-mono text-[11px]">
                  (Prometheus Node Exporter unreachable on :9100; native host OS collector active)
                </span>
              )}
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/30">
              NON-DESTRUCTIVE
            </span>
          </div>
        )}

        {/* Page Container */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            <Suspense fallback={<FlowstatePageSkeleton />}>
              {currentPage === 'access-denied' && (
                <PageAccessDenied
                  attemptedRoute={deniedInfo?.route || '/restricted'}
                  userRole={currentUser.role}
                  requiredPermission={deniedInfo?.requiredPermission}
                  onReturnHome={() => navigateToPage(defaultPageForRole(currentUser.role))}
                />
              )}
              {currentPage === 'admin' && (
                <div className="space-y-6">
                  <div className="titan-card rounded-xl p-4 border border-[var(--accent)]/30 bg-[var(--brand-soft)]/25 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--accent)] font-bold">
                        ADMINISTRATOR WORKSPACE
                      </div>
                      <div className="text-sm font-bold text-[var(--text-primary)]">
                        Platform Governance, User Provisioning, RBAC Matrix & Fleet Resilience
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => navigateToPage('users')}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white"
                      >
                        Manage Users & RBAC Matrix
                      </button>
                      <button
                        type="button"
                        onClick={() => navigateToPage('settings')}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-[var(--border-strong)] bg-[var(--surface-primary)]"
                      >
                        Security Policies
                      </button>
                      <button
                        type="button"
                        onClick={() => navigateToPage('tasks')}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-[var(--border-strong)] bg-[var(--surface-primary)]"
                      >
                        Operational Tasks
                      </button>
                      <button
                        type="button"
                        onClick={() => navigateToPage('audit')}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-[var(--border-strong)] bg-[var(--surface-primary)]"
                      >
                        Audit Ledger
                      </button>
                    </div>
                  </div>
                  <PageExecutiveOverview
                    onNavigateToDevice={handleNavigateToDevice}
                    onNavigateToTwin={handleNavigateToTwin}
                  />
                </div>
              )}
              {currentPage === 'operator' && (
                <PageOperatorDashboard
                  onNavigate={handleOperatorDeepLink}
                  selectedDeviceId={selectedDeviceId}
                />
              )}
              {currentPage === 'viewer' && (
                <PageViewerDashboard onNavigate={handleOperatorDeepLink} />
              )}
              {currentPage === 'overview' && (
                <PageExecutiveOverview
                  onNavigateToDevice={handleNavigateToDevice}
                  onNavigateToTwin={handleNavigateToTwin}
                />
              )}
              {currentPage === 'fleet' && (
                <PageStorageFleet onNavigateToIntelligence={handleNavigateToDevice} />
              )}
              {currentPage === 'topology' && (
                <PageStorageTopology onSelectDevice={handleNavigateToDevice} />
              )}
              {currentPage === 'live-telemetry' && <PageLiveTelemetry />}
              {currentPage === 'workload' && <PageWorkloadIntelligence />}
              {currentPage === 'risk-centre' && <PageCapacityRiskCentre />}
              {currentPage === 'optimizer' && <PageDecisionOptimisation />}
              {currentPage === 'approvals' && <PageApprovalCentre />}
              {currentPage === 'tasks' && (
                <PageTaskCentre
                  currentUserRole={currentUser.role}
                  currentUsername={currentUser.username}
                />
              )}
              {currentPage === 'integrations' && <PageIntegrationManagement />}
              {currentPage === 'control-plane' && (
                <PageControlPlane
                  currentUserRole={currentUser.role}
                  userPermissions={currentUser.permissions || []}
                />
              )}
              {currentPage === 'intelligence' && (
                <PageDeviceIntelligence
                  deviceId={selectedDeviceId}
                  onSelectDevice={setSelectedDeviceId}
                  onLaunchTwin={handleNavigateToTwin}
                />
              )}
              {currentPage === 'twin' && (
                <PageStorageDigitalTwin initialDeviceId={selectedDeviceId} />
              )}
              {currentPage === 'interventions' && (
                <PageInterventionStudio initialDeviceId={selectedDeviceId} />
              )}
              {currentPage === 'telemetry' && <PageTelemetryExplorer />}
              {currentPage === 'ml-lab' && <PageMLPredictionLab />}
              {currentPage === 'experiments' && <PageExperimentWorkbench />}
              {currentPage === 'reliability' && <PageModelReliability />}
              {currentPage === 'alerts' && <PageAlertsIncidents />}
              {currentPage === 'datasets' && <PageDatasetsQuality />}
              {currentPage === 'ingestion' && <PageDataIngestion />}
              {currentPage === 'ml-centre' && <PageMLModelCentre />}
              {currentPage === 'reports' && <PageReports />}
              {currentPage === 'audit' && <PageAuditLogs />}
              {currentPage === 'users' && <PageUserManagement currentUserRole={currentUser.role} />}
              {currentPage === 'settings' && <PageSettingsAudit />}
            </Suspense>
          </div>
        </main>
      </div>

      {/* Quick Search Palette (Ctrl+K) */}
      <CommandPalette
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onNavigatePage={(p) => navigateToPage(p)}
        onNavigateDevice={(id) => handleNavigateToDevice(id)}
      />

      {/* Identity & Session Security Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        currentUser={currentUser}
        onLogoutSuccess={handleLogout}
      />

      {/* Interactive 6-Step Onboarding Modal */}
      <OnboardingModal
        isOpen={isOnboardingOpen}
        onClose={handleCloseOnboarding}
        currentMode={operatingMode}
        onSelectMode={handleModeChange}
      />
      </div>
    </RealtimeProvider>
  );
};

export const App: React.FC = () => {
  return (
    <PresentationModeProvider>
      <OperatingModeProvider>
        <AppContent />
      </OperatingModeProvider>
    </PresentationModeProvider>
  );
};

export default App;
