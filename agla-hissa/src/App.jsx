import React, { useState } from 'react';
import './App.css';
import LoginButton from './components/loginButton';
import InputBox from './components/inputBox';
import axios from 'axios';
import { useNavigate,BrowserRouter , Routes, Route } from 'react-router-dom';
import Signup from './routes/signUp';
import Login from './routes/Login';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* <Route path="/login" element={<LoginPage />} /> */}
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
