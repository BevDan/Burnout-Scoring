import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import Login from '@/pages/Login';
import AdminDashboard from '@/pages/AdminDashboard';
import JudgeScoring from '@/pages/JudgeScoring';
import Leaderboard from '@/pages/Leaderboard';
import '@/App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    if (token && userData) {
      setUser(JSON.parse(userData));
    }
    setLoading(false);
  }, []);

  const handleLogin = (token, userData) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  if (loading) {
    return <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
      <div className="text-white">Loading...</div>
    </div>;
  }

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={
            user ? <Navigate to={user.role === 'admin' ? '/admin' : '/judge'} /> : <Login onLogin={handleLogin} />
          } />
          <Route path="/admin" element={
            user && user.role === 'admin' ? <AdminDashboard user={user} onLogout={handleLogout} /> : <Navigate to="/login" />
          } />
          <Route path="/judge" element={
            user && user.role === 'judge' ? <JudgeScoring user={user} onLogout={handleLogout} /> : <Navigate to="/login" />
          } />
          <Route path="/leaderboard" element={
            user ? <Leaderboard user={user} onLogout={handleLogout} /> : <Navigate to="/login" />
          } />
          <Route path="/" element={
            <Navigate to={user ? (user.role === 'admin' ? '/admin' : '/judge') : '/login'} />
          } />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </div>
  );
}

export default App;