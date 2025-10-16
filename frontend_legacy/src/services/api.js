import axios from 'axios';
import { API_BASE_URL } from '../../url';

// We'll need to get the mode dynamically in each function
// since we can't access React context directly in a service file
let getModeCallback = null;

// Function to set the mode getter callback
export const setModeGetter = (callback) => {
  getModeCallback = callback;
};

// Function to get current mode
const getCurrentMode = () => {
  if (getModeCallback) {
    return getModeCallback();
  }
  // Fallback to localStorage if callback not set
  const savedMode = localStorage.getItem('app_mode');
  return savedMode || 'Internal';
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const uploadFiles = async (files, threadId = null, threadName = null) => {
  try {
    const currentMode = getCurrentMode();
    console.log('Upload request:', { threadId, threadName, filesCount: files.length, mode: currentMode });
    
    const formData = new FormData();
    
    files.forEach((file) => {
      formData.append('files', file);
    });
    
    if (threadId) {
      formData.append('thread_id', threadId);
      console.log('Added thread_id to formData:', threadId);
    }
    if (threadName) {
      formData.append('thread_name', threadName);
      console.log('Added thread_name to formData:', threadName);
    }
    
    // Always append current mode
    formData.append('mode', currentMode);
    console.log('Added mode to formData:', currentMode);

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

export const sendQuery = async (threadId, question) => {
  try {
    const currentMode = getCurrentMode();
    console.log('Query request:', { threadId, question, mode: currentMode });
    
    const response = await api.post('/query/', {
      thread_id: threadId,
      question: question,
      mode: currentMode,
    });
    
    return response.data;
  } catch (error) {
    console.error('Query error:', error);
    throw error;
  }
};

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
    console.log(`Attempting to delete thread with ID: ${threadId}`);
    console.log(`Delete URL: /thread/${threadId}`);
    
    if (!threadId) {
      throw new Error('Thread ID is required for deletion');
    }
    
    const response = await api.delete(`/thread/${threadId}`);
    console.log('Delete thread successful response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Delete thread error:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      config: error.config
    });
    throw error;
  }
};

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

export const getMindMap = async (threadId, documentId, socketId = null) => {
  try {
    const currentMode = getCurrentMode();
    const payload = {
      thread_id: threadId,
      document_id: documentId,
      mode: currentMode
    };
    
    const headers = {
      'Content-Type': 'application/json'
    };
    
    if (socketId) {
      headers['x-socket-id'] = socketId;
    }
    
    console.log('MindMap request:', payload);
    const response = await api.post('/extra/mindmap', payload, { headers });
    
    return response.data;
  } catch (error) {
    if (error.response) {
      if (error.response.status === 422) {
        if (error.response.data?.detail) {
          console.error('Validation Details:', error.response.data.detail);
        }
      }
    } else {
      throw new Error('Error during request setup: ' + error.message);
    }
    
    throw error;
  }
};

export const getGlobalMindMap = async (threadId, socketId = null) => {
  try {
    const currentMode = getCurrentMode();
    const payload = {
      thread_id: threadId,
      document_id: 'global',
      mode: currentMode
    };
    
    const headers = {
      'Content-Type': 'application/json'
    };
    
    if (socketId) {
      headers['x-socket-id'] = socketId;
    }
    
    console.log('Global MindMap request:', payload);
    const response = await api.get(`/mindmap/${threadId}`, { headers });
    
    return response.data;
  } catch (error) {
    if (error.response) {
      if (error.response.status === 422) {
        if (error.response.data?.detail) {
          console.error('Validation Details:', error.response.data.detail);
        }
      }
    } else {
      throw new Error('Error during request setup: ' + error.message);
    }
    
    throw error;
  }
};

export const getWordCloud = async (threadId, documentIds, maxWords = 1000) => {
  try {
    const currentMode = getCurrentMode();
    const payload = {
      thread_id: threadId,
      document_ids: documentIds,
      max_words: maxWords,
      mode: currentMode
    };
    
    console.log('WordCloud request:', payload);
    const response = await api.post('/extra/wordcloud', payload, {
      responseType: 'blob',
      timeout: 30000
    });
    
    // Check if response is actually an image
    const contentType = response.headers['content-type'];
    if (!contentType || !contentType.startsWith('image/')) {
      try {
        const errorText = await response.data.text();
        throw new Error(errorText || 'Server returned non-image response');
      } catch (textError) {
        throw new Error('Server returned invalid response format');
      }
    }
    
    const imageUrl = URL.createObjectURL(response.data);
    
    return {
      status: true,
      imageUrl: imageUrl,
      blob: response.data
    };
  } catch (error) {
    if (error.response) {
      const contentType = error.response.headers['content-type'];
      
      if (contentType && contentType.includes('application/json')) {
        const errorMessage = error.response.data?.detail || error.response.data?.error || 'Unknown error from server';
        throw new Error(errorMessage);
      } else if (error.response.data instanceof Blob) {
        try {
          const errorText = await error.response.data.text();
          
          try {
            const errorData = JSON.parse(errorText);
            
            const errorMessage = errorData.error || errorData.detail || errorText;
            throw new Error(errorMessage);
          } catch (parseError) {
            throw new Error(errorText);
          }
        } catch (readError) {
          throw new Error('Failed to generate word cloud - unknown error');
        }
      } else {
        throw new Error(error.response.data?.error || error.response.data?.detail || 'Failed to generate word cloud');
      }
    } else if (error.request) {
      throw new Error('Network error - please check your connection');
    } else {
      throw new Error('Failed to generate word cloud: ' + error.message);
    }
  }
};

export default api;
