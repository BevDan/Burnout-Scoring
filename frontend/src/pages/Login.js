import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Flame } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/login`, {
        username,
        password
      });

      toast.success('Login successful!');
      onLogin(response.data.token, response.data.user);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden" data-testid="login-page">
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1759951124076-691c4ce81571')`,
        }}
      />
      <div className="absolute inset-0 bg-black/80" />
      
      <div className="relative z-10 min-h-screen flex items-center justify-center px-4">
        <div className="glass-panel w-full max-w-md p-8 rounded-lg border border-[#27272a] noise-overlay">
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-[#f97316] rounded-lg neon-glow">
                <Flame className="w-12 h-12 text-white" />
              </div>
            </div>
            <h1 className="heading-font text-4xl font-bold tracking-tighter text-white mb-2">
              BURNOUT
            </h1>
            <p className="ui-font text-lg tracking-wide text-[#a1a1aa]">
              SCOREKEEPER
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="ui-font text-sm font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-[#18181b] border border-[#27272a] rounded-md text-white focus:outline-none focus:border-[#f97316] focus:ring-1 focus:ring-[#f97316] transition-all"
                placeholder="Enter username"
                required
                data-testid="username-input"
              />
            </div>

            <div>
              <label className="ui-font text-sm font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-[#18181b] border border-[#27272a] rounded-md text-white focus:outline-none focus:border-[#f97316] focus:ring-1 focus:ring-[#f97316] transition-all"
                placeholder="Enter password"
                required
                data-testid="password-input"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-4 rounded-md ui-font text-lg font-bold tracking-wide text-white uppercase disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="login-button"
            >
              {loading ? 'LOGGING IN...' : 'LOGIN'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}