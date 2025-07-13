import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './routes/Login';
import SignUp from './routes/signUp';
import ChatPage from './routes/chatPage';
import NavBar from './components/NavBar';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userData, setUserData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('jwt');
      const storedUserData = localStorage.getItem('userData');
      
      if (token && storedUserData) {
        try {
          const parsedUserData = JSON.parse(storedUserData);
          setIsAuthenticated(true);
          setUserData(parsedUserData);
        } catch (error) {
          console.error('Error parsing stored user data:', error);
          localStorage.removeItem('jwt');
          localStorage.removeItem('userData');
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const handleLogin = (token, user) => {
    localStorage.setItem('jwt', token);
    localStorage.setItem('userData', JSON.stringify(user));
    setIsAuthenticated(true);
    setUserData(user);
  };

  const handleLogout = () => {
    localStorage.removeItem('jwt');
    localStorage.removeItem('userData');
    setIsAuthenticated(false);
    setUserData(null);
  };

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
        <NavBar 
          isAuthenticated={isAuthenticated}
          userData={userData}
          onLogout={handleLogout}
        />
        
        <Routes>
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
                <SignUp />
            } 
          />
          
          <Route 
            path="/chat" 
            element={
              isAuthenticated ? 
                <ChatPage 
                  userData={userData} 
                  setUserData={setUserData}
                /> : 
                <Navigate to="/login" replace />
            } 
          />
          
          <Route 
            path="/" 
            element={
              <Navigate to={isAuthenticated ? "/chat" : "/login"} replace />
            } 
          />
          
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
