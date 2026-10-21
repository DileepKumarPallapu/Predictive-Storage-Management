import React, { useState, useEffect, Suspense, lazy } from 'react';
import { Sidebar, PageId } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { CommandPalette } from './components/CommandPalette';
import { AuthModal } from './components/AuthModal';
import { OnboardingModal } from './components/OnboardingModal';
import { FlowstatePageSkeleton } from './components/FlowstatePageSkeleton';
import { PresentationModeProvider } from './context/PresentationModeContext';
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
const PageOmegaControlRoom = lazy(() => import('./pages/PageOmegaControlRoom').then(m => ({ default: m.PageOmegaControlRoom })));
const PageJurassicLab = lazy(() => import('./pages/PageJurassicLab').then(m => ({ default: m.PageJurassicLab })));
const PagePhoenixOrchestrator = lazy(() => import('./pages/PagePhoenixOrchestrator').then(m => ({ default: m.PagePhoenixOrchestrator })));
const PageAtlasRealityLab = lazy(() => import('./pages/PageAtlasRealityLab').then(m => ({ default: m.PageAtlasRealityLab })));
const PageOracleIntelligence = lazy(() => import('./pages/PageOracleIntelligence').then(m => ({ default: m.PageOracleIntelligence })));

const AppContent: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [isLightTheme, setIsLightTheme] = useState<boolean>(false);
  const [operatingMode, setOperatingMode] = useState<string>('demo');
  const [activeAlertsCount, setActiveAlertsCount] = useState<number>(3);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('vol-nvme-tier1-db');

  // Modals state
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [isAuthOpen, setIsAuthOpen] = useState<boolean>(false);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState<boolean>(() => {
    return !localStorage.getItem('aegisstor_onboarding_completed');
  });

  const [currentUser, setCurrentUser] = useState<{ username: string; role: string }>({
    username: 'admin',
    role: 'ADMIN',
  });

  useEffect(() => {
    checkHealth();
    checkAuth();

    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  useEffect(() => {
    if (isLightTheme) {
      document.documentElement.classList.add('light-theme');
    } else {
      document.documentElement.classList.remove('light-theme');
    }
  }, [isLightTheme]);

  const checkHealth = async () => {
    try {
      const [h, alerts] = await Promise.all([
        api.getHealth(),
        api.getAlerts(undefined, undefined, 'ACTIVE'),
      ]);
      setOperatingMode(h.mode);
      setActiveAlertsCount(alerts.length);
    } catch (e) {
      console.warn("Backend not yet reached, operating in standard demo state:", e);
    }
  };

  const checkAuth = async () => {
    try {
      const profile = await api.getCurrentUser();
      setCurrentUser({ username: profile.username, role: profile.role });
    } catch (e) {
      // Keep default admin fallback in development
    }
  };

  const handleModeChange = async (newMode: string) => {
    try {
      await api.setOperatingMode(newMode);
      setOperatingMode(newMode);
    } catch (e) {
      console.error(e);
      setOperatingMode(newMode);
    }
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
    setCurrentPage('intelligence');
  };

  const handleNavigateToTwin = (devId: string) => {
    setSelectedDeviceId(devId);
    setCurrentPage('twin');
  };

  return (
    <div className={`min-h-screen flex ${isLightTheme ? 'light-theme' : ''} bg-transparent text-[var(--text-primary)] transition-colors duration-200`}>
      {/* Sidebar Navigation (7 Goal-Oriented Sections) */}
      <Sidebar
        currentPage={currentPage}
        onSelectPage={(p) => setCurrentPage(p)}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeAlertsCount={activeAlertsCount}
        onOpenOnboarding={() => setIsOnboardingOpen(true)}
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
          onOpenAlerts={() => setCurrentPage('alerts')}
          onOpenSearch={() => setIsSearchOpen(true)}
          onOpenAuth={() => setIsAuthOpen(true)}
          onOpenTour={() => setIsOnboardingOpen(true)}
          currentUser={currentUser}
        />

        {/* Page Container */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            <Suspense fallback={<FlowstatePageSkeleton />}>
              {currentPage === 'overview' && (
                <PageExecutiveOverview
                  onNavigateToDevice={handleNavigateToDevice}
                  onNavigateToTwin={handleNavigateToTwin}
                />
              )}
              {currentPage === 'fleet' && (
                <PageStorageFleet onNavigateToIntelligence={handleNavigateToDevice} />
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
              {currentPage === 'omega' && <PageOmegaControlRoom />}
              {currentPage === 'jurassic' && <PageJurassicLab />}
              {currentPage === 'phoenix' && <PagePhoenixOrchestrator />}
              {currentPage === 'atlas' && <PageAtlasRealityLab />}
              {currentPage === 'oracle' && <PageOracleIntelligence />}
              {currentPage === 'interventions' && (
                <PageInterventionStudio initialDeviceId={selectedDeviceId} />
              )}
              {currentPage === 'telemetry' && <PageTelemetryExplorer />}
              {currentPage === 'ml-lab' && <PageMLPredictionLab />}
              {currentPage === 'experiments' && <PageExperimentWorkbench />}
              {currentPage === 'reliability' && <PageModelReliability />}
              {currentPage === 'alerts' && <PageAlertsIncidents />}
              {currentPage === 'datasets' && <PageDatasetsQuality />}
              {currentPage === 'settings' && <PageSettingsAudit />}
            </Suspense>
          </div>
        </main>
      </div>

      {/* Quick Search Palette (Ctrl+K) */}
      <CommandPalette
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onNavigatePage={(p) => setCurrentPage(p)}
        onNavigateDevice={(id) => handleNavigateToDevice(id)}
      />

      {/* Identity & RBAC Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        currentUser={currentUser}
        onAuthSuccess={(username, role) => setCurrentUser({ username, role })}
      />

      {/* Interactive 6-Step Onboarding Modal */}
      <OnboardingModal
        isOpen={isOnboardingOpen}
        onClose={handleCloseOnboarding}
        currentMode={operatingMode}
        onSelectMode={handleModeChange}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <PresentationModeProvider>
      <AppContent />
    </PresentationModeProvider>
  );
};

export default App;
