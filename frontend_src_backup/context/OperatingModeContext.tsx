import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';

export type OperatingMode = 'demo' | 'replay' | 'live';

export interface LiveDiagnostics {
  native_host_active?: boolean;
  prometheus_operational?: boolean;
  prometheus_message?: string;
  remedy?: string;
}

interface OperatingModeContextType {
  operatingMode: OperatingMode;
  setOperatingMode: (mode: OperatingMode) => Promise<void>;
  provenanceLabel: string;
  isDemo: boolean;
  isReplay: boolean;
  isLive: boolean;
  liveDiagnostics: LiveDiagnostics | null;
  refreshKey: number;
  triggerRefresh: () => void;
}

const OperatingModeContext = createContext<OperatingModeContextType>({
  operatingMode: 'demo',
  setOperatingMode: async () => {},
  provenanceLabel: 'SYNTHETIC DEMO DATA',
  isDemo: true,
  isReplay: false,
  isLive: false,
  liveDiagnostics: null,
  refreshKey: 0,
  triggerRefresh: () => {},
});

export const OperatingModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [operatingMode, setModeState] = useState<OperatingMode>(() => {
    const saved = localStorage.getItem('aegisstor_operating_mode');
    if (saved === 'replay' || saved === 'live' || saved === 'demo') {
      return saved as OperatingMode;
    }
    return 'demo';
  });

  const [liveDiagnostics, setLiveDiagnostics] = useState<LiveDiagnostics | null>(null);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  // Sync with backend on startup
  useEffect(() => {
    const initMode = async () => {
      try {
        const saved = localStorage.getItem('aegisstor_operating_mode') as OperatingMode | null;
        if (saved && (saved === 'demo' || saved === 'replay' || saved === 'live')) {
          const res = await api.setOperatingMode(saved);
          if (res.diagnostics) setLiveDiagnostics(res.diagnostics);
        } else {
          const health = await api.getHealth();
          if (health.mode === 'demo' || health.mode === 'replay' || health.mode === 'live') {
            setModeState(health.mode as OperatingMode);
            localStorage.setItem('aegisstor_operating_mode', health.mode);
          }
        }
      } catch (e) {
        console.warn('Backend sync for operating mode completed with fallback:', e);
      }
    };
    initMode();
  }, []);

  const setOperatingMode = async (newMode: OperatingMode) => {
    setModeState(newMode);
    localStorage.setItem('aegisstor_operating_mode', newMode);
    try {
      const res = await api.setOperatingMode(newMode);
      if (res.diagnostics) {
        setLiveDiagnostics(res.diagnostics);
      } else {
        setLiveDiagnostics(null);
      }
    } catch (e) {
      console.error('Failed to notify backend of mode change:', e);
    } finally {
      // Trigger refresh across all active listeners
      setRefreshKey((prev) => prev + 1);
    }
  };

  const triggerRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const getProvenanceLabel = (mode: OperatingMode): string => {
    switch (mode) {
      case 'live':
        return 'LIVE PASSIVE HOST';
      case 'replay':
        return 'CHRONOLOGICAL REPLAY TRACE';
      case 'demo':
      default:
        return 'SYNTHETIC DEMO DATA';
    }
  };

  return (
    <OperatingModeContext.Provider
      value={{
        operatingMode,
        setOperatingMode,
        provenanceLabel: getProvenanceLabel(operatingMode),
        isDemo: operatingMode === 'demo',
        isReplay: operatingMode === 'replay',
        isLive: operatingMode === 'live',
        liveDiagnostics,
        refreshKey,
        triggerRefresh,
      }}
    >
      {children}
    </OperatingModeContext.Provider>
  );
};

export const useOperatingMode = () => useContext(OperatingModeContext);
