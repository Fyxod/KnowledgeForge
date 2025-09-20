import React, { createContext, useContext, useState, useEffect } from 'react';

const ModeContext = createContext();

/**
 * Application modes (matching backend constants)
 */
export const APP_MODES = {
  INTERNAL: 'Internal',
  WEB_ENHANCED: 'External'
};

/**
 * Mode display names and descriptions
 */
export const MODE_CONFIG = {
  [APP_MODES.INTERNAL]: {
    name: 'Internal Knowledge',
    description: 'Uses only uploaded documents',
    icon: '',
    color: 'blue'
  },
  [APP_MODES.WEB_ENHANCED]: {
    name: 'Web Enhanced',
    description: 'Uses documents + web search',
    icon: '',
    color: 'green'
  }
};

/**
 * Hook to use Mode context
 * @returns {Object} Mode context value
 */
export const useMode = () => {
  const context = useContext(ModeContext);
  if (!context) {
    throw new Error('useMode must be used within a ModeProvider');
  }
  return context;
};

/**
 * Mode Provider Component
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 */
export const ModeProvider = ({ children }) => {
  const [currentMode, setCurrentMode] = useState(() => {
    // Load saved mode from localStorage or default to internal
    const savedMode = localStorage.getItem('app_mode');
    return savedMode && Object.values(APP_MODES).includes(savedMode) 
      ? savedMode 
      : APP_MODES.INTERNAL;
  });

  // Save mode to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('app_mode', currentMode);
  }, [currentMode]);

  /**
   * Toggle between internal and web-enhanced modes
   */
  const toggleMode = () => {
    setCurrentMode(prevMode => 
      prevMode === APP_MODES.INTERNAL 
        ? APP_MODES.WEB_ENHANCED 
        : APP_MODES.INTERNAL
    );
  };

  /**
   * Set specific mode
   * @param {string} mode - Mode to set
   */
  const setMode = (mode) => {
    if (Object.values(APP_MODES).includes(mode)) {
      setCurrentMode(mode);
    } else {
      console.warn(`Invalid mode: ${mode}. Valid modes are:`, Object.values(APP_MODES));
    }
  };

  /**
   * Get current mode configuration
   * @returns {Object} Current mode config
   */
  const getCurrentModeConfig = () => {
    return MODE_CONFIG[currentMode];
  };

  /**
   * Check if current mode is web-enhanced
   * @returns {boolean} True if web-enhanced mode is active
   */
  const isWebEnhanced = () => {
    return currentMode === APP_MODES.WEB_ENHANCED;
  };

  /**
   * Check if current mode is internal only
   * @returns {boolean} True if internal mode is active
   */
  const isInternal = () => {
    return currentMode === APP_MODES.INTERNAL;
  };

  const contextValue = {
    currentMode,
    setMode,
    toggleMode,
    getCurrentModeConfig,
    isWebEnhanced,
    isInternal,
    modes: APP_MODES,
    modeConfig: MODE_CONFIG
  };

  return (
    <ModeContext.Provider value={contextValue}>
      {children}
    </ModeContext.Provider>
  );
};

export default ModeContext;
