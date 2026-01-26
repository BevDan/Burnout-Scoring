import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Trophy, ArrowLeft, Medal, Award, Printer, Settings2 } from 'lucide-react';
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
  const printRef = useRef();
  const [rounds, setRounds] = useState([]);
  const [classes, setClasses] = useState([]);
  const [events, setEvents] = useState([]);
  const [selectedRound, setSelectedRound] = useState(null);
  const [selectedClass, setSelectedClass] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Load preferences from localStorage
  const [scoreDisplay, setScoreDisplay] = useState(() => {
    return localStorage.getItem('leaderboard_scoreDisplay') || 'average';
  });
  const [leaderboardType, setLeaderboardType] = useState('round');
  const [showScoresOnPrint, setShowScoresOnPrint] = useState(() => {
    const saved = localStorage.getItem('leaderboard_showScores');
    return saved !== null ? saved === 'true' : true;
  });
  
  // Logo and website settings for printing
  const [logo, setLogo] = useState(null);
  const [websiteSettings, setWebsiteSettings] = useState({ website_url: '', organization_name: '' });

  // Save preferences to localStorage when they change
  useEffect(() => {
    localStorage.setItem('leaderboard_scoreDisplay', scoreDisplay);
  }, [scoreDisplay]);

  useEffect(() => {
    localStorage.setItem('leaderboard_showScores', showScoresOnPrint.toString());
  }, [showScoresOnPrint]);

  useEffect(() => {
    fetchRounds();
    fetchClasses();
    fetchEvents();
    fetchSettings();
  }, []);

  useEffect(() => {
    if (leaderboardType === 'round' && selectedRound) {
      fetchLeaderboard();
    } else if (leaderboardType === 'minor') {
      fetchMinorRoundsLeaderboard();
    }
  }, [selectedRound, selectedClass, leaderboardType]);

  const fetchSettings = async () => {
    try {
      const [logoRes, websiteRes] = await Promise.all([
        axios.get(`${API}/admin/settings/logo`),
        axios.get(`${API}/admin/settings/website`)
      ]);
      setLogo(logoRes.data.logo);
      setWebsiteSettings(websiteRes.data);
    } catch (error) {
      // Settings might not exist yet
    }
  };

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

  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${API}/admin/events`, getAuthHeaders());
      setEvents(response.data);
    } catch (error) {
      // Events might not exist yet
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
      
      // Sort based on scoreDisplay preference
      const sorted = [...response.data].sort((a, b) => {
        if (scoreDisplay === 'total') {
          return b.total_score - a.total_score;
        }
        return b.average_score - a.average_score;
      });
      setLeaderboard(sorted);
    } catch (error) {
      toast.error('Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchMinorRoundsLeaderboard = async () => {
    setLoading(true);
    try {
      const url = selectedClass 
        ? `${API}/leaderboard/minor-rounds/cumulative?class_id=${selectedClass}`
        : `${API}/leaderboard/minor-rounds/cumulative`;
      const response = await axios.get(url, getAuthHeaders());
      
      // Sort based on scoreDisplay preference
      const sorted = [...response.data].sort((a, b) => {
        if (scoreDisplay === 'total') {
          return b.total_score - a.total_score;
        }
        return b.average_score - a.average_score;
      });
      setLeaderboard(sorted);
    } catch (error) {
      toast.error('Failed to load minor rounds leaderboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Re-sort when scoreDisplay changes
    if (leaderboard.length > 0) {
      const sorted = [...leaderboard].sort((a, b) => {
        if (scoreDisplay === 'total') {
          return b.total_score - a.total_score;
        }
        return b.average_score - a.average_score;
      });
      setLeaderboard(sorted);
    }
  }, [scoreDisplay]);

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

  const getActiveEvent = () => {
    return events.find(e => e.is_active !== false);
  };

  const getSelectedRoundName = () => {
    const round = rounds.find(r => r.id === selectedRound);
    return round?.name || '';
  };

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    
    const activeEvent = getActiveEvent();
    const roundName = leaderboardType === 'round' ? getSelectedRoundName() : 'Minor Rounds Cumulative';
    const className = selectedClass ? classes.find(c => c.id === selectedClass)?.name : 'All Classes';
    const now = new Date();
    const timestamp = now.toLocaleString('en-AU', { 
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: true
    });
    
    // Build title from event name and date
    const reportTitle = activeEvent 
      ? `${activeEvent.name} - ${activeEvent.date}`
      : 'Burnout Competition';
    
    printWindow.document.write(`
      <html>
        <head>
          <title>${reportTitle}</title>
          <style>
            * { box-sizing: border-box; }
            body { 
              font-family: Arial, sans-serif; 
              padding: 20px 40px; 
              margin: 0;
              color: #000;
            }
            
            /* Header with logo */
            .header {
              display: flex;
              align-items: flex-start;
              margin-bottom: 20px;
              padding-bottom: 15px;
              border-bottom: 1px solid #ccc;
            }
            .logo-container {
              flex-shrink: 0;
              margin-right: 20px;
            }
            .logo {
              max-height: 70px;
              max-width: 200px;
              object-fit: contain;
            }
            .header-text {
              flex: 1;
              text-align: center;
            }
            .event-title {
              font-size: 22px;
              font-weight: bold;
              margin-bottom: 8px;
            }
            .header-spacer {
              width: 200px;
              flex-shrink: 0;
            }
            
            /* Subtitle section */
            .subtitle-row {
              display: flex;
              justify-content: flex-start;
              gap: 40px;
              margin-bottom: 15px;
              font-size: 14px;
            }
            .subtitle-item {
              display: flex;
              gap: 8px;
            }
            .subtitle-label {
              font-weight: bold;
            }
            
            /* Table */
            table { 
              width: 100%; 
              border-collapse: collapse; 
              margin-top: 10px;
              font-size: 13px;
            }
            th, td { 
              border: 1px solid #000; 
              padding: 8px 10px; 
              text-align: left; 
            }
            th { 
              background-color: #f0f0f0; 
              font-weight: bold;
              font-size: 12px;
            }
            .rank-col { 
              width: 50px; 
              text-align: center; 
            }
            .car-col { 
              width: 80px; 
              font-weight: bold;
            }
            .score-col { 
              width: 80px; 
              text-align: right; 
              font-weight: bold;
            }
            
            /* Top 3 highlighting */
            .rank-1 { background-color: #fffde7; }
            .rank-2 { background-color: #f5f5f5; }
            .rank-3 { background-color: #fff3e0; }
            
            /* Footer */
            .footer {
              display: flex;
              justify-content: space-between;
              margin-top: 30px;
              padding-top: 15px;
              border-top: 1px solid #ccc;
              font-size: 11px;
              color: #666;
            }
            
            @media print {
              body { 
                -webkit-print-color-adjust: exact; 
                print-color-adjust: exact; 
              }
              @page { margin: 1cm; }
            }
          </style>
        </head>
        <body>
          <div class="header">
            ${logo ? `
              <div class="logo-container">
                <img src="${logo}" alt="Logo" class="logo" />
              </div>
            ` : ''}
            <div class="header-text">
              <div class="event-title">${reportTitle}</div>
            </div>
            ${logo ? '<div class="header-spacer"></div>' : ''}
          </div>
          
          <div class="subtitle-row">
            <div class="subtitle-item">
              <span class="subtitle-label">Burnout Class</span>
              <span>${className}</span>
            </div>
            <div class="subtitle-item">
              <span class="subtitle-label">For</span>
              <span>${roundName}</span>
            </div>
          </div>
          
          <table>
            <thead>
              <tr>
                <th class="rank-col"></th>
                <th class="car-col">Car Number</th>
                <th>Competitor</th>
                ${showScoresOnPrint ? `<th class="score-col">${scoreDisplay === 'total' ? 'Total' : 'Average'}</th>` : ''}
              </tr>
            </thead>
            <tbody>
              ${leaderboard.map((entry, index) => `
                <tr class="${index < 3 ? `rank-${index + 1}` : ''}">
                  <td class="rank-col">${index + 1}</td>
                  <td class="car-col">${entry.car_number}</td>
                  <td>${entry.competitor_name}</td>
                  ${showScoresOnPrint ? `<td class="score-col">${scoreDisplay === 'total' ? entry.total_score : entry.average_score}</td>` : ''}
                </tr>
              `).join('')}
            </tbody>
          </table>
          
          <div class="footer">
            <span>${timestamp}</span>
            <span>${websiteSettings.website_url || ''}</span>
          </div>
        </body>
      </html>
    `);
    printWindow.document.close();
    
    // Wait for logo image to load before printing
    if (logo) {
      const logoImg = printWindow.document.querySelector('.logo');
      if (logoImg) {
        logoImg.onload = () => {
          printWindow.print();
        };
        logoImg.onerror = () => {
          // Print anyway if logo fails to load
          printWindow.print();
        };
        // If image is already loaded (cached), print immediately
        if (logoImg.complete) {
          printWindow.print();
        }
      } else {
        printWindow.print();
      }
    } else {
      printWindow.print();
    }
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
              
              <Button
                onClick={handlePrint}
                className="btn-primary"
                disabled={leaderboard.length === 0}
              >
                <Printer className="w-4 h-4 mr-2" />
                Print Report
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

            {/* Settings Row */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
              <div>
                <label className="ui-font text-xs font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
                  Leaderboard Type
                </label>
                <Select value={leaderboardType} onValueChange={setLeaderboardType}>
                  <SelectTrigger className="bg-[#18181b] border-[#27272a] text-white h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#18181b] border-[#27272a]">
                    <SelectItem value="round">Single Round</SelectItem>
                    <SelectItem value="minor">Minor Rounds (Cumulative)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {leaderboardType === 'round' && (
                <div>
                  <label className="ui-font text-xs font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
                    Round
                  </label>
                  <Select value={selectedRound || ''} onValueChange={setSelectedRound}>
                    <SelectTrigger className="bg-[#18181b] border-[#27272a] text-white h-12" data-testid="round-select">
                      <SelectValue placeholder="Select round" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#18181b] border-[#27272a]">
                      {rounds.map((round) => (
                        <SelectItem key={round.id} value={round.id}>
                          {round.name} {round.is_minor && '(Minor)'}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div>
                <label className="ui-font text-xs font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
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

              <div>
                <label className="ui-font text-xs font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
                  Score Display
                </label>
                <Select value={scoreDisplay} onValueChange={setScoreDisplay}>
                  <SelectTrigger className="bg-[#18181b] border-[#27272a] text-white h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#18181b] border-[#27272a]">
                    <SelectItem value="average">Average Score</SelectItem>
                    <SelectItem value="total">Total Score</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="ui-font text-xs font-semibold tracking-wide text-[#a1a1aa] uppercase block mb-2">
                  Print Options
                </label>
                <div className="flex items-center gap-2 h-12 px-3 bg-[#18181b] border border-[#27272a] rounded-md">
                  <input
                    type="checkbox"
                    id="showScores"
                    checked={showScoresOnPrint}
                    onChange={(e) => setShowScoresOnPrint(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="showScores" className="text-white text-sm cursor-pointer">Show Scores</label>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 py-8" ref={printRef}>
          {loading ? (
            <div className="text-center py-12">
              <p className="text-[#a1a1aa] ui-font text-xl">Loading leaderboard...</p>
            </div>
          ) : leaderboard.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-[#a1a1aa] ui-font text-xl">
                {leaderboardType === 'minor' 
                  ? 'No scores available for minor rounds. Make sure you have rounds marked as "Minor".'
                  : 'No scores available for this round'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {leaderboard.map((entry, index) => {
                const rank = index + 1;
                const displayScore = scoreDisplay === 'total' ? entry.total_score : entry.average_score;
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
                          <span className="car-number-font text-2xl md:text-3xl font-bold text-[#f97316]">#{entry.car_number}</span>
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
                            {entry.rounds_competed && ` from ${entry.rounds_competed} round${entry.rounds_competed === 1 ? '' : 's'}`}
                          </span>
                        </div>
                      </div>

                      <div className="text-right">
                        <p className="ui-font text-xs tracking-wide text-[#a1a1aa] uppercase mb-1">
                          {scoreDisplay === 'total' ? 'Total' : 'Average'}
                        </p>
                        <p className="data-font text-4xl md:text-5xl font-bold text-[#f97316]" data-testid={`score-${rank}`}>
                          {displayScore}
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
