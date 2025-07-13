/**
 * API Service Module
 * 
 * Provides centralized HTTP client configuration and API functions
 * for communicating with the backend server. Handles authentication,
 * request/response interceptors, and provides typed API methods.
 * 
 * Features:
 * - Automatic JWT token attachment to authenticated requests
 * - Centralized error handling
 * - Consistent API endpoint management
 * - Support for both JSON and FormData requests
 */

import axios from 'axios';

// Backend server configuration
const API_BASE_URL = 'http://127.0.0.1:8000'; // Match your backend URL

// Create axios instance with default configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor to add JWT token to authenticated requests
 * Automatically attaches Bearer token from localStorage if available
 */
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// File upload service
export const uploadFiles = async (files, threadId = null, threadName = null) => {
  try {
    console.log('Upload request:', { threadId, threadName, filesCount: files.length });
    
    const formData = new FormData();
    
    // Add files to form data
    files.forEach((file) => {
      formData.append('files', file);
    });
    
    // Add thread info if provided
    if (threadId) {
      formData.append('thread_id', threadId);
      console.log('Added thread_id to formData:', threadId);
    }
    if (threadName) {
      formData.append('thread_name', threadName);
      console.log('Added thread_name to formData:', threadName);
    }

    const response = await api.post('/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
};

// Query service
export const sendQuery = async (threadId, question) => {
  try {
    const response = await api.post('/query/', {
      thread_id: threadId,
      question: question,
    });
    
    return response.data;
  } catch (error) {
    console.error('Query error:', error);
    throw error;
  }
};

// Thread management services
export const createThread = async (threadName = 'New Thread') => {
  try {
    const response = await api.post('/thread/', {
      thread_name: threadName,
    });
    
    return response.data;
  } catch (error) {
    console.error('Create thread error:', error);
    throw error;
  }
};

export const getThreads = async () => {
  try {
    const response = await api.get('/thread/');
    return response.data;
  } catch (error) {
    console.error('Get threads error:', error);
    throw error;
  }
};

export const deleteThread = async (threadId) => {
  try {
    const response = await api.delete(`/thread/${threadId}`);
    return response.data;
  } catch (error) {
    console.error('Delete thread error:', error);
    throw error;
  }
};

// Update thread name
export const updateThreadName = async (threadId, threadName) => {
  try {
    const response = await api.put(`/thread/${threadId}`, {
      thread_name: threadName,
    });
    
    return response.data;
  } catch (error) {
    console.error('Update thread name error:', error);
    throw error;
  }
};

// User services
export const login = async (credentials) => {
  try {
    const response = await api.post('/user/login', credentials);
    return response.data;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

export const signup = async (userData) => {
  try {
    const response = await api.post('/user/', userData);
    return response.data;
  } catch (error) {
    console.error('Signup error:', error);
    throw error;
  }
};

export const getUser = async (userId) => {
  try {
    const response = await api.get(`/user/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Get user error:', error);
    throw error;
  }
};

// Create an empty thread for chat
export const createEmptyThread = async (threadName = 'New Chat') => {
  try {
    const response = await api.post('/thread/', {
      thread_name: threadName,
    });
    
    return response.data;
  } catch (error) {
    console.error('Create thread error:', error);
    throw error;
  }
};

export default api;
