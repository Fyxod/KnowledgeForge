/**
 * Singleton Socket.IO manager for the streaming chat feature.
 *
 * Provides:
 * - Auto-reconnection with exponential back-off
 * - JWT-authenticated connections
 * - Typed event helpers for the streaming query protocol
 */

import { io, Socket } from 'socket.io-client';
import { API_URL } from '../../config';
import { getAuthToken } from './api';

// ── Types ────────────────────────────────────────────────────────────

export interface StreamStartPayload {
  thread_id: string;
}

export interface StreamStatusPayload {
  status: string;
}

export interface StreamTokenPayload {
  token: string;
}

export interface StreamEndPayload {
  thread_id: string;
  answer: string;
  sources: {
    documents_used: Array<{
      title: string;
      document_id: string;
      page_no: number;
    }>;
    web_used: Array<{
      title: string;
      url: string;
      favicon: string | null;
    }>;
  };
  timing: {
    total_seconds: number;
  };
}

export interface StreamErrorPayload {
  error: string;
}

export interface QueryStreamPayload {
  thread_id: string;
  question: string;
  mode: 'Internal' | 'External';
  use_self_knowledge: boolean;
  token?: string;
}

// ── Callbacks ────────────────────────────────────────────────────────

export interface StreamCallbacks {
  onStart?: (data: StreamStartPayload) => void;
  onStatus?: (data: StreamStatusPayload) => void;
  onToken?: (data: StreamTokenPayload) => void;
  onEnd?: (data: StreamEndPayload) => void;
  onError?: (data: StreamErrorPayload) => void;
  onConnect?: () => void;
  onDisconnect?: (reason: string) => void;
}

// ── Socket manager ──────────────────────────────────────────────────

class SocketManager {
  private socket: Socket | null = null;
  private callbacks: StreamCallbacks = {};
  private _connected = false;

  /** Whether the socket is currently connected. */
  get connected(): boolean {
    return this._connected;
  }

  /**
   * Connect to the Socket.IO server (idempotent – reuses the existing
   * socket if already connected).
   */
  connect(): Socket {
    if (this.socket?.connected) {
      return this.socket;
    }

    const token = getAuthToken() ?? '';

    this.socket = io(API_URL, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 30000,
      timeout: 30000,
    });

    // ── Lifecycle ────────────────────────────────────────────────
    this.socket.on('connect', () => {
      console.log('[Socket] Connected:', this.socket?.id);
      this._connected = true;
      this.callbacks.onConnect?.();
    });

    this.socket.on('disconnect', (reason: string) => {
      console.log('[Socket] Disconnected:', reason);
      this._connected = false;
      this.callbacks.onDisconnect?.(reason);
    });

    this.socket.on('connect_error', (err: Error) => {
      console.error('[Socket] Connection error:', err.message);
      this._connected = false;
    });

    // ── Streaming events ────────────────────────────────────────
    this.socket.on('stream_start', (data: StreamStartPayload) => {
      this.callbacks.onStart?.(data);
    });

    this.socket.on('stream_status', (data: StreamStatusPayload) => {
      this.callbacks.onStatus?.(data);
    });

    this.socket.on('stream_token', (data: StreamTokenPayload) => {
      this.callbacks.onToken?.(data);
    });

    this.socket.on('stream_end', (data: StreamEndPayload) => {
      this.callbacks.onEnd?.(data);
    });

    this.socket.on('stream_error', (data: StreamErrorPayload) => {
      this.callbacks.onError?.(data);
    });

    // Session reset acknowledgement
    this.socket.on('session_reset_ok', (data: { thread_id: string; message: string }) => {
      console.log('[Socket] Session reset:', data.message);
    });

    this.socket.on('session_reset_error', (data: { error: string }) => {
      console.error('[Socket] Session reset error:', data.error);
    });

    return this.socket;
  }

  /** Register streaming event callbacks. */
  setCallbacks(cbs: StreamCallbacks): void {
    this.callbacks = { ...this.callbacks, ...cbs };
  }

  /** Remove all streaming callbacks. */
  clearCallbacks(): void {
    this.callbacks = {};
  }

  /** Send a streaming query to the server. */
  emitQuery(payload: QueryStreamPayload): void {
    if (!this.socket?.connected) {
      console.error('[Socket] Cannot emit – not connected');
      return;
    }
    // Attach token in payload as well for auth fallback
    const token = getAuthToken() ?? '';
    this.socket.emit('query_stream', { ...payload, token });
  }

  /** Tell the server to reset KV cache / history for a thread. */
  emitResetSession(threadId: string): void {
    if (!this.socket?.connected) {
      console.warn('[Socket] Cannot reset session – not connected');
      return;
    }
    this.socket.emit('reset_session', { thread_id: threadId });
  }

  /** Disconnect the socket. */
  disconnect(): void {
    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.disconnect();
      this.socket = null;
      this._connected = false;
    }
  }
}

/** Global singleton. */
export const socketManager = new SocketManager();
