import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { LogOut, Trophy, Flame, Minus, Plus, AlertTriangle, CheckCircle2, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getAuthHeaders = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
});

export default function JudgeScoring({ user, onLogout }) {
  const navigate = useNavigate();
  const [rounds, setRounds] = useState([]);
  const [selectedRound, setSelectedRound] = useState(null);
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState('all');
  const [competitors, setCompetitors] = useState([]);
  const [filteredCompetitors, setFilteredCompetitors] = useState([]);
  const [selectedCompetitor, setSelectedCompetitor] = useState(null);
  const [myScores, setMyScores] = useState([]);
  const [showReview, setShowReview] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileData, setProfileData] = useState({ name: '', password: '' });

  const [scoreData, setScoreData] = useState({
    tip_in: 0,
    instant_smoke: 0,
    constant_smoke: 0,
    volume_of_smoke: 0,
    driving_skill: 0,
    tyres_popped: 0,
    penalty_reversing: 0,
    penalty_stopping: 0,
    penalty_contact_barrier: 0,
    penalty_small_fire: 0,
    penalty_failed_drive_off: 0,
    penalty_large_fire: 0
  });

  useEffect(() => {
    fetchRounds();
    fetchClasses();
    fetchMyScores();
  }, []);

  useEffect(() => {
    if (selectedRound) {
      fetchCompetitors();
    }
  }, [selectedRound]);

  useEffect(() => {
    // Filter competitors based on selected class
    if (selectedClass === 'all') {
      setFilteredCompetitors(competitors);
    } else {
      setFilteredCompetitors(competitors.filter(c => c.class_id === selectedClass));
    }
    // Reset selected competitor when class changes
    setSelectedCompetitor(null);
  }, [selectedClass, competitors]);

  const fetchRounds = async () => {
    try {
      const response = await axios.get(`${API}/admin/rounds`, getAuthHeaders());
      // Filter for active rounds - handle both 'round_status' (from API) and 'status' fields
      const activeRounds = response.data.filter(r => 
        (r.round_status || r.status || 'active') === 'active'
      );
      setRounds(activeRounds);
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

  const fetchCompetitors = async () => {
    try {
      const response = await axios.get(`${API}/judge/competitors/${selectedRound}`, getAuthHeaders());
      setCompetitors(response.data);
      setSelectedClass('all'); // Reset class filter when round changes
    } catch (error) {
      toast.error('Failed to load competitors');
    }
  };

  const fetchMyScores = async () => {
    try {
      const response = await axios.get(`${API}/judge/scores`, getAuthHeaders());
      setMyScores(response.data);
    } catch (error) {
      toast.error('Failed to load your scores');
    }
  };

  const updateScore = (field, value, max) => {
    const newValue = Math.max(0, Math.min(max, value));
    setScoreData({ ...scoreData, [field]: newValue });
  };

  const updatePenalty = (field, value) => {
    const newValue = Math.max(0, value);
    setScoreData({ ...scoreData, [field]: newValue });
  };

  const calculateTotals = () => {
    const subtotal = 
      scoreData.tip_in +
      scoreData.instant_smoke +
      scoreData.constant_smoke +
      scoreData.volume_of_smoke +
      scoreData.driving_skill +
      (scoreData.tyres_popped * 5);

    const penalties = 
      (scoreData.penalty_reversing * 5) +
      (scoreData.penalty_stopping * 5) +
      (scoreData.penalty_contact_barrier * 5) +
      (scoreData.penalty_small_fire * 5) +
      (scoreData.penalty_failed_drive_off * 10) +
      (scoreData.penalty_large_fire * 10);

    return { subtotal, penalties, final: subtotal - penalties };
  };

  const handleSubmit = async () => {
    if (!selectedCompetitor) {
      toast.error('Please select a competitor');
      return;
    }

    try {
      await axios.post(`${API}/judge/scores`, {
        ...scoreData,
        competitor_id: selectedCompetitor.id,
        round_id: selectedRound
      }, getAuthHeaders());

      toast.success('Score submitted successfully!');
      
      // Reset form
      setScoreData({
        tip_in: 0,
        instant_smoke: 0,
        constant_smoke: 0,
        volume_of_smoke: 0,
        driving_skill: 0,
        tyres_popped: 0,
        penalty_reversing: 0,
        penalty_stopping: 0,
        penalty_contact_barrier: 0,
        penalty_small_fire: 0,
        penalty_failed_drive_off: 0,
        penalty_large_fire: 0
      });
      setSelectedCompetitor(null);
      fetchMyScores();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit score');
    }
  };

  const handleProfileUpdate = async () => {
    try {
      const updateData = {};
      if (profileData.name) updateData.name = profileData.name;
      if (profileData.password) updateData.password = profileData.password;

      if (Object.keys(updateData).length === 0) {
        toast.error('Please provide name or password to update');
        return;
      }

      await axios.put(`${API}/auth/profile`, updateData, getAuthHeaders());
      toast.success('Profile updated successfully');
      setProfileOpen(false);
      setProfileData({ name: '', password: '' });
      
      if (updateData.name) {
        const userData = JSON.parse(localStorage.getItem('user'));
        userData.name = updateData.name;
        localStorage.setItem('user', JSON.stringify(userData));
        window.location.reload();
      }
    } catch (error) {
      toast.error('Failed to update profile');
    }
  };

  const totals = calculateTotals();

  return (
    <div className="min-h-screen bg-[#09090b] noise-overlay" data-testid="judge-scoring-page">
      <header className="bg-[#18181b] border-b border-[#27272a] px-4 py-4">
        <div className="max-w-4xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#f97316] rounded">
              <Flame className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="heading-font text-xl md:text-2xl font-bold tracking-tighter text-white">JUDGE SCORING</h1>
              <p className="text-sm text-[#a1a1aa]">Judge: {user.name}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => setShowReview(true)}
              className="bg-[#0ea5e9] hover:bg-[#0284c7] text-white"
              size="sm"
              data-testid="review-scores-button"
            >
              My Scores
            </Button>
            <Button 
              onClick={() => setProfileOpen(true)}
              variant="outline" 
              className="border-[#27272a]" 
              size="sm"
              data-testid="judge-settings-button"
            >
              <Settings className="w-4 h-4" />
            </Button>
            <Button onClick={onLogout} variant="outline" className="border-[#27272a]" size="sm" data-testid="logout-button">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="ui-font text-sm font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
              Select Round
            </label>
            <Select value={selectedRound || ''} onValueChange={setSelectedRound}>
              <SelectTrigger className="bg-[#18181b] border-[#27272a] text-white h-14" data-testid="round-select">
                <SelectValue placeholder="Choose a round" />
              </SelectTrigger>
              <SelectContent className="bg-[#18181b] border-[#27272a]">
                {rounds.map((round) => (
                  <SelectItem key={round.id} value={round.id}>{round.name} - {round.date}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="ui-font text-sm font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
              Select Competitor
            </label>
            <Select 
              value={selectedCompetitor?.id || ''} 
              onValueChange={(id) => setSelectedCompetitor(competitors.find(c => c.id === id))}
              disabled={!selectedRound}
            >
              <SelectTrigger className="bg-[#18181b] border-[#27272a] text-white h-14" data-testid="competitor-select">
                <SelectValue placeholder={!selectedRound ? "Select a round first" : competitors.length === 0 ? "No competitors available" : "Choose a competitor"} />
              </SelectTrigger>
              <SelectContent className="bg-[#18181b] border-[#27272a]">
                {competitors.length === 0 ? (
                  <div className="p-4 text-center text-[#a1a1aa]">
                    No competitors found. Contact admin to add competitors.
                  </div>
                ) : (
                  competitors.map((comp) => (
                    <SelectItem key={comp.id} value={comp.id}>
                      <span className="car-number-font">#{comp.car_number}</span> - {comp.name} ({comp.class_name})
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        {selectedCompetitor && (
          <div className="glass-panel p-6 rounded-lg border-l-4 border-[#f97316] space-y-4">
            <div className="flex items-center gap-3">
              <span className="car-number-font text-4xl font-bold text-[#f97316]">#{selectedCompetitor.car_number}</span>
              <div>
                <p className="ui-font text-2xl font-bold text-white">{selectedCompetitor.name}</p>
                <span className="inline-block mt-1 px-3 py-1 bg-[#f97316] text-white text-xs font-bold rounded">
                  {selectedCompetitor.class_name}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-[#18181b] p-3 rounded border border-[#27272a]">
                <label className="text-xs text-[#a1a1aa] uppercase block mb-1">Vehicle</label>
                <p className="text-white">{selectedCompetitor.vehicle_info}</p>
              </div>
              <div className="bg-[#18181b] p-3 rounded border border-[#27272a]">
                <label className="text-xs text-[#a1a1aa] uppercase block mb-1">Plate</label>
                <p className="text-[#22c55e] data-font font-semibold">{selectedCompetitor.plate}</p>
              </div>
            </div>
          </div>
        )}

        <div className="glass-panel p-6 rounded-lg border border-[#27272a] space-y-6">
          <h2 className="ui-font text-2xl font-bold tracking-wide text-white">SCORING</h2>

          <ScoreInput
            label="Tip In"
            value={scoreData.tip_in}
            max={10}
            onChange={(v) => updateScore('tip_in', v, 10)}
            testId="tip-in"
          />

          <ScoreInput
            label="Instant Smoke"
            value={scoreData.instant_smoke}
            max={10}
            onChange={(v) => updateScore('instant_smoke', v, 10)}
            testId="instant-smoke"
          />

          <ScoreInput
            label="Constant Smoke"
            value={scoreData.constant_smoke}
            max={20}
            onChange={(v) => updateScore('constant_smoke', v, 20)}
            testId="constant-smoke"
          />

          <ScoreInput
            label="Volume of Smoke"
            value={scoreData.volume_of_smoke}
            max={20}
            onChange={(v) => updateScore('volume_of_smoke', v, 20)}
            testId="volume-smoke"
          />

          <ScoreInput
            label="Driving Skill"
            value={scoreData.driving_skill}
            max={40}
            onChange={(v) => updateScore('driving_skill', v, 40)}
            testId="driving-skill"
          />

          <ScoreInput
            label="Tyres Popped (5pts each)"
            value={scoreData.tyres_popped}
            max={2}
            onChange={(v) => updateScore('tyres_popped', v, 2)}
            points={scoreData.tyres_popped * 5}
            testId="tyres-popped"
            integerOnly={true}
          />
        </div>

        <div className="glass-panel p-6 rounded-lg border border-[#27272a] space-y-4">
          <h2 className="ui-font text-2xl font-bold tracking-wide text-white flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-[#ef4444]" />
            PENALTIES
          </h2>

          <div className="grid md:grid-cols-2 gap-3">
            <PenaltyCounter
              label="Reversing"
              points={5}
              value={scoreData.penalty_reversing}
              onChange={(v) => updatePenalty('penalty_reversing', v)}
              testId="penalty-reversing"
            />
            <PenaltyCounter
              label="Stopping"
              points={5}
              value={scoreData.penalty_stopping}
              onChange={(v) => updatePenalty('penalty_stopping', v)}
              testId="penalty-stopping"
            />
            <PenaltyCounter
              label="Contact with Barrier"
              points={5}
              value={scoreData.penalty_contact_barrier}
              onChange={(v) => updatePenalty('penalty_contact_barrier', v)}
              testId="penalty-contact-barrier"
            />
            <PenaltyCounter
              label="Small Fire"
              points={5}
              value={scoreData.penalty_small_fire}
              onChange={(v) => updatePenalty('penalty_small_fire', v)}
              testId="penalty-small-fire"
            />
            <PenaltyToggle
              label="Failed to Drive Off Pad"
              points={10}
              value={scoreData.penalty_failed_drive_off}
              onChange={(v) => updatePenalty('penalty_failed_drive_off', v)}
              testId="penalty-failed-drive-off"
            />
            <PenaltyToggle
              label="Large Fire"
              points={10}
              value={scoreData.penalty_large_fire}
              onChange={(v) => updatePenalty('penalty_large_fire', v)}
              testId="penalty-large-fire"
            />
          </div>
        </div>

        <div className="glass-panel p-6 rounded-lg border-2 border-[#f97316] neon-glow space-y-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="ui-font text-sm tracking-wide text-[#a1a1aa] uppercase">Score</p>
              <p className="data-font text-4xl font-bold text-[#22c55e]" data-testid="score-subtotal">{totals.subtotal}</p>
            </div>
            <div>
              <p className="ui-font text-sm tracking-wide text-[#a1a1aa] uppercase">Penalties</p>
              <p className="data-font text-4xl font-bold text-[#ef4444]" data-testid="penalty-total">{totals.penalties > 0 ? '-' : ''}{totals.penalties}</p>
            </div>
            <div>
              <p className="ui-font text-sm tracking-wide text-[#a1a1aa] uppercase">Final Score</p>
              <p className="data-font text-5xl font-bold text-[#f97316]" data-testid="final-score">{totals.final}</p>
            </div>
          </div>

          <Button
            onClick={handleSubmit}
            className="w-full h-16 btn-primary ui-font text-2xl font-bold tracking-wide"
            disabled={!selectedCompetitor}
            data-testid="submit-score-button"
          >
            <CheckCircle2 className="w-8 h-8 mr-3" />
            SUBMIT SCORE
          </Button>
        </div>
      </main>

      <ScoreReviewDialog 
        open={showReview} 
        onOpenChange={setShowReview}
        scores={myScores}
        onScoreUpdated={fetchMyScores}
      />

      <Dialog open={profileOpen} onOpenChange={setProfileOpen}>
        <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
          <DialogHeader>
            <DialogTitle className="ui-font text-xl">Profile Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-[#09090b] p-3 rounded border border-[#27272a]">
              <p className="text-sm text-[#a1a1aa]">Username</p>
              <p className="text-white data-font">{user.username}</p>
            </div>
            <div>
              <Label>Display Name</Label>
              <Input
                value={profileData.name}
                onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                placeholder={user.name}
                className="bg-[#09090b] border-[#27272a]"
              />
              <p className="text-xs text-[#a1a1aa] mt-1">Leave blank to keep current: {user.name}</p>
            </div>
            <div>
              <Label>New Password</Label>
              <Input
                type="password"
                value={profileData.password}
                onChange={(e) => setProfileData({ ...profileData, password: e.target.value })}
                placeholder="Enter new password"
                className="bg-[#09090b] border-[#27272a]"
              />
              <p className="text-xs text-[#a1a1aa] mt-1">Leave blank to keep current password</p>
            </div>
            <Button onClick={handleProfileUpdate} className="w-full btn-primary">
              Update Profile
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ScoreInput({ label, value, max, onChange, points, testId, integerOnly = false }) {
  // Format display value - show .5 only when needed
  const displayValue = Number.isInteger(value) ? value : value.toFixed(1);
  const step = integerOnly ? 1 : 0.5;
  
  return (
    <div className="score-stepper">
      <div className="flex justify-between items-center mb-2">
        <label className="ui-font text-lg font-semibold tracking-wide text-white">{label}</label>
        <span className="data-font text-sm text-[#a1a1aa]">Max: {max}</span>
      </div>
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => onChange(Math.max(0, value - 1))}
          className={`${integerOnly ? 'w-16' : 'w-14'} h-14 bg-[#27272a] hover:bg-[#3f3f46] rounded text-white text-xl font-bold transition-colors`}
          data-testid={`${testId}-minus`}
        >
          <Minus className="w-5 h-5 mx-auto" />
        </button>
        {!integerOnly && (
          <button
            onClick={() => onChange(Math.max(0, value - 0.5))}
            className="w-12 h-14 bg-[#27272a] hover:bg-[#3f3f46] rounded text-white text-sm font-bold transition-colors"
            data-testid={`${testId}-minus-half`}
          >
            -0.5
          </button>
        )}
        <div className="flex-1 text-center">
          <div className="data-font text-5xl font-bold text-[#f97316]" data-testid={`${testId}-value`}>{displayValue}</div>
          {points !== undefined && (
            <div className="text-sm text-[#22c55e] mt-1">= {points} points</div>
          )}
        </div>
        {!integerOnly && (
          <button
            onClick={() => onChange(Math.min(max, value + 0.5))}
            className="w-12 h-14 bg-[#f97316] hover:bg-[#ea580c] rounded text-white text-sm font-bold transition-colors"
            data-testid={`${testId}-plus-half`}
          >
            +0.5
          </button>
        )}
        <button
          onClick={() => onChange(Math.min(max, value + 1))}
          className={`${integerOnly ? 'w-16' : 'w-14'} h-14 btn-primary rounded text-white text-xl font-bold`}
          data-testid={`${testId}-plus`}
        >
          <Plus className="w-5 h-5 mx-auto" />
        </button>
      </div>
      <input
        type="range"
        min="0"
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(integerOnly ? parseInt(e.target.value) : parseFloat(e.target.value))}
        className="w-full h-2 bg-[#27272a] rounded-lg appearance-none cursor-pointer slider"
        data-testid={`${testId}-slider`}
        style={{
          background: `linear-gradient(to right, #f97316 0%, #f97316 ${(value/max)*100}%, #27272a ${(value/max)*100}%, #27272a 100%)`
        }}
      />
    </div>
  );
}

function PenaltyCounter({ label, points, value, onChange, testId }) {
  const totalPenalty = value * points;
  
  return (
    <div className={`p-4 rounded border-2 transition-all ${
      value > 0
        ? 'bg-[#ef4444]/20 border-[#ef4444] neon-glow'
        : 'bg-[#18181b] border-[#27272a]'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="ui-font text-lg font-semibold text-white">{label}</span>
          <p className="text-xs text-[#a1a1aa]">-{points} pts each</p>
        </div>
        {value > 0 && <AlertTriangle className="w-5 h-5 text-[#ef4444]" />}
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={() => onChange(value - 1)}
          className="w-10 h-10 bg-[#27272a] hover:bg-[#3f3f46] rounded text-white font-bold transition-colors"
          data-testid={`${testId}-minus`}
        >
          <Minus className="w-4 h-4 mx-auto" />
        </button>
        <div className="flex-1 text-center">
          <div className="data-font text-3xl font-bold text-[#ef4444]" data-testid={testId}>{value}</div>
          {totalPenalty > 0 && (
            <div className="text-xs text-[#ef4444] mt-1">-{totalPenalty} pts</div>
          )}
        </div>
        <button
          onClick={() => onChange(value + 1)}
          className="w-10 h-10 bg-[#ef4444] hover:bg-[#dc2626] rounded text-white font-bold transition-colors"
          data-testid={`${testId}-plus`}
        >
          <Plus className="w-4 h-4 mx-auto" />
        </button>
      </div>
    </div>
  );
}

function PenaltyToggle({ label, points, value, onChange, testId }) {
  const isActive = value > 0;
  
  return (
    <div 
      className={`p-4 rounded border-2 transition-all cursor-pointer ${
        isActive
          ? 'bg-[#ef4444]/20 border-[#ef4444] neon-glow'
          : 'bg-[#18181b] border-[#27272a] hover:border-[#3f3f46]'
      }`}
      onClick={() => onChange(isActive ? 0 : 1)}
      data-testid={testId}
    >
      <div className="flex items-center justify-between">
        <div>
          <span className="ui-font text-lg font-semibold text-white">{label}</span>
          <p className="text-xs text-[#a1a1aa]">-{points} pts (one-time)</p>
        </div>
        <div className="flex items-center gap-3">
          {isActive && (
            <span className="data-font text-xl font-bold text-[#ef4444]">-{points}</span>
          )}
          <div className={`w-12 h-7 rounded-full transition-colors relative ${
            isActive ? 'bg-[#ef4444]' : 'bg-[#27272a]'
          }`}>
            <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-all ${
              isActive ? 'left-6' : 'left-1'
            }`} />
          </div>
        </div>
      </div>
    </div>
  );
}

function ScoreReviewDialog({ open, onOpenChange, scores, onScoreUpdated }) {
  const [editingScore, setEditingScore] = useState(null);
  const [editData, setEditData] = useState(null);

  const startEdit = (score) => {
    setEditingScore(score.id);
    setEditData({
      tip_in: score.tip_in || 0,
      instant_smoke: score.instant_smoke,
      constant_smoke: score.constant_smoke,
      volume_of_smoke: score.volume_of_smoke,
      driving_skill: score.driving_skill,
      tyres_popped: score.tyres_popped,
      penalty_reversing: score.penalty_reversing,
      penalty_stopping: score.penalty_stopping,
      penalty_contact_barrier: score.penalty_contact_barrier,
      penalty_small_fire: score.penalty_small_fire,
      penalty_failed_drive_off: score.penalty_failed_drive_off,
      penalty_large_fire: score.penalty_large_fire
    });
  };

  const cancelEdit = () => {
    setEditingScore(null);
    setEditData(null);
  };

  const saveEdit = async () => {
    try {
      await axios.put(`${API}/judge/scores/${editingScore}`, editData, getAuthHeaders());
      toast.success('Score updated successfully');
      setEditingScore(null);
      setEditData(null);
      onScoreUpdated();
    } catch (error) {
      toast.error('Failed to update score');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#18181b] border-[#27272a] text-white max-w-5xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="ui-font text-2xl">MY SUBMITTED SCORES</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {scores.map((score) => (
            <div key={score.id} className="bg-[#09090b] p-5 rounded border border-[#27272a]">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="car-number-font text-2xl font-bold text-[#f97316]">#{score.car_number}</span>
                    <div>
                      <p className="ui-font text-xl font-bold text-white">{score.competitor_name}</p>
                      <p className="text-sm text-[#a1a1aa]">{score.round_name}</p>
                    </div>
                  </div>
                  {score.edited_at && (
                    <div className="flex items-center gap-2 mt-2">
                      <AlertTriangle className="w-4 h-4 text-[#f59e0b]" />
                      <span className="text-xs text-[#f59e0b]">
                        Edited: {new Date(score.edited_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <p className="data-font text-4xl font-bold text-[#f97316]">{score.final_score}</p>
                  <p className="text-xs text-[#a1a1aa] mt-1">
                    Submitted: {new Date(score.submitted_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {editingScore === score.id ? (
                <div className="space-y-4 bg-[#18181b] p-4 rounded">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Tip In (0-10)</label>
                      <input
                        type="number"
                        min="0"
                        max="10"
                        step="0.5"
                        value={editData.tip_in}
                        onChange={(e) => setEditData({...editData, tip_in: parseFloat(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Instant Smoke (0-10)</label>
                      <input
                        type="number"
                        min="0"
                        max="10"
                        step="0.5"
                        value={editData.instant_smoke}
                        onChange={(e) => setEditData({...editData, instant_smoke: parseFloat(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Constant Smoke (0-20)</label>
                      <input
                        type="number"
                        min="0"
                        max="20"
                        step="0.5"
                        value={editData.constant_smoke}
                        onChange={(e) => setEditData({...editData, constant_smoke: parseFloat(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Volume of Smoke (0-20)</label>
                      <input
                        type="number"
                        min="0"
                        max="20"
                        step="0.5"
                        value={editData.volume_of_smoke}
                        onChange={(e) => setEditData({...editData, volume_of_smoke: parseFloat(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Driving Skill (0-40)</label>
                      <input
                        type="number"
                        min="0"
                        max="40"
                        step="0.5"
                        value={editData.driving_skill}
                        onChange={(e) => setEditData({...editData, driving_skill: parseFloat(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Tyres Popped (0-2)</label>
                      <input
                        type="number"
                        min="0"
                        max="2"
                        value={editData.tyres_popped}
                        onChange={(e) => setEditData({...editData, tyres_popped: parseInt(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-[#a1a1aa] block mb-2">Penalties</label>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <span className="text-xs text-[#a1a1aa]">Reversing</span>
                        <input
                          type="number"
                          min="0"
                          value={editData.penalty_reversing}
                          onChange={(e) => setEditData({...editData, penalty_reversing: parseInt(e.target.value) || 0})}
                          className="w-full mt-1 px-2 py-1 bg-[#09090b] border border-[#27272a] rounded text-white text-sm"
                        />
                      </div>
                      <div>
                        <span className="text-xs text-[#a1a1aa]">Stopping</span>
                        <input
                          type="number"
                          min="0"
                          value={editData.penalty_stopping}
                          onChange={(e) => setEditData({...editData, penalty_stopping: parseInt(e.target.value) || 0})}
                          className="w-full mt-1 px-2 py-1 bg-[#09090b] border border-[#27272a] rounded text-white text-sm"
                        />
                      </div>
                      <div>
                        <span className="text-xs text-[#a1a1aa]">Barrier</span>
                        <input
                          type="number"
                          min="0"
                          value={editData.penalty_contact_barrier}
                          onChange={(e) => setEditData({...editData, penalty_contact_barrier: parseInt(e.target.value) || 0})}
                          className="w-full mt-1 px-2 py-1 bg-[#09090b] border border-[#27272a] rounded text-white text-sm"
                        />
                      </div>
                      <div>
                        <span className="text-xs text-[#a1a1aa]">Small Fire</span>
                        <input
                          type="number"
                          min="0"
                          value={editData.penalty_small_fire}
                          onChange={(e) => setEditData({...editData, penalty_small_fire: parseInt(e.target.value) || 0})}
                          className="w-full mt-1 px-2 py-1 bg-[#09090b] border border-[#27272a] rounded text-white text-sm"
                        />
                      </div>
                      <div>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editData.penalty_failed_drive_off > 0}
                            onChange={(e) => setEditData({...editData, penalty_failed_drive_off: e.target.checked ? 1 : 0})}
                            className="w-4 h-4 rounded border-[#27272a] bg-[#09090b]"
                          />
                          <span className="text-xs text-[#a1a1aa]">Failed Drive Off (-10)</span>
                        </label>
                      </div>
                      <div>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editData.penalty_large_fire > 0}
                            onChange={(e) => setEditData({...editData, penalty_large_fire: e.target.checked ? 1 : 0})}
                            className="w-4 h-4 rounded border-[#27272a] bg-[#09090b]"
                          />
                          <span className="text-xs text-[#a1a1aa]">Large Fire (-10)</span>
                        </label>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-3 pt-2">
                    <Button onClick={saveEdit} className="flex-1 btn-primary">
                      Save Changes
                    </Button>
                    <Button onClick={cancelEdit} variant="outline" className="flex-1 border-[#27272a]">
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-sm mb-3">
                    <div className="bg-[#18181b] p-2 rounded">
                      <span className="text-[#a1a1aa] block text-xs">Tip In</span>
                      <span className="data-font text-white font-bold">{score.tip_in || 0}</span>
                    </div>
                    <div className="bg-[#18181b] p-2 rounded">
                      <span className="text-[#a1a1aa] block text-xs">Instant Smoke</span>
                      <span className="data-font text-white font-bold">{score.instant_smoke}</span>
                    </div>
                    <div className="bg-[#18181b] p-2 rounded">
                      <span className="text-[#a1a1aa] block text-xs">Constant</span>
                      <span className="data-font text-white font-bold">{score.constant_smoke}</span>
                    </div>
                    <div className="bg-[#18181b] p-2 rounded">
                      <span className="text-[#a1a1aa] block text-xs">Volume</span>
                      <span className="data-font text-white font-bold">{score.volume_of_smoke}</span>
                    </div>
                    <div className="bg-[#18181b] p-2 rounded">
                      <span className="text-[#a1a1aa] block text-xs">Driving</span>
                      <span className="data-font text-white font-bold">{score.driving_skill}</span>
                    </div>
                    <div className="bg-[#18181b] p-2 rounded">
                      <span className="text-[#a1a1aa] block text-xs">Tyres</span>
                      <span className="data-font text-white font-bold">{score.tyres_popped}</span>
                    </div>
                  </div>
                  {(score.penalty_reversing > 0 || score.penalty_stopping > 0 || score.penalty_contact_barrier > 0 ||
                    score.penalty_small_fire > 0 || score.penalty_failed_drive_off > 0 || score.penalty_large_fire > 0) && (
                    <div className="bg-[#ef4444]/10 p-3 rounded mb-3">
                      <p className="text-xs text-[#a1a1aa] mb-2">Penalties:</p>
                      <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs">
                        {score.penalty_reversing > 0 && <span className="text-[#ef4444]">Reversing: {score.penalty_reversing}</span>}
                        {score.penalty_stopping > 0 && <span className="text-[#ef4444]">Stopping: {score.penalty_stopping}</span>}
                        {score.penalty_contact_barrier > 0 && <span className="text-[#ef4444]">Barrier: {score.penalty_contact_barrier}</span>}
                        {score.penalty_small_fire > 0 && <span className="text-[#ef4444]">Small Fire: {score.penalty_small_fire}</span>}
                        {score.penalty_failed_drive_off > 0 && <span className="text-[#ef4444]">Failed Drive: {score.penalty_failed_drive_off}</span>}
                        {score.penalty_large_fire > 0 && <span className="text-[#ef4444]">Large Fire: {score.penalty_large_fire}</span>}
                      </div>
                    </div>
                  )}
                  <div className="flex justify-between items-center">
                    <div className="flex gap-4 text-sm">
                      <span className="text-[#22c55e]">Subtotal: <span className="data-font font-bold">{score.score_subtotal}</span></span>
                      <span className="text-[#ef4444]">Penalties: <span className="data-font font-bold">-{score.penalty_total}</span></span>
                    </div>
                    <Button onClick={() => startEdit(score)} size="sm" className="bg-[#0ea5e9] hover:bg-[#0284c7]">
                      Edit Score
                    </Button>
                  </div>
                </>
              )}
            </div>
          ))}
          {scores.length === 0 && (
            <p className="text-center text-[#a1a1aa] py-8">No scores submitted yet</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}