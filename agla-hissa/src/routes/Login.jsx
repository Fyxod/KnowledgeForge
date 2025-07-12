import React, { useState } from 'react';
import '../App.css';
import Button from '../components/loginButton';
import InputBox from '../components/inputBox';
import axios from 'axios';

function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [temid, setTemid] = useState('');

    const Login = async () => {
        try {
            const response = await axios.post('http://127.0.0.1:8000/user/login', {
                email,
                password,
            });

            console.log('Login response:', response.data);
            localStorage.setItem('jwt', `Bearer ${response.data.token}`);
        } catch (err) {
            console.error('Login failed:', err.response?.data || err.message);
        }
    };



    return (

        <div className="bg-dblue border-2 border-rose-50 absolute w-screen h-screen flex flex-col items-center justify-center gap-4">
            <InputBox text="Enter your email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <InputBox text="Enter your password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />

            <Button text=" login " onClick={Login} />
        </div>
    );
}

export default Login;
