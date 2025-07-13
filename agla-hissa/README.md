# Multi-Modal Enterprise Knowledge Synthesis Platform - Frontend

A modern, professional React-based frontend for an enterprise LLM chat platform that enables users to interact with AI, upload documents, and manage conversation threads.

## Features

### 🔐 Authentication
- User registration and login
- JWT-based authentication
- Secure session management
- Automatic token refresh

### 💬 Chat Interface
- Real-time messaging with AI
- Thread-based conversation management
- Professional rectangular message bubbles
- Typing indicators for better UX
- Message copying functionality

### 📁 Document Management
- Drag-and-drop file upload
- Multiple file format support
- Document-based chat threads
- File upload progress indicators
- Document preview in chat

### 🧭 Navigation & Organization
- Sidebar with thread management
- "New Chat" button for quick thread creation
- Thread history with file/document indicators
- Top navigation bar with user info
- Clean, business-appropriate UI design

## Getting Started

### Prerequisites
- Node.js (v14 or higher)
- npm or yarn
- Backend server running on `http://localhost:8000`

### Installation

1. Navigate to the frontend directory:
```bash
cd agla-hissa
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173` (or next available port).

### Building for Production

```bash
npm run build
```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ChatInput.jsx   # Message input with file upload
│   ├── ChatWindow.jsx  # Main chat display area
│   ├── MessageBubble.jsx # Individual message component
│   ├── NavBar.jsx      # Top navigation bar
│   └── Sidebar.jsx     # Thread management sidebar
├── routes/             # Page components
│   ├── chatPage.jsx    # Main chat interface
│   ├── Login.jsx       # User login page
│   └── signUp.jsx      # User registration page
├── services/           # API integration
│   └── api.js          # Backend API functions
├── App.jsx             # Main application component
└── main.jsx           # Application entry point
```

## Key Components

### App.jsx
- Main application wrapper
- Authentication state management
- Route protection
- User data management

### ChatPage.jsx
- Primary chat interface
- Thread creation and management
- File upload handling
- Loading states

### Sidebar.jsx
- Thread navigation
- "New Chat" functionality
- File/document indicators
- Professional icons (no emojis)

### ChatWindow.jsx
- Message display
- Welcome screen
- Document preview
- Professional UI design

### ChatInput.jsx
- Message composition
- File upload (drag-and-drop + click)
- Send functionality
- Upload progress indication

### MessageBubble.jsx
- Individual message display
- Professional rectangular design
- Copy message functionality
- User/AI avatar indicators

## API Integration

The frontend communicates with the backend through these main endpoints:

- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `GET /user/me` - Get current user info
- `POST /upload` - File upload and thread creation
- `POST /query` - Send messages to AI
- `GET /threads` - Get user's chat threads

All authenticated requests include JWT tokens in the `Authorization` header as `Bearer <token>`.

## Design Principles

### Professional UI
- No emojis in the interface
- Rectangular message bubbles (no speech tails)
- SVG icons for all interface elements
- Clean, business-appropriate color scheme
- Consistent spacing and typography

### User Experience
- Loading indicators for all async operations
- Error handling with user-friendly messages
- Responsive design for different screen sizes
- Intuitive navigation and controls

### Code Quality
- Modular component structure
- Consistent naming conventions
- Proper error boundaries
- Clean separation of concerns

## Environment Configuration

The application uses these default configurations:

- Backend API: `http://localhost:8000`
- Frontend dev server: `http://localhost:5173`

To modify the backend URL, update the `API_BASE_URL` in `src/services/api.js`.

## Features Overview

### 1. User Authentication Flow
1. User visits the application
2. Redirected to login page if not authenticated
3. Can register new account or login with existing credentials
4. Upon successful authentication, redirected to chat interface
5. JWT token stored and used for subsequent requests

### 2. Chat Interface
1. Users see a welcome screen when no thread is selected
2. Can create new threads via "New Chat" button or file upload
3. Messages appear in rectangular bubbles with clear user/AI distinction
4. Real-time typing indicators during AI response
5. Copy message functionality available

### 3. File Upload Process
1. Users can drag files onto the chat input or click to browse
2. Files are uploaded with progress indication
3. New thread is created automatically upon file upload
4. Documents appear with preview indicators in the chat
5. Thread appears in sidebar with document icon

### 4. Thread Management
1. All user threads appear in the sidebar
2. Threads show file/document indicators when applicable
3. Users can switch between threads seamlessly
4. Thread history is preserved across sessions

## Troubleshooting

### Common Issues

1. **Login/Signup not working**: Ensure backend server is running on port 8000
2. **File upload failing**: Check file size limits and backend upload endpoint
3. **Messages not sending**: Verify JWT token is valid and backend is accessible
4. **Styling issues**: Clear browser cache and ensure all CSS files are loaded

### Development Tips

1. Use browser developer tools to monitor network requests
2. Check console for any JavaScript errors
3. Verify backend API responses match expected format
4. Test with different file types and sizes

## Contributing

When contributing to this project:

1. Follow the existing code style and naming conventions
2. Add proper error handling for new features
3. Include loading states for async operations
4. Test all user flows thoroughly
5. Update documentation for new features

## Technology Stack

- **React 18** - Frontend framework
- **Vite** - Build tool and dev server
- **CSS3** - Styling
- **JavaScript ES6+** - Programming language
- **Fetch API** - HTTP client for backend communication

Built with ❤️ for enterprise knowledge synthesis.
