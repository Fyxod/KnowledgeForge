import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import websocketService from '../services/websocket';

const WebSocketContext = createContext();

/**
 * Hook to use WebSocket context
 * @returns {Object} WebSocket context value
 */
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    // Return default values instead of throwing error to prevent app crash
    console.warn('useWebSocket called outside of WebSocketProvider, returning defaults');
    return {
      isConnected: false,
      subscribeToAllThreadUpdates: () => () => {},
      joinThreadRoom: () => {},
      leaveThreadRoom: () => {},
      connectionStatus: 'disconnected',
      socketId: null,
      threadUpdates: {}
    };
  }
  return context;
};

/**
 * WebSocket Provider Component
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 * @param {string} props.userId - Current user ID
 * @param {boolean} props.enabled - Whether WebSocket should be enabled
 */
export const WebSocketProvider = ({ children, userId, enabled = true }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [socketId, setSocketId] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [threadUpdates, setThreadUpdates] = useState({});

  // Initialize WebSocket connection
  useEffect(() => {
    if (!enabled || !userId) {
      if (websocketService.isSocketConnected()) {
        websocketService.disconnect();
        setIsConnected(false);
        setSocketId(null);
        setConnectionStatus('disconnected');
      }
      return;
    }

    const token = localStorage.getItem('jwt');
    if (!token) {
      console.warn('No JWT token found, skipping WebSocket connection');
      return;
    }

    console.log('🔌 Initializing WebSocket connection for user:', userId);
    setConnectionStatus('connecting');

    // Connect to WebSocket
    websocketService.connect(userId, token);

    // Listen for connection status changes
    const handleConnect = () => {
      setIsConnected(true);
      setSocketId(websocketService.getSocketId());
      setConnectionStatus('connected');
      console.log('🔌 WebSocket connected successfully');
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      setSocketId(null);
      setConnectionStatus('disconnected');
      console.log('🔌 WebSocket disconnected');
    };

    const handleConnectError = () => {
      setConnectionStatus('error');
      console.log('🔌 WebSocket connection error');
    };

    const handleReconnect = () => {
      setConnectionStatus('reconnected');
      console.log('🔌 WebSocket reconnected');
    };

    // Setup event listeners
    websocketService.on('connect', handleConnect);
    websocketService.on('disconnect', handleDisconnect);
    websocketService.on('connect_error', handleConnectError);
    websocketService.on('reconnect', handleReconnect);

    // Cleanup on unmount or userId change
    return () => {
      console.log('🔌 Cleaning up WebSocket connection');
      websocketService.off('connect', handleConnect);
      websocketService.off('disconnect', handleDisconnect);
      websocketService.off('connect_error', handleConnectError);
      websocketService.off('reconnect', handleReconnect);
      
      if (websocketService.isSocketConnected()) {
        websocketService.disconnect();
      }
    };
  }, [userId, enabled]);

  /**
   * Subscribe to thread updates with automatic cleanup
   * @param {string} threadId - Thread ID to monitor
   * @param {Function} callback - Callback for updates
   * @returns {Function} Cleanup function
   */
  const subscribeToThreadUpdates = useCallback((threadId, callback) => {
    if (!isConnected || !threadId) {
      console.warn('Cannot subscribe to thread updates: not connected or missing threadId');
      return () => {};
    }

    return websocketService.subscribeToThreadUpdates(threadId, callback);
  }, [isConnected]);

  /**
   * Subscribe to all thread updates for current user
   * @param {Function} callback - Callback for any thread update
   * @returns {Function} Cleanup function
   */
  const subscribeToAllThreadUpdates = useCallback((callback) => {
    if (!isConnected) {
      console.warn('Cannot subscribe to all thread updates: not connected');
      return () => {};
    }

    return websocketService.subscribeToAllThreadUpdates(callback);
  }, [isConnected]);

  /**
   * Join a thread room for real-time updates
   * @param {string} threadId - Thread ID to join
   */
  const joinThreadRoom = useCallback((threadId) => {
    if (!isConnected || !threadId) return;
    websocketService.joinThreadRoom(threadId);
  }, [isConnected]);

  /**
   * Leave a thread room
   * @param {string} threadId - Thread ID to leave
   */
  const leaveThreadRoom = useCallback((threadId) => {
    if (!isConnected || !threadId) return;
    websocketService.leaveThreadRoom(threadId);
  }, [isConnected]);

  /**
   * Update thread name via WebSocket
   * @param {string} threadId - Thread ID
   * @param {string} newName - New thread name
   */
  const updateThreadName = useCallback((threadId, newName) => {
    if (!isConnected || !threadId || !newName) return;
    websocketService.updateThreadName(threadId, newName);
  }, [isConnected]);

  /**
   * Get socket ID
   * @returns {string|null} Current socket ID
   */
  const getSocketId = useCallback(() => {
    return websocketService.getSocketId();
  }, []);

  /**
   * Emit custom event
   * @param {string} event - Event name
   * @param {Object} data - Event data
   */
  const emit = useCallback((event, data) => {
    if (!isConnected) {
      console.warn('Cannot emit event: WebSocket not connected');
      return;
    }
    websocketService.emit(event, data);
  }, [isConnected]);

  /**
   * Subscribe to custom event
   * @param {string} event - Event name
   * @param {Function} callback - Event callback
   */
  const on = useCallback((event, callback) => {
    websocketService.on(event, callback);
  }, []);

  /**
   * Unsubscribe from custom event
   * @param {string} event - Event name
   * @param {Function} callback - Event callback (optional)
   */
  const off = useCallback((event, callback) => {
    websocketService.off(event, callback);
  }, []);

  // Context value
  const value = {
    // Connection state
    isConnected,
    socketId,
    connectionStatus,
    userId,
    
    // Thread-specific methods
    subscribeToThreadUpdates,
    subscribeToAllThreadUpdates,
    joinThreadRoom,
    leaveThreadRoom,
    updateThreadName,
    
    // General WebSocket methods
    getSocketId,
    emit,
    on,
    off,
    
    // Direct access to service (use with caution)
    websocketService,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export default WebSocketContext;
