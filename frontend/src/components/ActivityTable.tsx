import { useState, useEffect, useRef } from 'react';
import api from '../api/client';
import { ChevronLeft, ChevronRight, MoreHorizontal, Flag } from 'lucide-react';

interface Activity {
  activity_id: number;
  activity_type: string | null;
  activity_name: string | null;
  start_time: string | null;
  distance_meters: string | null;
  duration_sec: string | null;
  avg_hr: number | null;
  avg_pace: string | null;
  is_race: boolean;
  race_type: string | null;
  race_prep_weeks: number | null;
}

const RACE_OPTIONS = [
  { label: '10k', value: '10k' },
  { label: 'Half Marathon', value: 'half' },
  { label: 'Full Marathon', value: 'full' },
];

const PREP_WEEKS = [4, 8, 12, 16];

export default function ActivityTable() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(10);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState<number | null>(null);
  const [tagging, setTagging] = useState<number | null>(null);
  const [toast, setToast] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/activities?limit=${limit}&offset=${offset}`);
      setActivities(res.data.items);
      setTotal(res.data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [limit, offset]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const tagRace = async (activityId: number, raceType: string, prepWeeks: number) => {
    setTagging(activityId);
    try {
      await api.patch(`/activities/${activityId}`, {
        is_race: true,
        race_type: raceType,
        race_prep_weeks: prepWeeks,
      });
      setToast(`🏁 Tagged as ${raceType} (${prepWeeks}w prep). Graph update queued.`);
      await fetchData();
    } catch (err: any) {
      setToast(err.response?.data?.detail || 'Failed to tag race');
    } finally {
      setTagging(null);
      setMenuOpen(null);
      setTimeout(() => setToast(''), 3000);
    }
  };

  const removeRace = async (activityId: number) => {
    setTagging(activityId);
    try {
      await api.patch(`/activities/${activityId}`, {
        is_race: false,
        race_type: null,
      });
      setToast('Race tag removed.');
      await fetchData();
    } catch (err: any) {
      setToast(err.response?.data?.detail || 'Failed to remove race tag');
    } finally {
      setTagging(null);
      setMenuOpen(null);
      setTimeout(() => setToast(''), 3000);
    }
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
      {toast && (
        <div className="px-6 py-2 bg-emerald-900/50 border-b border-emerald-700 text-emerald-300 text-sm">
          {toast}
        </div>
      )}
      <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <h3 className="font-semibold text-slate-100">Recent Activities</h3>
        <span className="text-sm text-slate-400">
          {total} total · Page {currentPage} of {totalPages || 1}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-700/50 text-slate-300">
            <tr>
              <th className="px-6 py-3">Name</th>
              <th className="px-6 py-3">Type</th>
              <th className="px-6 py-3">Date</th>
              <th className="px-6 py-3">Distance</th>
              <th className="px-6 py-3">Duration</th>
              <th className="px-6 py-3">Avg HR</th>
              <th className="px-6 py-3">Pace</th>
              <th className="px-6 py-3 w-16"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {loading ? (
              <tr><td colSpan={8} className="px-6 py-8 text-center text-slate-400">Loading...</td></tr>
            ) : activities.length === 0 ? (
              <tr><td colSpan={8} className="px-6 py-8 text-center text-slate-400">No activities found</td></tr>
            ) : (
              activities.map((a) => (
                <tr
                  key={a.activity_id}
                  className={`hover:bg-slate-700/30 transition-colors ${
                    a.is_race ? 'border-l-4 border-l-rose-500' : ''
                  }`}
                >
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      {a.is_race && <Flag size={14} className="text-rose-400" />}
                      <span className="font-medium text-slate-100">{a.activity_name || '-'}</span>
                      {a.is_race && (
                        <span className="px-1.5 py-0.5 bg-rose-500/20 text-rose-300 rounded text-xs uppercase">
                          {a.race_type}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-3">
                    <span className="px-2 py-1 bg-slate-700 rounded text-xs capitalize">{a.activity_type || '-'}</span>
                  </td>
                  <td className="px-6 py-3 text-slate-400">
                    {a.start_time ? new Date(a.start_time).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-6 py-3">
                    {a.distance_meters ? `${(parseFloat(a.distance_meters) / 1000).toFixed(2)} km` : '-'}
                  </td>
                  <td className="px-6 py-3">
                    {a.duration_sec ? `${Math.floor(parseFloat(a.duration_sec) / 60)}m` : '-'}
                  </td>
                  <td className="px-6 py-3">{a.avg_hr ? `${a.avg_hr} bpm` : '-'}</td>
                  <td className="px-6 py-3 text-sky-400">{a.avg_pace || '-'}</td>
                  <td className="px-6 py-3 relative">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpen(menuOpen === a.activity_id ? null : a.activity_id);
                      }}
                      disabled={tagging === a.activity_id}
                      className="p-1.5 rounded hover:bg-slate-700 text-slate-400 transition-colors"
                    >
                      {tagging === a.activity_id ? (
                        <span className="text-xs">...</span>
                      ) : (
                        <MoreHorizontal size={16} />
                      )}
                    </button>

                    {menuOpen === a.activity_id && (
                      <div
                        ref={menuRef}
                        className="absolute right-4 top-10 z-20 w-56 bg-slate-700 border border-slate-600 rounded-lg shadow-xl overflow-hidden"
                      >
                        {a.is_race ? (
                          <button
                            onClick={() => removeRace(a.activity_id)}
                            className="w-full px-4 py-2.5 text-left text-sm text-rose-300 hover:bg-slate-600 transition-colors"
                          >
                            ❌ Remove Race
                          </button>
                        ) : (
                          <div className="py-1">
                            <div className="px-4 py-2 text-xs text-slate-400 font-medium border-b border-slate-600">
                              🏁 Mark as Race
                            </div>
                            <div className="grid grid-cols-2 gap-px bg-slate-600">
                              {RACE_OPTIONS.flatMap((opt) =>
                                PREP_WEEKS.map((w) => (
                                  <button
                                    key={`${opt.value}-${w}`}
                                    onClick={() => tagRace(a.activity_id, opt.value, w)}
                                    className="px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-600 transition-colors bg-slate-700"
                                  >
                                    <span className="font-medium">{opt.label}</span>
                                    <span className="text-slate-400 text-xs ml-1">{w}w</span>
                                  </button>
                                ))
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="px-6 py-4 border-t border-slate-700 flex items-center justify-between">
        <select
          value={limit}
          onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0); }}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-1 text-sm text-slate-100"
        >
          <option value={10}>10 / page</option>
          <option value={20}>20 / page</option>
          <option value={50}>50 / page</option>
        </select>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-40 transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= total}
            className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-40 transition-colors"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
