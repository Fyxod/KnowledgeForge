import React, { useState } from 'react';
import './App.css';
import LoginButton from './components/loginButton';
import InputBox from './components/inputBox';
import axios from 'axios';

function App() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name,setName] = useState('');

 const signupUser = async () => {
  try {
    const response = await axios.post('http://127.0.0.1:8000/user', {
      email,
      password,
      name
    });

    console.log('User created:', response.data.user);
    localStorage.setItem('userId', response.data.user.userId);

  } catch (err) {
    console.error('Signup failed:', err.response?.data || err.message);
  }
};

  return (
    <div className="bg-dblue border-2 border-rose-50 absolute w-screen h-screen flex flex-col items-center justify-center gap-4">
      <InputBox text="Enter your email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <InputBox text="Enter your password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <InputBox text="Enter your name" value={name} onChange={(e) => setName(e.target.value)} />

      <LoginButton text="Login / Sign up" onClick={signupUser} />
    </div>
  );
}

export default App;
