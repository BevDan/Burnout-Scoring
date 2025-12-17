import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { LogOut, Users, Trophy, Calendar, Flag, Upload, Download, Settings } from 'lucide-react';
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
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileData, setProfileData] = useState({ name: '', password: '' });

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [judgesRes, classesRes, competitorsRes, roundsRes] = await Promise.all([
        axios.get(`${API}/admin/judges`, getAuthHeaders()),
        axios.get(`${API}/admin/classes`, getAuthHeaders()),
        axios.get(`${API}/admin/competitors`, getAuthHeaders()),
        axios.get(`${API}/admin/rounds`, getAuthHeaders())
      ]);
      setJudges(judgesRes.data);
      setClasses(classesRes.data);
      setCompetitors(competitorsRes.data);
      setRounds(roundsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
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

      <main className="max-w-7xl mx-auto px-6 py-8">
        <Tabs defaultValue="judges" className="space-y-6">
          <TabsList className="bg-[#18181b] border border-[#27272a] p-1">
            <TabsTrigger value="judges" className="data-[state=active]:bg-[#f97316]">Judges</TabsTrigger>
            <TabsTrigger value="classes" className="data-[state=active]:bg-[#f97316]">Classes</TabsTrigger>
            <TabsTrigger value="competitors" className="data-[state=active]:bg-[#f97316]">Competitors</TabsTrigger>
            <TabsTrigger value="rounds" className="data-[state=active]:bg-[#f97316]">Rounds</TabsTrigger>
          </TabsList>

          <TabsContent value="judges">
            <JudgesPanel judges={judges} onRefresh={fetchAllData} />
          </TabsContent>

          <TabsContent value="classes">
            <ClassesPanel classes={classes} onRefresh={fetchAllData} />
          </TabsContent>

          <TabsContent value="competitors">
            <CompetitorsPanel competitors={competitors} classes={classes} onRefresh={fetchAllData} />
          </TabsContent>

          <TabsContent value="rounds">
            <RoundsPanel rounds={rounds} onRefresh={fetchAllData} />
          </TabsContent>
        </Tabs>
      </main>

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

  return (
    <div className="glass-panel p-6 rounded-lg border border-[#27272a]">
      <div className="flex justify-between items-center mb-6">
        <h2 className="ui-font text-2xl font-bold tracking-wide text-white">JUDGES</h2>
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
        {judges.map((judge) => (
          <div key={judge.id} className="bg-[#18181b] p-4 rounded border border-[#27272a] flex justify-between items-center">
            <div>
              <p className="ui-font text-lg font-semibold text-white">{judge.name}</p>
              <p className="data-font text-sm text-[#a1a1aa]">{judge.username}</p>
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
        ))}
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
  const [csvData, setCsvData] = useState('');
  const [formData, setFormData] = useState({ name: '', car_number: '', vehicle_info: '', plate: '', class_id: '' });

  const handleCreate = async () => {
    try {
      await axios.post(`${API}/admin/competitors`, formData, getAuthHeaders());
      toast.success('Competitor created successfully');
      setOpen(false);
      setFormData({ name: '', car_number: '', vehicle_info: '', plate: '', class_id: '' });
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
                  <Label>CSV Format: name,car_number,vehicle_info,plate,class_id</Label>
                  <textarea
                    value={csvData}
                    onChange={(e) => setCsvData(e.target.value)}
                    className="w-full h-48 p-3 bg-[#09090b] border border-[#27272a] rounded text-white data-font text-sm"
                    placeholder="name,car_number,vehicle_info,plate,class_id&#10;John Doe,42,Ford Mustang,BURNOUT1,class-id-here&#10;Jane Smith,88,Chevy Camaro,SMOKEY,class-id-here"
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
            <Button
              onClick={() => handleDelete(comp.id)}
              variant="destructive"
              size="sm"
              data-testid={`delete-competitor-${comp.id}`}
            >
              Delete
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

function RoundsPanel({ rounds, onRefresh }) {
  const [open, setOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingRound, setEditingRound] = useState(null);
  const [formData, setFormData] = useState({ name: '', date: '', status: 'active' });

  const handleCreate = async () => {
    try {
      await axios.post(`${API}/admin/rounds`, formData, getAuthHeaders());
      toast.success('Round created successfully');
      setOpen(false);
      setFormData({ name: '', date: '', status: 'active' });
      onRefresh();
    } catch (error) {
      toast.error('Failed to create round');
    }
  };

  const startEdit = (round) => {
    setEditingRound(round);
    setFormData({ name: round.name, date: round.date, status: round.status });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    try {
      await axios.put(`${API}/admin/rounds/${editingRound.id}`, formData, getAuthHeaders());
      toast.success('Round updated successfully');
      setEditOpen(false);
      setEditingRound(null);
      setFormData({ name: '', date: '', status: 'active' });
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
              <div>
                <Label>Date</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                  data-testid="round-date-input"
                />
              </div>
              <div>
                <Label>Status</Label>
                <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value })}>
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
              <div>
                <Label>Date</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="bg-[#09090b] border-[#27272a]"
                />
              </div>
              <div>
                <Label>Status</Label>
                <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value })}>
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
                <p className="text-sm text-[#a1a1aa]">{round.date}</p>
                <span className={`inline-block mt-2 px-3 py-1 rounded text-xs font-bold ${
                  round.status === 'active' ? 'bg-[#22c55e] text-black' : 'bg-[#71717a] text-white'
                }`}>
                  {(round.status || 'active').toUpperCase()}
                </span>
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