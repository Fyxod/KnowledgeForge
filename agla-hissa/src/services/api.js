import axios from 'axios';

// const API_BASE_URL = 'http://127.0.0.1:8000';
const API_BASE_URL = 'https://api.dev-ansh.xyz';

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
    console.log('Upload request:', { threadId, threadName, filesCount: files.length });
    
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
    // Prepare the exact payload
    const payload = {
      thread_id: threadId,
      document_id: documentId
    };
    
    // Prepare headers with socket ID for progress updates
    const headers = {
      'Content-Type': 'application/json'
    };
    
    if (socketId) {
      headers['x-socket-id'] = socketId;
    }
    
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
      // Something else happened
      throw new Error('Error during request setup: ' + error.message);
    }
    
    throw error;
  }
};

export const getWordCloud = async (threadId, documentIds, maxWords = 1000) => {
  try {
    // Prepare the payload
    const payload = {
      thread_id: threadId,
      document_ids: documentIds,
      max_words: maxWords
    };
    
    const response = await api.post('/extra/wordcloud', payload, {
      responseType: 'blob', // Important: This tells axios to expect binary data
      timeout: 30000 // 30 second timeout
    });
    
    // Check if response is actually an image
    const contentType = response.headers['content-type'];
    if (!contentType || !contentType.startsWith('image/')) {
      // Try to read as text to see if it's an error message
      try {
        const errorText = await response.data.text();
        throw new Error(errorText || 'Server returned non-image response');
      } catch (textError) {
        throw new Error('Server returned invalid response format');
      }
    }
    
    // Convert blob to URL for display
    const imageUrl = URL.createObjectURL(response.data);
    
    return {
      status: true,
      imageUrl: imageUrl,
      blob: response.data
    };
  } catch (error) {
    if (error.response) {
      // Check if the error response is JSON (not a blob)
      const contentType = error.response.headers['content-type'];
      
      if (contentType && contentType.includes('application/json')) {
        // This is a JSON error response from FastAPI
        const errorMessage = error.response.data?.detail || error.response.data?.error || 'Unknown error from server';
        throw new Error(errorMessage);
      } else if (error.response.data instanceof Blob) {
        // This is a blob error response - try to read it
        try {
          const errorText = await error.response.data.text();
          
          // Try to parse as JSON for structured error
          try {
            const errorData = JSON.parse(errorText);
            
            // Throw the specific error message from the backend
            const errorMessage = errorData.error || errorData.detail || errorText;
            throw new Error(errorMessage);
          } catch (parseError) {
            // If not JSON, throw the raw text
            throw new Error(errorText);
          }
        } catch (readError) {
          throw new Error('Failed to generate word cloud - unknown error');
        }
      } else {
        // Handle other response types
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
