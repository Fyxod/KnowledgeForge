# API Integration Documentation

This document provides detailed information about the frontend's integration with the backend API.

## API Configuration

### Base Configuration
```javascript
const API_BASE_URL = 'http://127.0.0.1:8000';
```

### Authentication
All authenticated requests include JWT tokens in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## API Endpoints

### Authentication Endpoints

#### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "name": "string",
  "email": "string", 
  "password": "string"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "token": "jwt_token_string",
  "user": {
    "id": "user_id",
    "name": "string",
    "email": "string"
  }
}
```

**Frontend Implementation:**
```javascript
const registerUser = async (name, email, password) => {
  const response = await api.post('/auth/register', { name, email, password });
  return response.data;
};
```

#### POST /auth/login
Authenticate existing user.

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "token": "jwt_token_string",
  "user": {
    "id": "user_id",
    "name": "string",
    "email": "string"
  }
}
```

**Frontend Implementation:**
```javascript
const loginUser = async (email, password) => {
  const response = await api.post('/auth/login', { email, password });
  return response.data;
};
```

### User Endpoints

#### GET /user/me
Get current user information (requires authentication).

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response (Success):**
```json
{
  "id": "user_id",
  "name": "string",
  "email": "string",
  "created_at": "timestamp"
}
```

**Frontend Implementation:**
```javascript
const getCurrentUser = async () => {
  const response = await api.get('/user/me');
  return response.data;
};
```

#### GET /threads
Get user's chat threads (requires authentication).

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response (Success):**
```json
[
  {
    "id": "thread_id",
    "user_id": "user_id",
    "messages": [...],
    "documents": [...],
    "created_at": "timestamp",
    "updated_at": "timestamp"
  }
]
```

**Frontend Implementation:**
```javascript
const getThreads = async () => {
  const response = await api.get('/threads');
  return response.data;
};
```

### File Upload Endpoints

#### POST /upload
Upload files and create a new thread (requires authentication).

**Request:**
- Content-Type: multipart/form-data
- Body: FormData with files

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data
```

**Response (Success):**
```json
{
  "thread_id": "string",
  "files": [
    {
      "filename": "string",
      "size": number,
      "type": "string"
    }
  ],
  "message": "Upload successful"
}
```

**Frontend Implementation:**
```javascript
const uploadFiles = async (files) => {
  const formData = new FormData();
  Array.from(files).forEach(file => {
    formData.append('files', file);
  });
  
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};
```

### Chat Endpoints

#### POST /query
Send a message to AI (requires authentication).

**Request Body:**
```json
{
  "query": "string",
  "thread_id": "string" // optional for new threads
}
```

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response (Success):**
```json
{
  "response": "string",
  "thread_id": "string",
  "message_id": "string"
}
```

**Frontend Implementation:**
```javascript
const sendMessage = async (query, threadId = null) => {
  const payload = { query };
  if (threadId) payload.thread_id = threadId;
  
  const response = await api.post('/query', payload);
  return response.data;
};
```

## Frontend API Service Structure

### Service File Organization
```
src/services/
└── api.js          # Main API service module
```

### Key Functions

#### Authentication Functions
- `registerUser(name, email, password)` - User registration
- `loginUser(email, password)` - User login
- `getCurrentUser()` - Get current user info

#### Thread Management Functions
- `getThreads()` - Fetch user's threads
- `createEmptyThread()` - Create new empty thread

#### File Operations
- `uploadFiles(files)` - Upload files and create thread

#### Chat Functions
- `sendMessage(query, threadId)` - Send message to AI

### Error Handling

#### Network Errors
```javascript
// Handled automatically by axios interceptors
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('jwt');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

#### Frontend Error Handling Pattern
```javascript
try {
  const result = await apiFunction();
  // Handle success
} catch (error) {
  if (error.response?.data?.message) {
    // Show backend error message
    setError(error.response.data.message);
  } else {
    // Show generic error
    setError('An unexpected error occurred');
  }
}
```

## Response Data Formats

### Thread Object Structure
```javascript
{
  id: "string",
  user_id: "string", 
  messages: [
    {
      id: "string",
      content: "string",
      role: "user" | "assistant",
      timestamp: "ISO_string"
    }
  ],
  documents: [
    {
      filename: "string",
      size: number,
      type: "string",
      upload_date: "ISO_string"
    }
  ],
  created_at: "ISO_string",
  updated_at: "ISO_string"
}
```

### Message Object Structure
```javascript
{
  id: "string",
  thread_id: "string",
  content: "string", 
  role: "user" | "assistant",
  timestamp: "ISO_string",
  metadata: {} // optional additional data
}
```

### User Object Structure
```javascript
{
  id: "string",
  name: "string",
  email: "string",
  created_at: "ISO_string",
  last_login: "ISO_string"
}
```

## Frontend State Management

### Authentication State
```javascript
// Stored in App.jsx
const [isAuthenticated, setIsAuthenticated] = useState(false);
const [userData, setUserData] = useState(null);

// localStorage keys
'jwt' - JWT token string
'userData' - JSON stringified user object
```

### Thread State
```javascript
// Stored in ChatPage.jsx
const [threads, setThreads] = useState([]);
const [selectedThread, setSelectedThread] = useState(null);
const [messages, setMessages] = useState([]);
```

## API Integration Patterns

### Protected Route Pattern
```javascript
// Check authentication before API calls
useEffect(() => {
  const token = localStorage.getItem('jwt');
  if (!token) {
    navigate('/login');
    return;
  }
  fetchUserData();
}, []);
```

### Optimistic Updates
```javascript
// Add message immediately, then send to server
const handleSend = async (message) => {
  // Optimistic update
  setMessages(prev => [...prev, {
    content: message,
    role: 'user',
    timestamp: new Date().toISOString()
  }]);
  
  try {
    const response = await sendMessage(message, threadId);
    // Update with server response
    setMessages(prev => [...prev, {
      content: response.response,
      role: 'assistant', 
      timestamp: new Date().toISOString()
    }]);
  } catch (error) {
    // Handle error - possibly remove optimistic update
  }
};
```

### File Upload with Progress
```javascript
const handleFileUpload = async (files) => {
  setIsUploading(true);
  try {
    const response = await uploadFiles(files);
    // Handle success
    await refreshThreads();
  } catch (error) {
    // Handle error
  } finally {
    setIsUploading(false);
  }
};
```

## Testing API Integration

### Local Development
1. Start backend server: `uvicorn app.main:app --reload --port 8000`
2. Start frontend: `npm run dev`
3. Test all endpoints through UI

### API Testing Tools
- Browser Network tab for request/response inspection
- Postman for direct API testing
- Frontend console logs for debugging

### Common Issues and Solutions

#### CORS Issues
```javascript
// Backend should include CORS middleware
// Frontend should use correct origin in requests
```

#### Token Expiration
```javascript
// Check for 401 responses and handle token refresh
// Implement automatic logout on expired tokens
```

#### File Upload Timeouts
```javascript
// Increase timeout for large files
// Implement upload progress indicators
// Handle upload interruptions gracefully
```

---

This documentation should be updated as the API evolves and new endpoints are added.
