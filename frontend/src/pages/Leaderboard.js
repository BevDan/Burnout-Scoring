import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Trophy, ArrowLeft, Medal, Award } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getAuthHeaders = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
});

export default function Leaderboard({ user }) {
  const navigate = useNavigate();
  const [rounds, setRounds] = useState([]);
  const [classes, setClasses] = useState([]);
  const [selectedRound, setSelectedRound] = useState(null);
  const [selectedClass, setSelectedClass] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRounds();
    fetchClasses();
  }, []);

  useEffect(() => {
    if (selectedRound) {
      fetchLeaderboard();
    }
  }, [selectedRound, selectedClass]);

  const fetchRounds = async () => {
    try {
      const response = await axios.get(`${API}/admin/rounds`, getAuthHeaders());
      setRounds(response.data);
      if (response.data.length > 0) {
        setSelectedRound(response.data[0].id);
      }
    } catch (error) {
      toast.error('Failed to load rounds');
    }
  };

  const fetchClasses = async () => {
    try {
      const response = await axios.get(`${API}/admin/classes`, getAuthHeaders());
      setClasses(response.data);
    } catch (error) {
      toast.error('Failed to load classes');
    }
  };

  const fetchLeaderboard = async () => {
    if (!selectedRound) return;
    
    setLoading(true);
    try {
      const url = selectedClass 
        ? `${API}/leaderboard/${selectedRound}?class_id=${selectedClass}`
        : `${API}/leaderboard/${selectedRound}`;
      const response = await axios.get(url, getAuthHeaders());
      setLeaderboard(response.data);
    } catch (error) {
      toast.error('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  const getRankIcon = (rank) => {
    if (rank === 1) return <Trophy className="w-8 h-8 text-[#ffd700]" />;
    if (rank === 2) return <Medal className="w-8 h-8 text-[#c0c0c0]" />;
    if (rank === 3) return <Award className="w-8 h-8 text-[#cd7f32]" />;
    return null;
  };

  const getRankClass = (rank) => {
    if (rank === 1) return 'rank-1';
    if (rank === 2) return 'rank-2';
    if (rank === 3) return 'rank-3';
    return '';
  };

  return (
    <div className="min-h-screen bg-[#09090b] noise-overlay" data-testid="leaderboard-page">
      <div 
        className="absolute top-0 left-0 right-0 h-64 bg-cover bg-center opacity-20"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1593166978275-5dbc8b293c3c')`,
        }}
      />

      <div className="relative z-10">
        <header className="bg-[#18181b]/80 backdrop-blur-xl border-b border-[#27272a] px-4 py-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex justify-between items-center mb-6">
              <Button
                onClick={() => navigate(user.role === 'admin' ? '/admin' : '/judge')}
                variant="outline"
                className="border-[#27272a]"
                data-testid="back-button"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </div>

            <div className="text-center mb-6">
              <div className="flex justify-center mb-4">
                <div className="p-4 bg-[#f97316] rounded-lg neon-glow">
                  <Trophy className="w-12 h-12 text-white" />
                </div>
              </div>
              <h1 className="heading-font text-4xl md:text-6xl font-black tracking-tighter text-white mb-2 speed-skew">
                LEADERBOARD
              </h1>
              <p className="ui-font text-lg tracking-wide text-[#a1a1aa]">
                COMPETITION RANKINGS
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="ui-font text-sm font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
                  Round
                </label>
                <Select value={selectedRound || ''} onValueChange={setSelectedRound}>
                  <SelectTrigger className="bg-[#18181b] border-[#27272a] text-white h-12" data-testid="round-select">
                    <SelectValue placeholder="Select round" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#18181b] border-[#27272a]">
                    {rounds.map((round) => (
                      <SelectItem key={round.id} value={round.id}>
                        {round.name} - {round.date}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="ui-font text-sm font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
                  Filter by Class
                </label>
                <Select value={selectedClass || 'all'} onValueChange={(v) => setSelectedClass(v === 'all' ? null : v)}>
                  <SelectTrigger className="bg-[#18181b] border-[#27272a] text-white h-12" data-testid="class-filter-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#18181b] border-[#27272a]">
                    <SelectItem value="all">All Classes</SelectItem>
                    {classes.map((cls) => (
                      <SelectItem key={cls.id} value={cls.id}>{cls.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 py-8">
          {loading ? (
            <div className="text-center py-12">
              <p className="text-[#a1a1aa] ui-font text-xl">Loading leaderboard...</p>
            </div>
          ) : leaderboard.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-[#a1a1aa] ui-font text-xl">No scores available for this round</p>
            </div>
          ) : (
            <div className="space-y-4">
              {leaderboard.map((entry, index) => {
                const rank = index + 1;
                return (
                  <div
                    key={entry.competitor_id}
                    className={`leaderboard-row glass-panel p-6 rounded-lg border border-[#27272a] ${getRankClass(rank)}`}
                    style={{ animationDelay: `${index * 0.1}s` }}
                    data-testid={`leaderboard-entry-${rank}`}
                  >
                    <div className="flex items-center gap-6">
                      <div className="w-16 text-center">
                        {getRankIcon(rank) || (
                          <span className="data-font text-4xl font-bold text-[#a1a1aa]">{rank}</span>
                        )}
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="data-font text-2xl md:text-3xl font-bold text-[#f97316]">#{entry.car_number}</span>
                          <div>
                            <h3 className="ui-font text-xl md:text-2xl font-bold text-white">{entry.competitor_name}</h3>
                            <p className="text-sm text-[#a1a1aa]">{entry.vehicle_info}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="inline-block px-3 py-1 bg-[#f97316] text-white text-xs font-bold rounded">
                            {entry.class_name}
                          </span>
                          <span className="data-font text-xs text-[#a1a1aa]">
                            {entry.score_count} {entry.score_count === 1 ? 'score' : 'scores'}
                          </span>
                        </div>
                      </div>

                      <div className="text-right">
                        <p className="ui-font text-xs tracking-wide text-[#a1a1aa] uppercase mb-1">Average</p>
                        <p className="data-font text-4xl md:text-5xl font-bold text-[#f97316]" data-testid={`score-${rank}`}>
                          {entry.average_score}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}