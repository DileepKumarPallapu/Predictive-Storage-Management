import React, { useState, useEffect } from 'react';
import { Sidebar, PageId } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { CommandPalette } from './components/CommandPalette';
import { AuthModal } from './components/AuthModal';
import { PageExecutiveOverview } from './pages/PageExecutiveOverview';
import { PageStorageFleet } from './pages/PageStorageFleet';
import { PageDeviceIntelligence } from './pages/PageDeviceIntelligence';
import { PageStorageDigitalTwin } from './pages/PageStorageDigitalTwin';
import { PageInterventionStudio } from './pages/PageInterventionStudio';
import { PageTelemetryExplorer } from './pages/PageTelemetryExplorer';
import { PageMLPredictionLab } from './pages/PageMLPredictionLab';
import { PageExperimentWorkbench } from './pages/PageExperimentWorkbench';
import { PageModelReliability } from './pages/PageModelReliability';
import { PageAlertsIncidents } from './pages/PageAlertsIncidents';
import { PageDatasetsQuality } from './pages/PageDatasetsQuality';
import { PageSettingsAudit } from './pages/PageSettingsAudit';
import { PageOmegaControlRoom } from './pages/PageOmegaControlRoom';
import { PageJurassicLab } from './pages/PageJurassicLab';
import { PagePhoenixOrchestrator } from './pages/PagePhoenixOrchestrator';
import { PageAtlasRealityLab } from './pages/PageAtlasRealityLab';
import { api } from './api/client';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [isLightTheme, setIsLightTheme] = useState<boolean>(false);
  const [operatingMode, setOperatingMode] = useState<string>('demo');
  const [activeAlertsCount, setActiveAlertsCount] = useState<number>(3);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('vol-nvme-tier1-db');
  
  // Modals state
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [isAuthOpen, setIsAuthOpen] = useState<boolean>(false);
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
      {/* Sidebar Navigation */}
      <Sidebar
        currentPage={currentPage}
        onSelectPage={(p) => setCurrentPage(p)}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeAlertsCount={activeAlertsCount}
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
          currentUser={currentUser}
        />

        {/* Page Container */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto space-y-6">
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
    </div>
  );
};

export default App;
