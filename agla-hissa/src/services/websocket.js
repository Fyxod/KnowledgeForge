import { io } from 'socket.io-client';
import { API_BASE_URL } from '../../url';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.userId = null;
  }

  /**
   * Initialize WebSocket connection
   * @param {string} userId - User ID for authentication
   * @param {string} token - JWT token for authentication
   */
  connect(userId, token = null) {
    try {
      this.userId = userId;
      
      // Use the same base URL as API
      const wsUrl = API_BASE_URL;
      
      this.socket = io(wsUrl, {
        auth: {
          token: token || localStorage.getItem('jwt'),
          userId: userId
        },
        transports: ['websocket', 'polling'],
        upgrade: true,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 20000,
      });

      this._setupEventHandlers();
      
      return this.socket;
    } catch (error) {
      console.error('Failed to initialize WebSocket connection:', error);
      return null;
    }
  }

  /**
   * Setup core WebSocket event handlers
   */
  _setupEventHandlers() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('🔌 WebSocket connected:', this.socket.id);
      this.isConnected = true;
      this.reconnectAttempts = 0;
      
      // Join user-specific room for personal updates
      if (this.userId) {
        this.socket.emit('join_user_room', { userId: this.userId });
        console.log('🔌 Joined user room for:', this.userId);
      }
    });

    this.socket.on('disconnect', (reason) => {
      console.log('🔌 WebSocket disconnected:', reason);
      this.isConnected = false;
      
      if (reason === 'io server disconnect') {
        // Server disconnected, need to reconnect manually
        setTimeout(() => this.reconnect(), 1000);
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('🔌 WebSocket connection error:', error.message);
      this.isConnected = false;
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('🔌 Max reconnection attempts reached');
      }
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('🔌 WebSocket reconnected after', attemptNumber, 'attempts');
      this.isConnected = true;
      this.reconnectAttempts = 0;
    });

    this.socket.on('reconnect_error', (error) => {
      console.error('🔌 WebSocket reconnection failed:', error.message);
    });

    // Handle authentication errors
    this.socket.on('auth_error', (data) => {
      console.error('🔌 WebSocket authentication failed:', data.message);
      this.disconnect();
    });
  }

  /**
   * Manually reconnect to WebSocket
   */
  reconnect() {
    if (this.socket && !this.isConnected) {
      console.log('🔌 Attempting manual reconnection...');
      this.socket.connect();
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.socket) {
      console.log('🔌 Disconnecting WebSocket...');
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
      this.listeners.clear();
      this.userId = null;
    }
  }

  /**
   * Subscribe to WebSocket events
   * @param {string} event - Event name
   * @param {Function} callback - Event callback
   */
  on(event, callback) {
    if (!this.socket) {
      console.warn('WebSocket not connected, cannot subscribe to:', event);
      return;
    }
    
    this.socket.on(event, callback);
    
    // Store callback for cleanup
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  /**
   * Unsubscribe from WebSocket events
   * @param {string} event - Event name
   * @param {Function} callback - Specific callback (optional)
   */
  off(event, callback = null) {
    if (!this.socket) return;

    if (callback) {
      this.socket.off(event, callback);
      
      // Remove from stored listeners
      const eventListeners = this.listeners.get(event);
      if (eventListeners) {
        const index = eventListeners.indexOf(callback);
        if (index > -1) {
          eventListeners.splice(index, 1);
        }
      }
    } else {
      this.socket.off(event);
      this.listeners.delete(event);
    }
  }

  /**
   * Emit event to server
   * @param {string} event - Event name
   * @param {Object} data - Event data
   */
  emit(event, data) {
    if (this.socket && this.isConnected) {
      this.socket.emit(event, data);
    } else {
      console.warn('WebSocket not connected, cannot emit:', event);
    }
  }

  /**
   * Get current socket ID
   * @returns {string|null} Socket ID
   */
  getSocketId() {
    return this.socket ? this.socket.id : null;
  }

  /**
   * Check if WebSocket is connected
   * @returns {boolean} Connection status
   */
  isSocketConnected() {
    return this.isConnected && this.socket && this.socket.connected;
  }

  /**
   * Subscribe to thread name updates
   * @param {string} threadId - Thread ID to monitor
   * @param {Function} callback - Callback for thread updates
   */
  subscribeToThreadUpdates(threadId, callback) {
    if (!this.userId || !threadId) {
      console.warn('Cannot subscribe to thread updates: missing userId or threadId');
      return;
    }

    const eventName = `${this.userId}/${threadId}/thread_update`;
    
    const wrappedCallback = (data) => {
      console.log('📝 Thread update received:', data);
      callback(data);
    };

    this.on(eventName, wrappedCallback);
    
    // Return unsubscribe function
    return () => {
      this.off(eventName, wrappedCallback);
    };
  }

  /**
   * Subscribe to all thread updates for current user
   * @param {Function} callback - Callback for any thread update
   */
  subscribeToAllThreadUpdates(callback) {
    if (!this.userId) {
      console.warn('Cannot subscribe to thread updates: missing userId');
      return;
    }

    // Listen for the global thread update event
    const wrappedCallback = (data) => {
      console.log('📝 Thread update received (all):', data);
      callback(data);
    };

    // Subscribe to the global thread update event
    this.on('thread_update_global', wrappedCallback);
    
    // Request to subscribe to all thread updates (join the user's thread updates room)
    this.emit('subscribe_all_thread_updates', { userId: this.userId });
    
    // Return unsubscribe function
    return () => {
      this.off('thread_update_global', wrappedCallback);
      this.emit('unsubscribe_all_thread_updates', { userId: this.userId });
    };
  }

  /**
   * Join a specific thread room for real-time updates
   * @param {string} threadId - Thread ID to join
   */
  joinThreadRoom(threadId) {
    if (!this.userId || !threadId) return;
    
    this.emit('join_thread_room', {
      userId: this.userId,
      threadId: threadId
    });
  }

  /**
   * Leave a specific thread room
   * @param {string} threadId - Thread ID to leave
   */
  leaveThreadRoom(threadId) {
    if (!this.userId || !threadId) return;
    
    this.emit('leave_thread_room', {
      userId: this.userId,
      threadId: threadId
    });
  }

  /**
   * Request immediate thread name update
   * @param {string} threadId - Thread ID
   * @param {string} newName - New thread name
   */
  updateThreadName(threadId, newName) {
    if (!this.userId || !threadId || !newName) return;
    
    this.emit('update_thread_name', {
      userId: this.userId,
      threadId: threadId,
      newName: newName
    });
  }
}

// Create singleton instance
const websocketService = new WebSocketService();

export default websocketService;
