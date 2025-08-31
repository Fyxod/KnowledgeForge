import { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import { API_BASE_URL } from '../../url';

/**
 * Simple WebSocket hook for thread name updates with comprehensive debugging
 * @param {string} userId - User ID for WebSocket connection
 * @param {boolean} enabled - Whether WebSocket should be enabled
 * @returns {Object} - WebSocket connection state and methods
 */
const useWebSocket = (userId, enabled = true) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const socketRef = useRef(null);

  useEffect(() => {
    // Don't connect if disabled or no userId
    if (!enabled || !userId) {
      console.log('[WebSocket] 🔌 Connection disabled or no userId:', { enabled, userId });
      return;
    }

    const token = localStorage.getItem('jwt');
    if (!token) {
      console.warn('[WebSocket]  No JWT token found, skipping connection');
      return;
    }

    try {
      console.log('[WebSocket]  Connecting for user:', userId);
      setConnectionStatus('connecting');

      // Create socket connection
      socketRef.current = io(API_BASE_URL, {
        auth: {
          token: token,
          userId: userId
        },
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 10000,
      });

      // Connection event handlers
      socketRef.current.on('connect', () => {
        console.log('[WebSocket]  Connected successfully');
        console.log('[WebSocket]  Socket ID:', socketRef.current.id);
        console.log('[WebSocket]  Auth info:', { userId, token: token ? 'present' : 'missing' });
        setIsConnected(true);
        setConnectionStatus('connected');
      });

      socketRef.current.on('disconnect', (reason) => {
        console.log('[WebSocket] ❌ Disconnected:', reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
      });

      socketRef.current.on('connect_error', (error) => {
        console.error('[WebSocket]  Connection error:', error);
        setConnectionStatus('error');
      });

      // Add comprehensive event listener to see ALL events
      socketRef.current.onAny((eventName, ...args) => {
        console.log(`[WebSocket]  Event received: ${eventName}`, args);
        
        // Check if this is a thread update event
        const threadUpdatePattern = new RegExp(`^${userId}/.+/thread_update$`);
        if (threadUpdatePattern.test(eventName)) {
          console.log('[WebSocket] 🧵 This is a thread update event!');
        }
      });

    } catch (error) {
      console.error('[WebSocket]  Connection setup failed:', error);
      setConnectionStatus('error');
    }

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        console.log('[WebSocket]  Cleaning up connection');
        socketRef.current.disconnect();
        socketRef.current = null;
        setIsConnected(false);
        setConnectionStatus('disconnected');
      }
    };
  }, [userId, enabled]);

  /**
   * Subscribe to all thread name updates for the user
   * @param {Function} callback - Callback function to handle updates
   * @returns {Function} - Unsubscribe function
   */
  const subscribeToThreadUpdates = (callback) => {
    if (!socketRef.current || !isConnected) {
      console.warn('[WebSocket]  Cannot subscribe: not connected');
      console.warn('[WebSocket] Socket exists:', !!socketRef.current);
      console.warn('[WebSocket] Is connected:', isConnected);
      return () => {};
    }

    console.log('[WebSocket]  Setting up thread update subscription for user:', userId);

    // Create a pattern to match thread update events
    const eventPattern = new RegExp(`^${userId}/.+/thread_update$`);
    console.log('[WebSocket] 🔍 Looking for events matching pattern:', eventPattern.toString());

    // Listen to all thread update events for this user
    const handleThreadUpdate = (data) => {
      console.log('[WebSocket] Processing thread update event:', data);
      callback(data);
    };

    // Store original onAny handler count for debugging
    const listenersCount = socketRef.current.listenerCount ? socketRef.current.listenerCount() : 'unknown';
    console.log('[WebSocket]Current listener count:', listenersCount);

    // Register a global listener for all events and filter for thread updates
    const eventHandler = (eventName, data) => {
      console.log('[WebSocket] Checking event:', eventName, 'against pattern:', eventPattern.toString());
      
      if (eventPattern.test(eventName)) {
        console.log('[WebSocket]  Pattern match! Processing thread update');
        
        // Extract threadId from event name: "userId/threadId/thread_update"
        const parts = eventName.split('/');
        const threadId = parts[1];
        
        console.log('[WebSocket] 🆔 Extracted threadId:', threadId);
        console.log('[WebSocket] 📦 Event data:', data);
        
        handleThreadUpdate({
          ...data,
          threadId: threadId // Ensure threadId is available
        });
      } else {
        console.log('[WebSocket]  No pattern match for event:', eventName);
      }
    };

    // Add the event handler
    socketRef.current.onAny(eventHandler);
    console.log('[WebSocket]  Event handler attached');

    // Return unsubscribe function
    return () => {
      if (socketRef.current) {
        console.log('[WebSocket]  Unsubscribing from thread updates');
        socketRef.current.offAny(eventHandler);
      }
    };
  };

  /**
   * Subscribe to mind map creation updates for a specific thread
   * @param {string} threadId - Thread ID to subscribe to
   * @param {Function} callback - Callback function to handle updates
   * @returns {Function} - Unsubscribe function
   */
  const subscribeToMindMapUpdates = (threadId, callback) => {
    if (!socketRef.current || !isConnected || !threadId) {
      console.warn('[WebSocket] ⚠️ Cannot subscribe to mind maps: not connected or missing threadId');
      console.warn('[WebSocket] Socket exists:', !!socketRef.current);
      console.warn('[WebSocket] Is connected:', isConnected);
      console.warn('[WebSocket] ThreadId:', threadId);
      return () => {};
    }

    console.log('[WebSocket] 🗺️ Setting up mind map update subscription for thread:', threadId);

    // Create a pattern to match mind map update events for this thread
    const eventPattern = new RegExp(`^${userId}/${threadId}/mind_map$`);
    console.log('[WebSocket] 🔍 Looking for mind map events matching pattern:', eventPattern.toString());

    // Handle mind map updates
    const handleMindMapUpdate = (data) => {
      console.log('[WebSocket] 🗺️ Received mind map update event:', data);
      callback(data);
    };

    // Register event handler
    const eventHandler = (eventName, data) => {
      console.log('[WebSocket] 🔍 Checking event for mind map:', eventName);
      
      if (eventPattern.test(eventName)) {
        console.log('[WebSocket] ✅ Mind map event pattern match!');
        handleMindMapUpdate({
          ...data,
          threadId: threadId
        });
      }
    };

    // Add the event handler
    socketRef.current.onAny(eventHandler);
    console.log('[WebSocket] 🎧 Mind map event handler attached');

    // Return unsubscribe function
    return () => {
      if (socketRef.current) {
        console.log('[WebSocket] 🔇 Unsubscribing from mind map updates');
        socketRef.current.offAny(eventHandler);
      }
    };
  };

  return {
    isConnected,
    connectionStatus,
    subscribeToThreadUpdates,
    subscribeToMindMapUpdates
  };
};

export { useWebSocket };
