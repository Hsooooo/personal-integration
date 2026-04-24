import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import { Save, RefreshCw, Activity, ShieldCheck } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  const [garminEmail, setGarminEmail] = useState('');
  const [garminPassword, setGarminPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [syncStatus, setSyncStatus] = useState<{ pending_jobs: number; user_garmin_configured: boolean } | null>(null);

  useEffect(() => {
    if (user?.garmin_email) {
      setGarminEmail(user.garmin_email);
    }
    fetchStatus();
  }, [user]);

  const fetchStatus = async () => {
    try {
      const res = await api.get('/garmin/status');
      setSyncStatus(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveMsg('');
    try {
      await api.patch('/users/me', {
        garmin_email: garminEmail || null,
        garmin_password: garminPassword || null,
      });
      setSaveMsg('Credentials saved successfully');
      setGarminPassword('');
      fetchStatus();
    } catch (err: any) {
      setSaveMsg(err.response?.data?.detail || 'Failed to save credentials');
    } finally {
      setSaving(false);
    }
  };

  const handleFullSync = async () => {
    setSyncing(true);
    setSyncMsg('');
    try {
      const res = await api.post('/garmin/sync?sync_type=full');
      setSyncMsg(`Full sync queued: ${res.data.message_id}`);
      fetchStatus();
    } catch (err: any) {
      setSyncMsg(err.response?.data?.detail || 'Failed to trigger full sync');
    } finally {
      setSyncing(false);
    }
  };

  const handleGraphSync = async () => {
    setSyncing(true);
    setSyncMsg('');
    try {
      const res = await api.post('/activities/sync');
      setSyncMsg(`Graph sync completed: ${res.data.activities_synced} activities, ${res.data.health_synced} health records`);
      fetchStatus();
    } catch (err: any) {
      setSyncMsg(err.response?.data?.detail || 'Failed to trigger graph sync');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Settings</h2>
        <p className="text-sm text-slate-400">Manage your Garmin credentials and sync preferences</p>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <Activity size={18} className="text-sky-400" />
          <h3 className="font-semibold text-slate-100">Garmin Connect</h3>
        </div>

        <form onSubmit={handleSaveCredentials} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Garmin Email</label>
            <input
              type="email"
              value={garminEmail}
              onChange={(e) => setGarminEmail(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
              placeholder="your@email.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Garmin Password</label>
            <input
              type="password"
              value={garminPassword}
              onChange={(e) => setGarminPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
              placeholder="Leave blank to keep current"
            />
            <p className="text-xs text-slate-500 mt-1">Stored encrypted with Fernet (AES-128)</p>
          </div>
          {saveMsg && (
            <div className={`p-3 rounded-lg text-sm ${saveMsg.includes('success') ? 'bg-green-900/50 text-green-300 border border-green-700' : 'bg-red-900/50 text-red-300 border border-red-700'}`}>
              {saveMsg}
            </div>
          )}
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-400 text-slate-900 font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            <Save size={16} />
            {saving ? 'Saving...' : 'Save Credentials'}
          </button>
        </form>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <RefreshCw size={18} className="text-sky-400" />
          <h3 className="font-semibold text-slate-100">Manual Sync</h3>
        </div>
        <p className="text-sm text-slate-400">
          Trigger a full Garmin sync (all activities + 30 days health). The job is queued via Redis Stream and processed by the worker.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleFullSync}
            disabled={syncing || !syncStatus?.user_garmin_configured}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Queueing...' : 'Full Garmin Sync'}
          </button>
          <button
            onClick={handleGraphSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-400 text-slate-900 font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Syncing...' : 'Graph Sync Only'}
          </button>
          {syncStatus && (
            <span className="text-sm text-slate-400">
              Pending jobs: {syncStatus.pending_jobs}
            </span>
          )}
        </div>
        {syncMsg && (
          <div className={`p-3 rounded-lg text-sm ${syncMsg.includes('queued') ? 'bg-green-900/50 text-green-300 border border-green-700' : 'bg-red-900/50 text-red-300 border border-red-700'}`}>
            {syncMsg}
          </div>
        )}
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <ShieldCheck size={18} className="text-sky-400" />
          <h3 className="font-semibold text-slate-100">Security</h3>
        </div>
        <div className="text-sm text-slate-400 space-y-2">
          <p>• Your Garmin password is encrypted before storage using Fernet symmetric encryption.</p>
          <p>• The encryption key is derived from the application secret key.</p>
          <p>• Only the worker process can decrypt and use your credentials to connect to Garmin.</p>
        </div>
      </div>
    </div>
  );
}
