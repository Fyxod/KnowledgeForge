
import { useMode } from '../contexts/ModeContext';

/**
 * Mode Toggle Button Component
 * Displays a toggle switch to switch between internal and web-enhanced modes
 */
export default function ModeToggle() {
  const { currentMode, toggleMode, getCurrentModeConfig, isWebEnhanced } = useMode();
  const currentConfig = getCurrentModeConfig();

  return (
    <div className="flex items-center space-x-3">
      {/* Mode indicator */}
      <div className="hidden lg:flex items-center space-x-2">
        <span className="text-lg" role="img" aria-label={currentConfig.name}>
          {currentConfig.icon}
        </span>
        <div className="text-xs">
          <div className={`font-medium text-${currentConfig.color}-600`}>
            {currentConfig.name}
          </div>
          <div className="text-gray-500 text-[10px]">
            {currentConfig.description}
          </div>
        </div>
      </div>

      {/* Toggle switch */}
      <div className="relative">
        <button
          onClick={toggleMode}
          className={`
            relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            ${isWebEnhanced() 
              ? 'bg-green-600 hover:bg-green-700' 
              : 'bg-blue-600 hover:bg-blue-700'
            }
          `}
          role="switch"
          aria-checked={isWebEnhanced()}
          aria-label={`Switch to ${isWebEnhanced() ? 'Internal Knowledge' : 'Web Enhanced'} mode`}
          title={`Current: ${currentConfig.name}. Click to switch to ${isWebEnhanced() ? 'Internal Knowledge' : 'Web Enhanced'} mode`}
        >
          <span
            className={`
              inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200
              ${isWebEnhanced() ? 'translate-x-6' : 'translate-x-1'}
            `}
          >
            <span 
              className="absolute inset-0 flex items-center justify-center text-[8px]"
              role="img"
              aria-hidden="true"
            >
              {isWebEnhanced() ? '' : ''}
            </span>
          </span>
        </button>
      </div>

      {/* Mobile mode indicator */}
      <div className="lg:hidden">
        <span 
          className={`text-xs font-medium text-${currentConfig.color}-600`}
          title={currentConfig.description}
        >
          {currentConfig.icon} {currentConfig.name}
        </span>
      </div>
    </div>
  );
}
