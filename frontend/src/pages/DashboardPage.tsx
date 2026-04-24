import { useState, useEffect } from 'react';
import api from '../api/client';
import ActivityTable from '../components/ActivityTable';
import { RefreshCw, TrendingUp, Activity, Timer, Heart } from 'lucide-react';

interface WeeklyStat {
  week: string;
  total_km: number;
  runs: number;
  avg_hr: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<WeeklyStat | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      const res = await api.get('/activities/stats/weekly');
      const data = res.data as WeeklyStat[];
      setStats(data[0] || null);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.post('/activities/sync');
      setLastSync(new Date().toLocaleTimeString());
      await fetchStats();
    } catch (e) {
      console.error(e);
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const statCards = [
    { label: 'Week', value: stats?.week ?? '-', icon: Activity, suffix: '' },
    { label: 'Runs', value: stats?.runs ?? 0, icon: TrendingUp, suffix: '' },
    { label: 'Distance', value: stats?.total_km.toFixed(1) ?? '0.0', icon: Timer, suffix: ' km' },
    { label: 'Avg HR', value: stats?.avg_hr ?? 0, icon: Heart, suffix: ' bpm' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Dashboard</h2>
          <p className="text-sm text-slate-400">Weekly overview</p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-400 text-slate-900 font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
      </div>
      {lastSync && (
        <p className="text-xs text-slate-500">Last sync: {lastSync}</p>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="bg-slate-800 border border-slate-700 rounded-xl p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-sky-500/20 rounded-lg">
                  <Icon size={18} className="text-sky-400" />
                </div>
                <span className="text-sm text-slate-400">{card.label}</span>
              </div>
              <p className="text-2xl font-bold text-slate-100">
                {card.value}{card.suffix}
              </p>
            </div>
          );
        })}
      </div>
      <ActivityTable />
    </div>
  );
}
