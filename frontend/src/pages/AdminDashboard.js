import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { LogOut, Users, Trophy, Calendar, Flag, Upload, Download, Settings, Trash2, AlertTriangle, ClipboardList, ImageIcon, Globe, X, AlertCircle, CheckCircle2, Mail, Send } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getAuthHeaders = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
});

export default function AdminDashboard({ user, onLogout }) {
  const navigate = useNavigate();
  const [judges, setJudges] = useState([]);
  const [classes, setClasses] = useState([]);
  const [competitors, setCompetitors] = useState([]);
  const [rounds, setRounds] = useState([]);
  const [events, setEvents] = useState([]);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileData, setProfileData] = useState({ name: '', password: '' });
  const [resetConfirm, setResetConfirm] = useState('');
  const [isResetting, setIsResetting] = useState(false);
  
  // Logo and website settings
  const [logo, setLogo] = useState(null);
  const [logoUploading, setLogoUploading] = useState(false);
  const [websiteSettings, setWebsiteSettings] = useState({ website_url: '', organization_name: '' });
  
  // SMTP Settings
  const [smtpSettings, setSmtpSettings] = useState({ 
    smtp_server: '', smtp_port: 587, smtp_email: '', smtp_password: '', smtp_use_tls: true 
  });
  const [smtpTesting, setSmtpTesting] = useState(false);
  
  // Scoring errors
  const [scoringErrors, setScoringErrors] = useState([]);
  
  // Pending emails
  const [pendingEmails, setPendingEmails] = useState({ total_competitors_scored: 0, competitors_pending_email: 0, competitors_list: [] });

  useEffect(() => {
    fetchAllData();
    fetchSettings();
    fetchScoringErrors();
    fetchPendingEmails();
  }, []);

  const fetchAllData = async () => {
    try {
      const [judgesRes, classesRes, competitorsRes, roundsRes, eventsRes] = await Promise.all([
        axios.get(`${API}/admin/judges`, getAuthHeaders()),
        axios.get(`${API}/admin/classes`, getAuthHeaders()),
        axios.get(`${API}/admin/competitors`, getAuthHeaders()),
        axios.get(`${API}/admin/rounds`, getAuthHeaders()),
        axios.get(`${API}/admin/events`, getAuthHeaders())
      ]);
      setJudges(judgesRes.data);
      setClasses(classesRes.data);
      setCompetitors(competitorsRes.data);
      setRounds(roundsRes.data);
      setEvents(eventsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

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
    // Fetch SMTP settings separately (requires auth)
    try {
      const smtpRes = await axios.get(`${API}/admin/settings/smtp`, getAuthHeaders());
      setSmtpSettings(smtpRes.data);
    } catch (error) {
      // SMTP settings might not exist yet
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setLogoUploading(true);
    try {
      await axios.post(`${API}/admin/settings/logo`, formData, {
        ...getAuthHeaders(),
        headers: {
          ...getAuthHeaders().headers,
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success('Logo uploaded successfully');
      fetchSettings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload logo');
    } finally {
      setLogoUploading(false);
    }
  };

  const handleDeleteLogo = async () => {
    try {
      await axios.delete(`${API}/admin/settings/logo`, getAuthHeaders());
      setLogo(null);
      toast.success('Logo deleted');
    } catch (error) {
      toast.error('Failed to delete logo');
    }
  };

  const handleWebsiteSettingsUpdate = async () => {
    try {
      await axios.put(
        `${API}/admin/settings/website?website_url=${encodeURIComponent(websiteSettings.website_url)}&organization_name=${encodeURIComponent(websiteSettings.organization_name)}`,
        {},
        getAuthHeaders()
      );
      toast.success('Website settings updated');
    } catch (error) {
      toast.error('Failed to update website settings');
    }
  };

  const fetchScoringErrors = async () => {
    try {
      const response = await axios.get(`${API}/admin/scoring-errors`, getAuthHeaders());
      setScoringErrors(response.data);
    } catch (error) {
      // Errors endpoint might not be critical
    }
  };

  const fetchPendingEmails = async () => {
    try {
      const response = await axios.get(`${API}/admin/pending-emails`, getAuthHeaders());
      setPendingEmails(response.data);
    } catch (error) {
      // Pending emails endpoint might not be critical
    }
  };

  const handleSmtpSettingsUpdate = async () => {
    try {
      await axios.put(`${API}/admin/settings/smtp`, smtpSettings, getAuthHeaders());
      toast.success('SMTP settings saved');
    } catch (error) {
      toast.error('Failed to save SMTP settings');
    }
  };

  const handleTestSmtp = async () => {
    setSmtpTesting(true);
    try {
      await axios.post(`${API}/admin/settings/smtp/test`, {}, getAuthHeaders());
      toast.success('SMTP connection successful!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'SMTP connection failed');
    } finally {
      setSmtpTesting(false);
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
      
      // Update local user data if name changed
      if (updateData.name) {
        const userData = JSON.parse(localStorage.getItem('user'));
        userData.name = updateData.name;
        localStorage.setItem('user', JSON.stringify(userData));
        window.location.reload(); // Reload to show new name
      }
    } catch (error) {
      toast.error('Failed to update profile');
    }
  };

  const handleReset = async (type) => {
    const confirmTexts = {
      scores: 'DELETE SCORES',
      competition: 'DELETE COMPETITION',
      full: 'DELETE ALL'
    };
    
    if (resetConfirm !== confirmTexts[type]) {
      toast.error(`Please type "${confirmTexts[type]}" to confirm`);
      return;
    }
    
    setIsResetting(true);
    try {
      const response = await axios.delete(`${API}/admin/reset/${type}`, getAuthHeaders());
      toast.success(response.data.message);
      setResetConfirm('');
      fetchAllData(); // Refresh all data
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Reset failed');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] noise-overlay" data-testid="admin-dashboard">
      <header className="bg-[#18181b] border-b border-[#27272a] px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#f97316] rounded">
              <Flag className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="heading-font text-2xl font-bold tracking-tighter text-white">ADMIN CONTROL</h1>
              <p className="text-sm text-[#a1a1aa]">Logged in as {user.name}</p>
            </div>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={async () => {
                try {
                  const response = await axios.get(`${API}/export/all-data`, {
                    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
                    responseType: 'blob'
                  });
                  const url = window.URL.createObjectURL(new Blob([response.data]));
                  const link = document.createElement('a');
                  link.href = url;
                  link.setAttribute('download', 'burnout_scoring_all_data.csv');
                  document.body.appendChild(link);
                  link.click();
                  link.remove();
                  toast.success('Data exported successfully');
                } catch (error) {
                  toast.error('Failed to export data');
                }
              }}
              className="bg-[#22c55e] hover:bg-[#16a34a] text-white"
              data-testid="download-all-data-button"
            >
              <Download className="w-4 h-4 mr-2" />
              Download All Data
            </Button>
            <Button
              onClick={() => navigate('/leaderboard')}
              className="bg-[#0ea5e9] hover:bg-[#0284c7] text-white"
              data-testid="view-leaderboard-button"
            >
              <Trophy className="w-4 h-4 mr-2" />
              Leaderboard
            </Button>
            <Button 
              onClick={() => setProfileOpen(true)} 
              variant="outline" 
              className="border-[#27272a]"
              data-testid="profile-settings-button"
            >
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
            <Button onClick={onLogout} variant="outline" className="border-[#27272a]" data-testid="logout-button">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Scoring Errors Alert */}
      {scoringErrors.length > 0 && (
        <div className="max-w-7xl mx-auto px-6 pt-6" data-testid="scoring-errors-section">
          <div className="bg-[#7f1d1d]/30 border border-[#ef4444] rounded-lg p-4">
            <div className="flex items-start gap-3 mb-3">
              <AlertCircle className="w-6 h-6 text-[#ef4444] flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="ui-font text-lg font-bold text-[#ef4444]">
                  Scoring Issues Detected ({scoringErrors.length})
                </h3>
                <p className="text-sm text-[#fca5a5]">
                  The following competitors have scoring issues that need attention.
                  Active judges: {judges.filter(j => j.is_active !== false).length}
                </p>
              </div>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {scoringErrors.map((error, idx) => (
                <div 
                  key={idx}
                  className="bg-[#09090b] p-3 rounded border border-[#27272a] flex items-center justify-between"
                >
                  <div className="flex items-center gap-4">
                    <span className="car-number-font text-lg font-bold text-[#f97316]">#{error.car_number}</span>
                    <div>
                      <p className="text-white font-medium">{error.competitor_name}</p>
                      <p className="text-xs text-[#a1a1aa]">{error.round_name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold ${
                      error.error_type === 'missing_scores' 
                        ? 'bg-[#f59e0b]/20 text-[#f59e0b]' 
                        : 'bg-[#ef4444]/20 text-[#ef4444]'
                    }`}>
                      {error.error_type === 'missing_scores' ? 'Missing Scores' : 'Duplicate Scores'}
                    </span>
                    <p className="text-xs text-[#a1a1aa] mt-1">{error.details}</p>
                    <p className="text-xs text-[#71717a]">
                      {error.judge_count}/{error.expected_count} judges
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <Button 
              onClick={fetchScoringErrors} 
              variant="outline" 
              size="sm" 
              className="mt-3 border-[#ef4444] text-[#ef4444] hover:bg-[#ef4444] hover:text-white"
            >
              Refresh Errors
            </Button>
          </div>
        </div>
      )}

      {/* No Errors - Success indicator */}
      {scoringErrors.length === 0 && judges.filter(j => j.is_active !== false).length > 0 && (
        <div className="max-w-7xl mx-auto px-6 pt-6">
          <div className="bg-[#14532d]/30 border border-[#22c55e] rounded-lg p-3 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-[#22c55e]" />
            <p className="text-[#86efac] text-sm">
              No scoring issues detected. Active judges: {judges.filter(j => j.is_active !== false).length}
            </p>
          </div>
        </div>
      )}

      {/* Pending Emails Indicator */}
      {pendingEmails.competitors_pending_email > 0 && (
        <div className="max-w-7xl mx-auto px-6 pt-4" data-testid="pending-emails-section">
          <div className="bg-[#422006]/50 border border-[#f59e0b] rounded-lg p-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-[#f59e0b] rounded-full px-3 py-1">
                <span className="ui-font text-lg font-bold text-black">{pendingEmails.competitors_pending_email}</span>
              </div>
              <p className="text-[#fbbf24] text-sm">
                Competitor score{pendingEmails.competitors_pending_email !== 1 ? 's' : ''} ready to email 
                <span className="text-[#a1a1aa] ml-1">
                  ({pendingEmails.total_competitors_scored} total scored)
                </span>
              </p>
            </div>
            <Button 
              onClick={fetchPendingEmails}
              variant="outline"
              size="sm"
              className="border-[#f59e0b] text-[#f59e0b] hover:bg-[#f59e0b] hover:text-black"
            >
              Refresh
            </Button>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-6 py-8">
        <Tabs defaultValue="judges" className="space-y-6">
          <TabsList className="bg-[#18181b] border border-[#27272a] p-1">
            <TabsTrigger value="judges" className="data-[state=active]:bg-[#f97316]">Judges</TabsTrigger>
            <TabsTrigger value="classes" className="data-[state=active]:bg-[#f97316]">Classes</TabsTrigger>
            <TabsTrigger value="competitors" className="data-[state=active]:bg-[#f97316]">Competitors</TabsTrigger>
            <TabsTrigger value="events" className="data-[state=active]:bg-[#f97316]">Events</TabsTrigger>
            <TabsTrigger value="rounds" className="data-[state=active]:bg-[#f97316]">Rounds</TabsTrigger>
            <TabsTrigger value="scores" className="data-[state=active]:bg-[#f97316]">Scores</TabsTrigger>
          </TabsList>

          <TabsContent value="judges">
            <JudgesPanel judges={judges} onRefresh={() => { fetchAllData(); fetchScoringErrors(); fetchPendingEmails(); }} />
          </TabsContent>

          <TabsContent value="classes">
            <ClassesPanel classes={classes} onRefresh={fetchAllData} />
          </TabsContent>

          <TabsContent value="competitors">
            <CompetitorsPanel competitors={competitors} classes={classes} onRefresh={fetchAllData} />
          </TabsContent>

          <TabsContent value="events">
            <EventsPanel events={events} onRefresh={fetchAllData} />
          </TabsContent>

          <TabsContent value="rounds">
            <RoundsPanel rounds={rounds} onRefresh={fetchAllData} />
          </TabsContent>

          <TabsContent value="scores">
            <ScoresPanel rounds={rounds} judges={judges} competitors={competitors} pendingEmails={pendingEmails} onRefresh={() => { fetchAllData(); fetchPendingEmails(); }} />
          </TabsContent>
        </Tabs>
      </main>

      <Dialog open={profileOpen} onOpenChange={(open) => { setProfileOpen(open); setResetConfirm(''); }}>
        <DialogContent className="bg-[#18181b] border-[#27272a] text-white max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="ui-font text-xl">Settings</DialogTitle>
          </DialogHeader>
          
          {/* Profile Section */}
          <div className="space-y-4">
            <h3 className="ui-font text-lg font-semibold text-white border-b border-[#27272a] pb-2">Profile</h3>
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
                data-testid="profile-name-input"
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
                data-testid="profile-password-input"
              />
              <p className="text-xs text-[#a1a1aa] mt-1">Leave blank to keep current password</p>
            </div>
            <Button onClick={handleProfileUpdate} className="w-full btn-primary" data-testid="update-profile-button">
              Update Profile
            </Button>
          </div>

          {/* Report Settings Section */}
          <div className="space-y-4 mt-6">
            <h3 className="ui-font text-lg font-semibold text-white border-b border-[#27272a] pb-2 flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-[#f97316]" />
              Report Settings
            </h3>
            
            {/* Logo Upload */}
            <div className="bg-[#09090b] p-4 rounded border border-[#27272a]">
              <p className="text-white font-semibold mb-2">Organization Logo</p>
              <p className="text-xs text-[#a1a1aa] mb-3">This logo will appear on printed reports and email reports. Max 2MB.</p>
              
              {logo ? (
                <div className="flex items-center gap-4">
                  <img src={logo} alt="Logo" className="h-16 object-contain bg-white rounded p-2" />
                  <Button 
                    onClick={handleDeleteLogo} 
                    variant="outline" 
                    size="sm"
                    className="border-[#ef4444] text-[#ef4444] hover:bg-[#ef4444] hover:text-white"
                  >
                    <X className="w-4 h-4 mr-1" />
                    Remove
                  </Button>
                </div>
              ) : (
                <div>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={handleLogoUpload}
                    className="hidden"
                    id="logo-upload"
                  />
                  <label htmlFor="logo-upload">
                    <Button 
                      asChild 
                      className="btn-primary cursor-pointer"
                      disabled={logoUploading}
                    >
                      <span>
                        <Upload className="w-4 h-4 mr-2" />
                        {logoUploading ? 'Uploading...' : 'Upload Logo'}
                      </span>
                    </Button>
                  </label>
                </div>
              )}
            </div>

            {/* Website Settings */}
            <div className="bg-[#09090b] p-4 rounded border border-[#27272a]">
              <p className="text-white font-semibold mb-2 flex items-center gap-2">
                <Globe className="w-4 h-4" />
                Website & Organization
              </p>
              <p className="text-xs text-[#a1a1aa] mb-3">These details appear in the footer of printed reports.</p>
              
              <div className="space-y-3">
                <div>
                  <Label className="text-xs">Organization Name</Label>
                  <Input
                    value={websiteSettings.organization_name}
                    onChange={(e) => setWebsiteSettings({ ...websiteSettings, organization_name: e.target.value })}
                    placeholder="e.g., Steel City Drags"
                    className="bg-[#18181b] border-[#27272a] text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Website URL</Label>
                  <Input
                    value={websiteSettings.website_url}
                    onChange={(e) => setWebsiteSettings({ ...websiteSettings, website_url: e.target.value })}
                    placeholder="e.g., steelcitydrags.com"
                    className="bg-[#18181b] border-[#27272a] text-sm"
                  />
                </div>
                <Button onClick={handleWebsiteSettingsUpdate} size="sm" className="btn-primary">
                  Save Settings
                </Button>
              </div>
            </div>
          </div>

          {/* Email/SMTP Settings Section */}
          <div className="space-y-4 mt-6">
            <h3 className="ui-font text-lg font-semibold text-white border-b border-[#27272a] pb-2 flex items-center gap-2">
              <Mail className="w-5 h-5 text-[#3b82f6]" />
              Email Settings (SMTP)
            </h3>
            
            <div className="bg-[#09090b] p-4 rounded border border-[#27272a]">
              <p className="text-xs text-[#a1a1aa] mb-3">Configure SMTP server to send score reports to competitors via email.</p>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">SMTP Server</Label>
                  <Input
                    value={smtpSettings.smtp_server}
                    onChange={(e) => setSmtpSettings({ ...smtpSettings, smtp_server: e.target.value })}
                    placeholder="e.g., smtp.gmail.com"
                    className="bg-[#18181b] border-[#27272a] text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Port</Label>
                  <Input
                    type="number"
                    value={smtpSettings.smtp_port}
                    onChange={(e) => setSmtpSettings({ ...smtpSettings, smtp_port: parseInt(e.target.value) || 587 })}
                    placeholder="587"
                    className="bg-[#18181b] border-[#27272a] text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Email Address</Label>
                  <Input
                    type="email"
                    value={smtpSettings.smtp_email}
                    onChange={(e) => setSmtpSettings({ ...smtpSettings, smtp_email: e.target.value })}
                    placeholder="your-email@example.com"
                    className="bg-[#18181b] border-[#27272a] text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Password / App Password</Label>
                  <Input
                    type="password"
                    value={smtpSettings.smtp_password}
                    onChange={(e) => setSmtpSettings({ ...smtpSettings, smtp_password: e.target.value })}
                    placeholder="••••••••"
                    className="bg-[#18181b] border-[#27272a] text-sm"
                  />
                </div>
              </div>
              
              <div className="flex items-center gap-2 mt-3">
                <input
                  type="checkbox"
                  id="smtp-tls"
                  checked={smtpSettings.smtp_use_tls}
                  onChange={(e) => setSmtpSettings({ ...smtpSettings, smtp_use_tls: e.target.checked })}
                  className="w-4 h-4"
                />
                <Label htmlFor="smtp-tls" className="text-xs">Use TLS (recommended for port 587)</Label>
              </div>
              
              <div className="flex gap-2 mt-4">
                <Button onClick={handleSmtpSettingsUpdate} size="sm" className="btn-primary">
                  Save SMTP Settings
                </Button>
                <Button 
                  onClick={handleTestSmtp} 
                  size="sm" 
                  variant="outline" 
                  className="border-[#3b82f6] text-[#3b82f6] hover:bg-[#3b82f6] hover:text-white"
                  disabled={smtpTesting || !smtpSettings.smtp_server}
                >
                  {smtpTesting ? 'Testing...' : 'Test Connection'}
                </Button>
              </div>
            </div>
          </div>

          {/* Data Management Section */}
          <div className="space-y-4 mt-6">
            <h3 className="ui-font text-lg font-semibold text-white border-b border-[#27272a] pb-2 flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-[#ef4444]" />
              Data Management
            </h3>
            
            <div className="bg-[#1c1917] p-4 rounded border border-[#ef4444]/30">
              <div className="flex items-start gap-3 mb-4">
                <AlertTriangle className="w-5 h-5 text-[#f59e0b] flex-shrink-0 mt-0.5" />
                <p className="text-sm text-[#a1a1aa]">
                  These actions are <span className="text-[#ef4444] font-bold">irreversible</span>. Type the confirmation text exactly to proceed.
                </p>
              </div>

              <div className="space-y-4">
                {/* Reset Scores Only */}
                <div className="bg-[#09090b] p-3 rounded border border-[#27272a]">
                  <p className="text-white font-semibold mb-1">Reset Scores Only</p>
                  <p className="text-xs text-[#a1a1aa] mb-2">Deletes all submitted scores. Keeps competitors, rounds, classes, and judges.</p>
                  <div className="flex gap-2">
                    <Input
                      value={resetConfirm}
                      onChange={(e) => setResetConfirm(e.target.value)}
                      placeholder='Type "DELETE SCORES" to confirm'
                      className="bg-[#18181b] border-[#27272a] text-sm flex-1"
                    />
                    <Button 
                      onClick={() => handleReset('scores')}
                      disabled={isResetting}
                      className="bg-[#f59e0b] hover:bg-[#d97706] text-black"
                      size="sm"
                    >
                      Reset
                    </Button>
                  </div>
                </div>

                {/* Reset Competition Data */}
                <div className="bg-[#09090b] p-3 rounded border border-[#27272a]">
                  <p className="text-white font-semibold mb-1">Reset Competition Data</p>
                  <p className="text-xs text-[#a1a1aa] mb-2">Deletes scores, competitors, rounds, and classes. Keeps judges and admin.</p>
                  <div className="flex gap-2">
                    <Input
                      value={resetConfirm}
                      onChange={(e) => setResetConfirm(e.target.value)}
                      placeholder='Type "DELETE COMPETITION" to confirm'
                      className="bg-[#18181b] border-[#27272a] text-sm flex-1"
                    />
                    <Button 
                      onClick={() => handleReset('competition')}
                      disabled={isResetting}
                      className="bg-[#ef4444] hover:bg-[#dc2626] text-white"
                      size="sm"
                    >
                      Reset
                    </Button>
                  </div>
                </div>

                {/* Full Reset */}
                <div className="bg-[#09090b] p-3 rounded border border-[#ef4444]/50">
                  <p className="text-[#ef4444] font-semibold mb-1">Full Reset</p>
                  <p className="text-xs text-[#a1a1aa] mb-2">Deletes EVERYTHING except your admin account. Use for starting a completely new competition.</p>
                  <div className="flex gap-2">
                    <Input
                      value={resetConfirm}
                      onChange={(e) => setResetConfirm(e.target.value)}
                      placeholder='Type "DELETE ALL" to confirm'
                      className="bg-[#18181b] border-[#ef4444]/30 text-sm flex-1"
                    />
                    <Button 
                      onClick={() => handleReset('full')}
                      disabled={isResetting}
                      className="bg-[#7f1d1d] hover:bg-[#991b1b] text-white"
                      size="sm"
                    >
                      Reset All
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function JudgesPanel({ judges, onRefresh }) {
  const [open, setOpen] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '', name: '' });

  const handleCreate = async () => {
    try {
      await axios.post(`${API}/auth/register`, { ...formData, role: 'judge' }, getAuthHeaders());
      toast.success('Judge created successfully');
      setOpen(false);
      setFormData({ username: '', password: '', name: '' });
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create judge');
    }
  };

  const handleDelete = async (judgeId) => {
    if (!window.confirm('Delete this judge?')) return;
    try {
      await axios.delete(`${API}/admin/judges/${judgeId}`, getAuthHeaders());
      toast.success('Judge deleted');
      onRefresh();
    } catch (error) {
      toast.error('Failed to delete judge');
    }
  };

  const handleToggleActive = async (judgeId) => {
    try {
      await axios.put(`${API}/admin/judges/${judgeId}/toggle-active`, {}, getAuthHeaders());
      onRefresh();
    } catch (error) {
      toast.error('Failed to update judge status');
    }
  };

  const activeCount = judges.filter(j => j.is_active !== false).length;

  return (
    <div className="glass-panel p-6 rounded-lg border border-[#27272a]">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="ui-font text-2xl font-bold tracking-wide text-white">JUDGES</h2>
          <p className="text-sm text-[#a1a1aa]">
            <span className="text-[#22c55e] font-semibold">{activeCount}</span> active judge{activeCount !== 1 ? 's' : ''} for this event
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="btn-primary" data-testid="add-judge-button">
              <Users className="w-4 h-4 mr-2" />
              Add Judge
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
            <DialogHeader>
              <DialogTitle className="ui-font text-xl">Create New Judge</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Username</Label>
                <Input
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                  data-testid="judge-username-input"
                />
              </div>
              <div>
                <Label>Password</Label>
                <Input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                  data-testid="judge-password-input"
                />
              </div>
              <div>
                <Label>Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                  data-testid="judge-name-input"
                />
              </div>
              <Button onClick={handleCreate} className="w-full btn-primary" data-testid="create-judge-button">
                Create Judge
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-3">
        {judges.map((judge) => {
          const isActive = judge.is_active !== false;
          return (
            <div 
              key={judge.id} 
              className={`bg-[#18181b] p-4 rounded border flex justify-between items-center ${
                isActive ? 'border-[#27272a]' : 'border-[#27272a] opacity-60'
              }`}
            >
              <div className="flex items-center gap-4">
                {/* Active Toggle */}
                <button
                  onClick={() => handleToggleActive(judge.id)}
                  className={`w-11 h-6 rounded-full transition-colors relative flex-shrink-0 ${
                    isActive ? 'bg-[#22c55e]' : 'bg-[#3f3f46]'
                  }`}
                  title={isActive ? 'Active - click to deactivate' : 'Inactive - click to activate'}
                  data-testid={`toggle-judge-${judge.id}`}
                >
                  <span 
                    className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-all duration-200 ${
                      isActive ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
                <div>
                  <p className={`ui-font text-lg font-semibold ${isActive ? 'text-white' : 'text-[#71717a]'}`}>
                    {judge.name}
                    {!isActive && <span className="ml-2 text-xs text-[#71717a]">(Inactive)</span>}
                  </p>
                  <p className="data-font text-sm text-[#a1a1aa]">{judge.username}</p>
                </div>
              </div>
              <Button
                onClick={() => handleDelete(judge.id)}
                variant="destructive"
                size="sm"
                data-testid={`delete-judge-${judge.id}`}
              >
                Delete
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ClassesPanel({ classes, onRefresh }) {
  const [open, setOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '' });

  const handleCreate = async () => {
    try {
      await axios.post(`${API}/admin/classes`, formData, getAuthHeaders());
      toast.success('Class created successfully');
      setOpen(false);
      setFormData({ name: '', description: '' });
      onRefresh();
    } catch (error) {
      toast.error('Failed to create class');
    }
  };

  const handleDelete = async (classId) => {
    if (!window.confirm('Delete this class?')) return;
    try {
      await axios.delete(`${API}/admin/classes/${classId}`, getAuthHeaders());
      toast.success('Class deleted');
      onRefresh();
    } catch (error) {
      toast.error('Failed to delete class');
    }
  };

  return (
    <div className="glass-panel p-6 rounded-lg border border-[#27272a]">
      <div className="flex justify-between items-center mb-6">
        <h2 className="ui-font text-2xl font-bold tracking-wide text-white">COMPETITION CLASSES</h2>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="btn-primary" data-testid="add-class-button">
              <Trophy className="w-4 h-4 mr-2" />
              Add Class
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
            <DialogHeader>
              <DialogTitle className="ui-font text-xl">Create New Class</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Class Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                  data-testid="class-name-input"
                />
              </div>
              <div>
                <Label>Description</Label>
                <Input
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                  data-testid="class-description-input"
                />
              </div>
              <Button onClick={handleCreate} className="w-full btn-primary" data-testid="create-class-button">
                Create Class
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-3">
        {classes.map((cls) => (
          <div key={cls.id} className="bg-[#18181b] p-4 rounded border border-[#27272a] flex justify-between items-center">
            <div>
              <p className="ui-font text-lg font-semibold text-white">{cls.name}</p>
              <p className="text-sm text-[#a1a1aa]">{cls.description}</p>
            </div>
            <Button
              onClick={() => handleDelete(cls.id)}
              variant="destructive"
              size="sm"
              data-testid={`delete-class-${cls.id}`}
            >
              Delete
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompetitorsPanel({ competitors, classes, onRefresh }) {
  const [open, setOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingCompetitor, setEditingCompetitor] = useState(null);
  const [csvData, setCsvData] = useState('');
  const [formData, setFormData] = useState({ name: '', car_number: '', vehicle_info: '', plate: '', class_id: '', email: '' });

  const handleCreate = async () => {
    try {
      await axios.post(`${API}/admin/competitors`, formData, getAuthHeaders());
      toast.success('Competitor created successfully');
      setOpen(false);
      setFormData({ name: '', car_number: '', vehicle_info: '', plate: '', class_id: '', email: '' });
      onRefresh();
    } catch (error) {
      toast.error('Failed to create competitor');
    }
  };

  const handleBulkImport = async () => {
    try {
      await axios.post(`${API}/admin/competitors/bulk`, csvData, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'text/plain'
        }
      });
      toast.success('Competitors imported successfully');
      setBulkOpen(false);
      setCsvData('');
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Import failed');
    }
  };

  const startEdit = (competitor) => {
    setEditingCompetitor(competitor);
    setFormData({
      name: competitor.name,
      car_number: competitor.car_number,
      vehicle_info: competitor.vehicle_info || '',
      plate: competitor.plate || '',
      class_id: competitor.class_id,
      email: competitor.email || ''
    });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    try {
      await axios.put(`${API}/admin/competitors/${editingCompetitor.id}`, formData, getAuthHeaders());
      toast.success('Competitor updated successfully');
      setEditOpen(false);
      setEditingCompetitor(null);
      setFormData({ name: '', car_number: '', vehicle_info: '', plate: '', class_id: '', email: '' });
      onRefresh();
    } catch (error) {
      toast.error('Failed to update competitor');
    }
  };

  const handleDelete = async (competitorId) => {
    if (!window.confirm('Delete this competitor?')) return;
    try {
      await axios.delete(`${API}/admin/competitors/${competitorId}`, getAuthHeaders());
      toast.success('Competitor deleted');
      onRefresh();
    } catch (error) {
      toast.error('Failed to delete competitor');
    }
  };

  return (
    <div className="glass-panel p-6 rounded-lg border border-[#27272a]">
      <div className="flex justify-between items-center mb-6">
        <h2 className="ui-font text-2xl font-bold tracking-wide text-white">COMPETITORS</h2>
        <div className="flex gap-3">
          <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#0ea5e9] hover:bg-[#0284c7]" data-testid="bulk-import-button">
                <Upload className="w-4 h-4 mr-2" />
                Bulk Import
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#18181b] border-[#27272a] text-white max-w-2xl">
              <DialogHeader>
                <DialogTitle className="ui-font text-xl">Bulk Import Competitors (CSV)</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>CSV Format: name,car_number,vehicle_info,plate,class_name,email</Label>
                  <p className="text-xs text-[#a1a1aa] mb-2">Use the class NAME (not ID). Email is optional.</p>
                  <textarea
                    value={csvData}
                    onChange={(e) => setCsvData(e.target.value)}
                    className="w-full h-48 p-3 bg-[#09090b] border border-[#27272a] rounded text-white data-font text-sm"
                    placeholder="name,car_number,vehicle_info,plate,class_name,email&#10;John Doe,42,Ford Mustang,BURNOUT1,Pro Class,john@email.com&#10;Jane Smith,88,Chevy Camaro,SMOKEY,Street Class,jane@email.com"
                    data-testid="csv-textarea"
                  />
                </div>
                <Button onClick={handleBulkImport} className="w-full btn-primary" data-testid="import-csv-button">
                  Import CSV
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="btn-primary" data-testid="add-competitor-button">
                Add Competitor
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
              <DialogHeader>
                <DialogTitle className="ui-font text-xl">Create New Competitor</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Name</Label>
                    <Input
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="bg-[#09090b] border-[#27272a]"
                      data-testid="competitor-name-input"
                    />
                  </div>
                  <div>
                    <Label>Car Number</Label>
                    <Input
                      value={formData.car_number}
                      onChange={(e) => setFormData({ ...formData, car_number: e.target.value })}
                      className="bg-[#09090b] border-[#27272a]"
                      data-testid="competitor-car-number-input"
                    />
                  </div>
                </div>
                <div>
                  <Label>Email Address</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="competitor@email.com"
                    className="bg-[#09090b] border-[#27272a]"
                    data-testid="competitor-email-input"
                  />
                </div>
                <div>
                  <Label>Vehicle Info</Label>
                  <Input
                    value={formData.vehicle_info}
                    onChange={(e) => setFormData({ ...formData, vehicle_info: e.target.value })}
                    className="bg-[#09090b] border-[#27272a]"
                    data-testid="competitor-vehicle-input"
                  />
                </div>
                <div>
                  <Label>Plate</Label>
                  <Input
                    value={formData.plate}
                    onChange={(e) => setFormData({ ...formData, plate: e.target.value })}
                    className="bg-[#09090b] border-[#27272a]"
                    data-testid="competitor-plate-input"
                  />
                </div>
                <div>
                  <Label>Class</Label>
                  <Select value={formData.class_id} onValueChange={(value) => setFormData({ ...formData, class_id: value })}>
                    <SelectTrigger className="bg-[#09090b] border-[#27272a]" data-testid="competitor-class-select">
                      <SelectValue placeholder="Select class" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#18181b] border-[#27272a]">
                      {classes.map((cls) => (
                        <SelectItem key={cls.id} value={cls.id}>{cls.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleCreate} className="w-full btn-primary" data-testid="create-competitor-button">
                  Create Competitor
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="space-y-3">
        {competitors.map((comp) => (
          <div key={comp.id} className="bg-[#18181b] p-4 rounded border-l-4 border-[#f97316] flex justify-between items-center">
            <div>
              <div className="flex items-center gap-3">
                <span className="car-number-font text-2xl font-bold text-[#f97316]">#{comp.car_number}</span>
                <div>
                  <p className="ui-font text-lg font-semibold text-white">{comp.name}</p>
                  <p className="text-sm text-[#a1a1aa]">{comp.vehicle_info}</p>
                  <p className="text-sm text-[#22c55e] data-font">Plate: {comp.plate}</p>
                  <p className="text-xs text-[#f97316] mt-1">{comp.class_name}</p>
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => startEdit(comp)}
                className="bg-[#f59e0b] hover:bg-[#d97706]"
                size="sm"
                data-testid={`edit-competitor-${comp.id}`}
              >
                Edit
              </Button>
              <Button
                onClick={() => handleDelete(comp.id)}
                variant="destructive"
                size="sm"
                data-testid={`delete-competitor-${comp.id}`}
              >
                Delete
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Edit Competitor Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
          <DialogHeader>
            <DialogTitle className="ui-font text-xl">Edit Competitor</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="bg-[#09090b] border-[#27272a]"
              />
            </div>
            <div>
              <Label>Car Number</Label>
              <Input
                value={formData.car_number}
                onChange={(e) => setFormData({ ...formData, car_number: e.target.value })}
                className="bg-[#09090b] border-[#27272a]"
              />
            </div>
            <div>
              <Label>Vehicle Info</Label>
              <Input
                value={formData.vehicle_info}
                onChange={(e) => setFormData({ ...formData, vehicle_info: e.target.value })}
                className="bg-[#09090b] border-[#27272a]"
              />
            </div>
            <div>
              <Label>Plate</Label>
              <Input
                value={formData.plate}
                onChange={(e) => setFormData({ ...formData, plate: e.target.value })}
                className="bg-[#09090b] border-[#27272a]"
              />
            </div>
            <div>
              <Label>Class</Label>
              <Select value={formData.class_id} onValueChange={(value) => setFormData({ ...formData, class_id: value })}>
                <SelectTrigger className="bg-[#09090b] border-[#27272a]">
                  <SelectValue placeholder="Select class" />
                </SelectTrigger>
                <SelectContent className="bg-[#18181b] border-[#27272a]">
                  {classes.map((cls) => (
                    <SelectItem key={cls.id} value={cls.id}>{cls.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleEdit} className="w-full btn-primary">
              Update Competitor
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}


function EventsPanel({ events, onRefresh }) {
  const [open, setOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [formData, setFormData] = useState({ name: '', date: '', is_active: true });

  const handleCreate = async () => {
    try {
      await axios.post(`${API}/admin/events`, formData, getAuthHeaders());
      toast.success('Event created successfully');
      setOpen(false);
      setFormData({ name: '', date: '', is_active: true });
      onRefresh();
    } catch (error) {
      toast.error('Failed to create event');
    }
  };

  const startEdit = (event) => {
    setEditingEvent(event);
    setFormData({ name: event.name, date: event.date, is_active: event.is_active !== false });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    try {
      await axios.put(`${API}/admin/events/${editingEvent.id}`, formData, getAuthHeaders());
      toast.success('Event updated successfully');
      setEditOpen(false);
      setEditingEvent(null);
      setFormData({ name: '', date: '', is_active: true });
      onRefresh();
    } catch (error) {
      toast.error('Failed to update event');
    }
  };

  const handleDelete = async (eventId) => {
    if (!window.confirm('Delete this event?')) return;
    try {
      await axios.delete(`${API}/admin/events/${eventId}`, getAuthHeaders());
      toast.success('Event deleted');
      onRefresh();
    } catch (error) {
      toast.error('Failed to delete event');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="ui-font text-2xl font-bold text-white">Events</h2>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="btn-primary">
              <Flag className="w-4 h-4 mr-2" />
              Add Event
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
            <DialogHeader>
              <DialogTitle className="ui-font text-xl">Create New Event</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Event Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Summer Burnouts 2025"
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div>
                <Label>Date</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-[#27272a] bg-[#09090b]"
                />
                <Label htmlFor="is_active" className="cursor-pointer">Active Event</Label>
              </div>
              <Button onClick={handleCreate} className="w-full btn-primary">
                Create Event
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
          <DialogHeader>
            <DialogTitle className="ui-font text-xl">Edit Event</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Event Name</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="bg-[#09090b] border-[#27272a]"
              />
            </div>
            <div>
              <Label>Date</Label>
              <Input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                className="bg-[#09090b] border-[#27272a]"
              />
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="edit_is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="w-4 h-4 rounded border-[#27272a] bg-[#09090b]"
              />
              <Label htmlFor="edit_is_active" className="cursor-pointer">Active Event</Label>
            </div>
            <Button onClick={handleEdit} className="w-full btn-primary">
              Update Event
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <div className="space-y-3">
        {events.length === 0 ? (
          <div className="text-center py-12 bg-[#18181b] rounded border border-[#27272a]">
            <Flag className="w-12 h-12 text-[#a1a1aa] mx-auto mb-3" />
            <p className="text-[#a1a1aa]">No events created yet. Click "Add Event" to get started.</p>
          </div>
        ) : (
          events.map((event) => (
            <div key={event.id} className="bg-[#18181b] p-4 rounded border border-[#27272a] flex justify-between items-center">
              <div>
                <p className="ui-font text-lg font-semibold text-white">{event.name}</p>
                <p className="text-sm text-[#a1a1aa]">{event.date}</p>
                <span className={`inline-block mt-2 px-3 py-1 rounded text-xs font-bold ${
                  event.is_active !== false ? 'bg-[#22c55e] text-black' : 'bg-[#71717a] text-white'
                }`}>
                  {event.is_active !== false ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => startEdit(event)}
                  className="bg-[#f59e0b] hover:bg-[#d97706]"
                  size="sm"
                >
                  Edit
                </Button>
                <Button
                  onClick={() => handleDelete(event.id)}
                  variant="destructive"
                  size="sm"
                >
                  Delete
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function RoundsPanel({ rounds, onRefresh }) {
  const [open, setOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingRound, setEditingRound] = useState(null);
  const [formData, setFormData] = useState({ name: '', is_minor: false, round_status: 'active' });

  const handleCreate = async () => {
    try {
      await axios.post(`${API}/admin/rounds`, formData, getAuthHeaders());
      toast.success('Round created successfully');
      setOpen(false);
      setFormData({ name: '', is_minor: false, round_status: 'active' });
      onRefresh();
    } catch (error) {
      toast.error('Failed to create round');
    }
  };

  const startEdit = (round) => {
    setEditingRound(round);
    setFormData({ name: round.name, is_minor: round.is_minor || false, round_status: round.round_status || 'active' });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    try {
      await axios.put(`${API}/admin/rounds/${editingRound.id}`, formData, getAuthHeaders());
      toast.success('Round updated successfully');
      setEditOpen(false);
      setEditingRound(null);
      setFormData({ name: '', is_minor: false, round_status: 'active' });
      onRefresh();
    } catch (error) {
      toast.error('Failed to update round');
    }
  };

  const handleDelete = async (roundId) => {
    if (!window.confirm('Delete this round?')) return;
    try {
      await axios.delete(`${API}/admin/rounds/${roundId}`, getAuthHeaders());
      toast.success('Round deleted');
      onRefresh();
    } catch (error) {
      toast.error('Failed to delete round');
    }
  };

  const handleExport = async (roundId) => {
    try {
      const response = await axios.get(`${API}/export/scores/${roundId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `scores_round_${roundId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Scores exported');
    } catch (error) {
      toast.error('Failed to export scores');
    }
  };

  return (
    <div className="glass-panel p-6 rounded-lg border border-[#27272a]">
      <div className="flex justify-between items-center mb-6">
        <h2 className="ui-font text-2xl font-bold tracking-wide text-white">ROUNDS</h2>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="btn-primary" data-testid="add-round-button">
              <Calendar className="w-4 h-4 mr-2" />
              Add Round
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
            <DialogHeader>
              <DialogTitle className="ui-font text-xl">Create New Round</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Round Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                  data-testid="round-name-input"
                />
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="is_minor"
                  checked={formData.is_minor}
                  onChange={(e) => setFormData({ ...formData, is_minor: e.target.checked })}
                  className="w-4 h-4 rounded border-[#27272a] bg-[#09090b]"
                />
                <Label htmlFor="is_minor" className="cursor-pointer">
                  Minor Round (for cumulative scoring before finals)
                </Label>
              </div>
              <div>
                <Label>Status</Label>
                <Select value={formData.round_status} onValueChange={(value) => setFormData({ ...formData, round_status: value })}>
                  <SelectTrigger className="bg-[#09090b] border-[#27272a]" data-testid="round-status-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#18181b] border-[#27272a]">
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={handleCreate} className="w-full btn-primary" data-testid="create-round-button">
                Create Round
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog open={editOpen} onOpenChange={setEditOpen}>
          <DialogContent className="bg-[#18181b] border-[#27272a] text-white">
            <DialogHeader>
              <DialogTitle className="ui-font text-xl">Edit Round</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Round Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="edit_is_minor"
                  checked={formData.is_minor}
                  onChange={(e) => setFormData({ ...formData, is_minor: e.target.checked })}
                  className="w-4 h-4 rounded border-[#27272a] bg-[#09090b]"
                />
                <Label htmlFor="edit_is_minor" className="cursor-pointer">
                  Minor Round (for cumulative scoring before finals)
                </Label>
              </div>
              <div>
                <Label>Status</Label>
                <Select value={formData.round_status} onValueChange={(value) => setFormData({ ...formData, round_status: value })}>
                  <SelectTrigger className="bg-[#09090b] border-[#27272a]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#18181b] border-[#27272a]">
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={handleEdit} className="w-full btn-primary">
                Update Round
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-3">
        {rounds.length === 0 ? (
          <div className="text-center py-12 bg-[#18181b] rounded border border-[#27272a]">
            <Calendar className="w-12 h-12 text-[#a1a1aa] mx-auto mb-3" />
            <p className="text-[#a1a1aa]">No rounds created yet. Click "Add Round" to get started.</p>
          </div>
        ) : (
          rounds.map((round) => (
            <div key={round.id} className="bg-[#18181b] p-4 rounded border border-[#27272a] flex justify-between items-center">
              <div>
                <p className="ui-font text-lg font-semibold text-white">{round.name}</p>
                <div className="flex gap-2 mt-2">
                  <span className={`inline-block px-3 py-1 rounded text-xs font-bold ${
                    (round.round_status || 'active') === 'active' ? 'bg-[#22c55e] text-black' : 'bg-[#71717a] text-white'
                  }`}>
                    {(round.round_status || 'active').toUpperCase()}
                  </span>
                  {round.is_minor && (
                    <span className="inline-block px-3 py-1 rounded text-xs font-bold bg-[#8b5cf6] text-white">
                      MINOR
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => startEdit(round)}
                  className="bg-[#f59e0b] hover:bg-[#d97706]"
                  size="sm"
                  data-testid={`edit-round-${round.id}`}
                >
                  Edit
                </Button>
                <Button
                  onClick={() => handleExport(round.id)}
                  className="bg-[#0ea5e9] hover:bg-[#0284c7]"
                  size="sm"
                  data-testid={`export-round-${round.id}`}
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </Button>
                <Button
                  onClick={() => handleDelete(round.id)}
                  variant="destructive"
                  size="sm"
                  data-testid={`delete-round-${round.id}`}
                >
                  Delete
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}


function ScoresPanel({ rounds, judges, competitors, pendingEmails, onRefresh }) {
  const [scores, setScores] = useState([]);
  const [filterRound, setFilterRound] = useState('all');
  const [filterJudge, setFilterJudge] = useState('all');
  const [sortBy, setSortBy] = useState('car_number');
  const [loading, setLoading] = useState(false);
  const [editScore, setEditScore] = useState(null);
  const [editData, setEditData] = useState({});
  const [emailDialog, setEmailDialog] = useState(null);
  const [emailAddress, setEmailAddress] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);
  const [bulkEmailDialog, setBulkEmailDialog] = useState(false);
  const [bulkEmailData, setBulkEmailData] = useState([]);
  const [sendingBulk, setSendingBulk] = useState(false);

  const fetchScores = async () => {
    setLoading(true);
    try {
      let url = `${API}/admin/scores`;
      const params = new URLSearchParams();
      if (filterRound !== 'all') params.append('round_id', filterRound);
      if (filterJudge !== 'all') params.append('judge_id', filterJudge);
      if (params.toString()) url += `?${params.toString()}`;
      
      const response = await axios.get(url, getAuthHeaders());
      setScores(response.data);
    } catch (error) {
      toast.error('Failed to load scores');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScores();
  }, [filterRound, filterJudge]);

  const handleDelete = async (scoreId) => {
    if (!window.confirm('Delete this score? This cannot be undone.')) return;
    try {
      await axios.delete(`${API}/admin/scores/${scoreId}`, getAuthHeaders());
      toast.success('Score deleted');
      fetchScores();
      onRefresh();
    } catch (error) {
      toast.error('Failed to delete score');
    }
  };

  const handleEdit = (score) => {
    setEditScore(score);
    setEditData({
      tip_in: score.tip_in || 0,
      instant_smoke: score.instant_smoke || 0,
      constant_smoke: score.constant_smoke || 0,
      volume_of_smoke: score.volume_of_smoke || 0,
      driving_skill: score.driving_skill || 0,
      tyres_popped: score.tyres_popped || 0,
      penalty_reversing: score.penalty_reversing || 0,
      penalty_stopping: score.penalty_stopping || 0,
      penalty_contact_barrier: score.penalty_contact_barrier || 0,
      penalty_small_fire: score.penalty_small_fire || 0,
      penalty_failed_drive_off: score.penalty_failed_drive_off || 0,
      penalty_large_fire: score.penalty_large_fire || 0,
      penalty_disqualified: score.penalty_disqualified || false
    });
  };

  const handleSendEmail = async () => {
    if (!emailAddress || !emailDialog) return;
    setSendingEmail(true);
    try {
      await axios.post(`${API}/admin/send-competitor-report`, {
        competitor_id: emailDialog.competitor_id,
        round_id: emailDialog.round_id,
        recipient_email: emailAddress
      }, getAuthHeaders());
      toast.success(`Email sent to ${emailAddress}`);
      setEmailDialog(null);
      setEmailAddress('');
      fetchScores();
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send email');
    } finally {
      setSendingEmail(false);
    }
  };

  const handleOpenBulkEmail = () => {
    // Initialize bulk email data from pending emails list and competitors
    const emailData = (pendingEmails?.competitors_list || []).map(p => {
      const comp = competitors?.find(c => c.id === p.competitor_id);
      return {
        competitor_id: p.competitor_id,
        competitor_name: p.competitor_name,
        car_number: p.car_number,
        round_name: p.round_name,
        email: comp?.email || '',
        selected: true
      };
    });
    setBulkEmailData(emailData);
    setBulkEmailDialog(true);
  };

  const handleSendBulkEmails = async () => {
    const selected = bulkEmailData.filter(d => d.selected && d.email);
    if (selected.length === 0) {
      toast.error('No valid emails selected');
      return;
    }

    setSendingBulk(true);
    try {
      const response = await axios.post(`${API}/admin/send-bulk-emails`, {
        competitor_emails: selected.map(s => ({
          competitor_id: s.competitor_id,
          recipient_email: s.email
        }))
      }, getAuthHeaders());
      
      toast.success(response.data.message);
      if (response.data.failed?.length > 0) {
        response.data.failed.forEach(f => {
          toast.error(`Failed: #${f.competitor_id} - ${f.error}`);
        });
      }
      setBulkEmailDialog(false);
      fetchScores();
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send bulk emails');
    } finally {
      setSendingBulk(false);
    }
  };

  const handleSaveEdit = async () => {
    try {
      await axios.put(`${API}/admin/scores/${editScore.id}`, editData, getAuthHeaders());
      toast.success('Score updated');
      setEditScore(null);
      fetchScores();
      onRefresh();
    } catch (error) {
      toast.error('Failed to update score');
    }
  };

  const sortedScores = [...scores].sort((a, b) => {
    if (sortBy === 'car_number') {
      return (parseInt(a.car_number) || 0) - (parseInt(b.car_number) || 0);
    } else if (sortBy === 'competitor_name') {
      return a.competitor_name.localeCompare(b.competitor_name);
    } else if (sortBy === 'judge_name') {
      return a.judge_name.localeCompare(b.judge_name);
    } else if (sortBy === 'final_score') {
      return b.final_score - a.final_score;
    }
    return 0;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <Label className="text-xs text-[#a1a1aa]">Filter by Round</Label>
          <Select value={filterRound} onValueChange={setFilterRound}>
            <SelectTrigger className="w-48 bg-[#18181b] border-[#27272a]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#18181b] border-[#27272a]">
              <SelectItem value="all">All Rounds</SelectItem>
              {rounds.map((r) => (
                <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs text-[#a1a1aa]">Filter by Judge</Label>
          <Select value={filterJudge} onValueChange={setFilterJudge}>
            <SelectTrigger className="w-48 bg-[#18181b] border-[#27272a]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#18181b] border-[#27272a]">
              <SelectItem value="all">All Judges</SelectItem>
              {judges.map((j) => (
                <SelectItem key={j.id} value={j.id}>{j.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs text-[#a1a1aa]">Sort by</Label>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-48 bg-[#18181b] border-[#27272a]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#18181b] border-[#27272a]">
              <SelectItem value="car_number">Car Number</SelectItem>
              <SelectItem value="competitor_name">Competitor Name</SelectItem>
              <SelectItem value="judge_name">Judge Name</SelectItem>
              <SelectItem value="final_score">Final Score</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <p className="text-sm text-[#a1a1aa]">{scores.length} scores found</p>
          <Button
            onClick={handleOpenBulkEmail}
            className="bg-[#3b82f6] hover:bg-[#2563eb] text-white"
            disabled={!pendingEmails?.competitors_list?.length}
          >
            <Send className="w-4 h-4 mr-2" />
            Bulk Email ({pendingEmails?.competitors_pending_email || 0})
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 bg-[#18181b] rounded border border-[#27272a]">
          <p className="text-[#a1a1aa]">Loading scores...</p>
        </div>
      ) : scores.length === 0 ? (
        <div className="text-center py-12 bg-[#18181b] rounded border border-[#27272a]">
          <ClipboardList className="w-12 h-12 text-[#a1a1aa] mx-auto mb-3" />
          <p className="text-[#a1a1aa]">No scores found with current filters.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {sortedScores.map((score) => (
            <div key={score.id} className={`bg-[#18181b] p-4 rounded border flex justify-between items-center ${score.email_sent ? 'border-[#27272a]' : 'border-[#f59e0b]/50'}`}>
              <div className="flex-1 grid grid-cols-2 md:grid-cols-5 gap-4">
                <div>
                  <p className="text-xs text-[#a1a1aa]">Competitor</p>
                  <p className="text-white font-semibold">
                    <span className="car-number-font text-[#f97316]">#{score.car_number}</span> {score.competitor_name}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-[#a1a1aa]">Round</p>
                  <p className="text-white">{score.round_name}</p>
                </div>
                <div>
                  <p className="text-xs text-[#a1a1aa]">Judge</p>
                  <p className="text-white">{score.judge_name}</p>
                </div>
                <div>
                  <p className="text-xs text-[#a1a1aa]">Final Score</p>
                  <p className={`font-bold data-font text-lg ${score.penalty_disqualified ? 'text-[#ef4444]' : 'text-[#22c55e]'}`}>
                    {score.penalty_disqualified ? '0 (DQ)' : score.final_score}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-[#a1a1aa]">Status</p>
                  <p className={`text-sm ${score.email_sent ? 'text-[#22c55e]' : 'text-[#f59e0b]'}`}>
                    {score.email_sent ? '✓ Emailed' : 'Not emailed'}
                  </p>
                </div>
              </div>
              <div className="flex gap-2 ml-4">
                {!score.email_sent && (
                  <Button
                    onClick={() => {
                      setEmailDialog({ competitor_id: score.competitor_id, round_id: score.round_id, competitor_name: score.competitor_name, car_number: score.car_number });
                      setEmailAddress('');
                    }}
                    variant="outline"
                    size="sm"
                    className="border-[#3b82f6] text-[#3b82f6] hover:bg-[#3b82f6] hover:text-white"
                  >
                    <Send className="w-3 h-3 mr-1" />
                    Email
                  </Button>
                )}
                <Button
                  onClick={() => handleEdit(score)}
                  variant="outline"
                  size="sm"
                  className="border-[#f97316] text-[#f97316] hover:bg-[#f97316] hover:text-white"
                >
                  Edit
                </Button>
                <Button
                  onClick={() => handleDelete(score.id)}
                  variant="destructive"
                  size="sm"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit Score Dialog */}
      <Dialog open={!!editScore} onOpenChange={() => setEditScore(null)}>
        <DialogContent className="bg-[#18181b] border-[#27272a] text-white max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="ui-font text-xl">
              Edit Score - #{editScore?.car_number} {editScore?.competitor_name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-[#a1a1aa]">
              Round: {editScore?.round_name} | Judge: {editScore?.judge_name}
            </p>
            
            {/* Scoring Categories */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs">Tip In (0-10)</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  max="10"
                  value={editData.tip_in}
                  onChange={(e) => setEditData({...editData, tip_in: parseFloat(e.target.value) || 0})}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div>
                <Label className="text-xs">Instant Smoke (0-10)</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  max="10"
                  value={editData.instant_smoke}
                  onChange={(e) => setEditData({...editData, instant_smoke: parseFloat(e.target.value) || 0})}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div>
                <Label className="text-xs">Constant Smoke (0-20)</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  max="20"
                  value={editData.constant_smoke}
                  onChange={(e) => setEditData({...editData, constant_smoke: parseFloat(e.target.value) || 0})}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div>
                <Label className="text-xs">Volume of Smoke (0-20)</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  max="20"
                  value={editData.volume_of_smoke}
                  onChange={(e) => setEditData({...editData, volume_of_smoke: parseFloat(e.target.value) || 0})}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div>
                <Label className="text-xs">Driving Skill (0-40)</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  max="40"
                  value={editData.driving_skill}
                  onChange={(e) => setEditData({...editData, driving_skill: parseFloat(e.target.value) || 0})}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div>
                <Label className="text-xs">Tyres Popped (0-2)</Label>
                <Input
                  type="number"
                  step="1"
                  min="0"
                  max="2"
                  value={editData.tyres_popped}
                  onChange={(e) => setEditData({...editData, tyres_popped: parseInt(e.target.value) || 0})}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
            </div>

            {/* Penalties */}
            <div className="border-t border-[#27272a] pt-4">
              <Label className="text-sm font-semibold text-[#ef4444] mb-2 block">Penalties</Label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs">Reversing (-5 each)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={editData.penalty_reversing}
                    onChange={(e) => setEditData({...editData, penalty_reversing: parseInt(e.target.value) || 0})}
                    className="bg-[#09090b] border-[#27272a]"
                  />
                </div>
                <div>
                  <Label className="text-xs">Stopping (-5 each)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={editData.penalty_stopping}
                    onChange={(e) => setEditData({...editData, penalty_stopping: parseInt(e.target.value) || 0})}
                    className="bg-[#09090b] border-[#27272a]"
                  />
                </div>
                <div>
                  <Label className="text-xs">Contact with Barrier (-5 each)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={editData.penalty_contact_barrier}
                    onChange={(e) => setEditData({...editData, penalty_contact_barrier: parseInt(e.target.value) || 0})}
                    className="bg-[#09090b] border-[#27272a]"
                  />
                </div>
                <div>
                  <Label className="text-xs">Small Fire (-5 each)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={editData.penalty_small_fire}
                    onChange={(e) => setEditData({...editData, penalty_small_fire: parseInt(e.target.value) || 0})}
                    className="bg-[#09090b] border-[#27272a]"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editData.penalty_failed_drive_off > 0}
                    onChange={(e) => setEditData({...editData, penalty_failed_drive_off: e.target.checked ? 1 : 0})}
                    className="w-4 h-4"
                  />
                  <Label className="text-xs">Failed to Drive Off (-10)</Label>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editData.penalty_large_fire > 0}
                    onChange={(e) => setEditData({...editData, penalty_large_fire: e.target.checked ? 1 : 0})}
                    className="w-4 h-4"
                  />
                  <Label className="text-xs">Large Fire (-10)</Label>
                </div>
              </div>
              
              {/* Disqualified */}
              <div className="mt-4 p-3 border border-[#ef4444] rounded bg-[#7f1d1d]/20">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={editData.penalty_disqualified}
                    onChange={(e) => setEditData({...editData, penalty_disqualified: e.target.checked})}
                    className="w-5 h-5"
                  />
                  <div>
                    <Label className="text-sm font-bold text-[#ef4444]">DISQUALIFIED</Label>
                    <p className="text-xs text-[#a1a1aa]">If checked, final score will be 0</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button variant="outline" onClick={() => setEditScore(null)} className="border-[#27272a]">
                Cancel
              </Button>
              <Button onClick={handleSaveEdit} className="btn-primary">
                Save Changes
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Send Email Dialog */}
      <Dialog open={!!emailDialog} onOpenChange={() => setEmailDialog(null)}>
        <DialogContent className="bg-[#18181b] border-[#27272a] text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="ui-font text-xl flex items-center gap-2">
              <Mail className="w-5 h-5 text-[#3b82f6]" />
              Send Score Report
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-[#09090b] p-3 rounded border border-[#27272a]">
              <p className="text-white font-semibold">
                <span className="car-number-font text-[#f97316]">#{emailDialog?.car_number}</span> {emailDialog?.competitor_name}
              </p>
              <p className="text-xs text-[#a1a1aa] mt-1">
                This will send a detailed score report including all rounds and scoring categories.
              </p>
            </div>
            
            <div>
              <Label className="text-sm">Recipient Email Address</Label>
              <Input
                type="email"
                value={emailAddress}
                onChange={(e) => setEmailAddress(e.target.value)}
                placeholder="competitor@email.com"
                className="bg-[#09090b] border-[#27272a] mt-1"
              />
            </div>
            
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setEmailDialog(null)} className="border-[#27272a]">
                Cancel
              </Button>
              <Button 
                onClick={handleSendEmail} 
                className="bg-[#3b82f6] hover:bg-[#2563eb] text-white"
                disabled={sendingEmail || !emailAddress}
              >
                {sendingEmail ? 'Sending...' : 'Send Email'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Bulk Email Dialog */}
      <Dialog open={bulkEmailDialog} onOpenChange={setBulkEmailDialog}>
        <DialogContent className="bg-[#18181b] border-[#27272a] text-white max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="ui-font text-xl flex items-center gap-2">
              <Send className="w-5 h-5 text-[#3b82f6]" />
              Bulk Email Score Reports
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto space-y-3 py-2">
            <p className="text-sm text-[#a1a1aa]">
              Enter email addresses for each competitor. Only selected competitors with valid emails will receive reports.
            </p>
            {bulkEmailData.map((item, idx) => (
              <div key={idx} className="bg-[#09090b] p-3 rounded border border-[#27272a] flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={item.selected}
                  onChange={(e) => {
                    const updated = [...bulkEmailData];
                    updated[idx].selected = e.target.checked;
                    setBulkEmailData(updated);
                  }}
                  className="w-5 h-5 flex-shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-white font-semibold truncate">
                    <span className="car-number-font text-[#f97316]">#{item.car_number}</span> {item.competitor_name}
                  </p>
                  <p className="text-xs text-[#a1a1aa]">{item.round_name}</p>
                </div>
                <Input
                  type="email"
                  value={item.email}
                  onChange={(e) => {
                    const updated = [...bulkEmailData];
                    updated[idx].email = e.target.value;
                    setBulkEmailData(updated);
                  }}
                  placeholder="email@example.com"
                  className="bg-[#18181b] border-[#27272a] w-56"
                />
              </div>
            ))}
          </div>
          <div className="flex justify-between items-center pt-4 border-t border-[#27272a]">
            <p className="text-sm text-[#a1a1aa]">
              {bulkEmailData.filter(d => d.selected && d.email).length} / {bulkEmailData.length} ready to send
            </p>
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setBulkEmailDialog(false)} className="border-[#27272a]">
                Cancel
              </Button>
              <Button 
                onClick={handleSendBulkEmails} 
                className="bg-[#3b82f6] hover:bg-[#2563eb] text-white"
                disabled={sendingBulk || bulkEmailData.filter(d => d.selected && d.email).length === 0}
              >
                {sendingBulk ? 'Sending...' : `Send ${bulkEmailData.filter(d => d.selected && d.email).length} Emails`}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}