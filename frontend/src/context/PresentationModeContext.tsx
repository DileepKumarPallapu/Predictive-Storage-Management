import React, { createContext, useContext, useState, useEffect } from 'react';

export type PresentationMode = 'guided' | 'expert';

interface PresentationModeContextType {
  mode: PresentationMode;
  setMode: (mode: PresentationMode) => void;
  toggleMode: () => void;
  isGuided: boolean;
  isExpert: boolean;
}

const PresentationModeContext = createContext<PresentationModeContextType>({
  mode: 'guided',
  setMode: () => {},
  toggleMode: () => {},
  isGuided: true,
  isExpert: false,
});

export const PresentationModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<PresentationMode>(() => {
    const saved = localStorage.getItem('aegisstor_presentation_mode');
    return (saved === 'expert' ? 'expert' : 'guided');
  });

  const setMode = (newMode: PresentationMode) => {
    setModeState(newMode);
    localStorage.setItem('aegisstor_presentation_mode', newMode);
  };

  const toggleMode = () => {
    setMode(mode === 'guided' ? 'expert' : 'guided');
  };

  return (
    <PresentationModeContext.Provider
      value={{
        mode,
        setMode,
        toggleMode,
        isGuided: mode === 'guided',
        isExpert: mode === 'expert',
      }}
    >
      {children}
    </PresentationModeContext.Provider>
  );
};

export const usePresentationMode = () => useContext(PresentationModeContext);
