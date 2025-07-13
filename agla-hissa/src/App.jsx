/**
 * Main Application Component
 * 
 * Handles authentication state, routing, and user session management.
 * Provides a protected route system where unauthenticated users are
 * redirected to login, and authenticated users can access the chat interface.
 * 
 * Features:
 * - JWT-based authentication
 * - Persistent user sessions via localStorage
 * - Protected routing
 * - Global user state management
 */

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './routes/Login';
import SignUp from './routes/signUp';
import ChatPage from './routes/chatPage';
import NavBar from './components/NavBar';
import './App.css';

function App() {
  // Authentication and user state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userData, setUserData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Check authentication status on app initialization
   * Validates stored JWT token and user data from localStorage
   * Sets authentication state accordingly
   */
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('jwt');
      const storedUserData = localStorage.getItem('userData');
      
      // Validate both token and user data exist
      if (token && storedUserData) {
        try {
          const parsedUserData = JSON.parse(storedUserData);
          setIsAuthenticated(true);
          setUserData(parsedUserData);
        } catch (error) {
          console.error('Error parsing stored user data:', error);
          // Clear invalid data
          localStorage.removeItem('jwt');
          localStorage.removeItem('userData');
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  /**
   * Handle successful user login
   * Stores JWT token and user data in localStorage
   * Updates authentication state
   */
  const handleLogin = (token, user) => {
    localStorage.setItem('jwt', token);
    localStorage.setItem('userData', JSON.stringify(user));
    setIsAuthenticated(true);
    setUserData(user);
  };

  /**
   * Handle user logout
   * Clears stored authentication data and resets state
   */
  const handleLogout = () => {
    localStorage.removeItem('jwt');
    localStorage.removeItem('userData');
    setIsAuthenticated(false);
    setUserData(null);
  };

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <Router>
      <div className="App min-h-screen bg-gray-50">
        {/* Navigation Bar */}
        <NavBar 
          isAuthenticated={isAuthenticated}
          userData={userData}
          onLogout={handleLogout}
        />
        
        <Routes>
          {/* Public routes */}
          <Route 
            path="/login" 
            element={
              isAuthenticated ? 
                <Navigate to="/chat" replace /> : 
                <Login onLogin={handleLogin} />
            } 
          />
          <Route 
            path="/signup" 
            element={
              isAuthenticated ? 
                <Navigate to="/chat" replace /> : 
                <SignUp onLogin={handleLogin} />
            } 
          />
          
          {/* Protected routes */}
          <Route 
            path="/chat" 
            element={
              isAuthenticated ? 
                <ChatPage 
                  userData={userData} 
                  setUserData={setUserData}
                  onLogout={handleLogout}
                /> : 
                <Navigate to="/login" replace />
            } 
          />
          
          {/* Default redirect */}
          <Route 
            path="/" 
            element={
              <Navigate to={isAuthenticated ? "/chat" : "/login"} replace />
            } 
          />
          
          {/* Catch all route */}
          <Route 
            path="*" 
            element={
              <Navigate to={isAuthenticated ? "/chat" : "/login"} replace />
            } 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
