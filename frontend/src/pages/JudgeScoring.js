import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { LogOut, Trophy, Flame, Minus, Plus, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
  const [competitors, setCompetitors] = useState([]);
  const [selectedCompetitor, setSelectedCompetitor] = useState(null);
  const [myScores, setMyScores] = useState([]);
  const [showReview, setShowReview] = useState(false);

  const [scoreData, setScoreData] = useState({
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
    fetchMyScores();
  }, []);

  useEffect(() => {
    if (selectedRound) {
      fetchCompetitors();
    }
  }, [selectedRound]);

  const fetchRounds = async () => {
    try {
      const response = await axios.get(`${API}/admin/rounds`, getAuthHeaders());
      const activeRounds = response.data.filter(r => r.status === 'active');
      setRounds(activeRounds);
    } catch (error) {
      toast.error('Failed to load rounds');
    }
  };

  const fetchCompetitors = async () => {
    try {
      const response = await axios.get(`${API}/judge/competitors/${selectedRound}`, getAuthHeaders());
      setCompetitors(response.data);
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
              onClick={() => navigate('/leaderboard')}
              className="bg-[#22c55e] hover:bg-[#16a34a] text-white"
              size="sm"
              data-testid="view-leaderboard-button"
            >
              <Trophy className="w-4 h-4" />
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
                <SelectValue placeholder="Choose a competitor" />
              </SelectTrigger>
              <SelectContent className="bg-[#18181b] border-[#27272a]">
                {competitors.map((comp) => (
                  <SelectItem key={comp.id} value={comp.id}>
                    #{comp.car_number} - {comp.name} ({comp.class_name})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {selectedCompetitor && (
          <div className="glass-panel p-6 rounded-lg border-l-4 border-[#f97316] space-y-4">
            <div className="flex items-center gap-3">
              <span className="data-font text-4xl font-bold text-[#f97316]">#{selectedCompetitor.car_number}</span>
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
            <PenaltyCounter
              label="Failed to Drive Off Pad"
              points={10}
              value={scoreData.penalty_failed_drive_off}
              onChange={(v) => updatePenalty('penalty_failed_drive_off', v)}
              testId="penalty-failed-drive-off"
            />
            <PenaltyCounter
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
    </div>
  );
}

function ScoreInput({ label, value, max, onChange, points, testId }) {
  return (
    <div className="score-stepper">
      <div className="flex justify-between items-center mb-2">
        <label className="ui-font text-lg font-semibold tracking-wide text-white">{label}</label>
        <span className="data-font text-sm text-[#a1a1aa]">Max: {max}</span>
      </div>
      <div className="flex items-center gap-4 mb-3">
        <button
          onClick={() => onChange(value - 1)}
          className="w-16 h-16 bg-[#27272a] hover:bg-[#3f3f46] rounded text-white text-2xl font-bold transition-colors"
          data-testid={`${testId}-minus`}
        >
          <Minus className="w-6 h-6 mx-auto" />
        </button>
        <div className="flex-1 text-center">
          <div className="data-font text-5xl font-bold text-[#f97316]" data-testid={`${testId}-value`}>{value}</div>
          {points !== undefined && (
            <div className="text-sm text-[#22c55e] mt-1">= {points} points</div>
          )}
        </div>
        <button
          onClick={() => onChange(value + 1)}
          className="w-16 h-16 btn-primary rounded text-white text-2xl font-bold"
          data-testid={`${testId}-plus`}
        >
          <Plus className="w-6 h-6 mx-auto" />
        </button>
      </div>
      <input
        type="range"
        min="0"
        max={max}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
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

function ScoreReviewDialog({ open, onOpenChange, scores, onScoreUpdated }) {
  const [editingScore, setEditingScore] = useState(null);
  const [editData, setEditData] = useState(null);

  const startEdit = (score) => {
    setEditingScore(score.id);
    setEditData({
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
                    <span className="data-font text-2xl font-bold text-[#f97316]">#{score.car_number}</span>
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
                      <label className="text-sm text-[#a1a1aa]">Instant Smoke (0-10)</label>
                      <input
                        type="number"
                        min="0"
                        max="10"
                        value={editData.instant_smoke}
                        onChange={(e) => setEditData({...editData, instant_smoke: parseInt(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Constant Smoke (0-20)</label>
                      <input
                        type="number"
                        min="0"
                        max="20"
                        value={editData.constant_smoke}
                        onChange={(e) => setEditData({...editData, constant_smoke: parseInt(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Volume of Smoke (0-20)</label>
                      <input
                        type="number"
                        min="0"
                        max="20"
                        value={editData.volume_of_smoke}
                        onChange={(e) => setEditData({...editData, volume_of_smoke: parseInt(e.target.value) || 0})}
                        className="w-full mt-1 px-3 py-2 bg-[#09090b] border border-[#27272a] rounded text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm text-[#a1a1aa]">Driving Skill (0-40)</label>
                      <input
                        type="number"
                        min="0"
                        max="40"
                        value={editData.driving_skill}
                        onChange={(e) => setEditData({...editData, driving_skill: parseInt(e.target.value) || 0})}
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
                        <span className="text-xs text-[#a1a1aa]">Failed Drive Off</span>
                        <input
                          type="number"
                          min="0"
                          value={editData.penalty_failed_drive_off}
                          onChange={(e) => setEditData({...editData, penalty_failed_drive_off: parseInt(e.target.value) || 0})}
                          className="w-full mt-1 px-2 py-1 bg-[#09090b] border border-[#27272a] rounded text-white text-sm"
                        />
                      </div>
                      <div>
                        <span className="text-xs text-[#a1a1aa]">Large Fire</span>
                        <input
                          type="number"
                          min="0"
                          value={editData.penalty_large_fire}
                          onChange={(e) => setEditData({...editData, penalty_large_fire: parseInt(e.target.value) || 0})}
                          className="w-full mt-1 px-2 py-1 bg-[#09090b] border border-[#27272a] rounded text-white text-sm"
                        />
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
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm mb-3">
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