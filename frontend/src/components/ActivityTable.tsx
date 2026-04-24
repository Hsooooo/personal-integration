import { useState, useEffect } from 'react';
import api from '../api/client';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Activity {
  activity_id: number;
  activity_type: string | null;
  activity_name: string | null;
  start_time: string | null;
  distance_meters: string | null;
  duration_sec: string | null;
  avg_hr: number | null;
  avg_pace: string | null;
}

export default function ActivityTable() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(10);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);

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

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
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
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {loading ? (
              <tr><td colSpan={7} className="px-6 py-8 text-center text-slate-400">Loading...</td></tr>
            ) : activities.length === 0 ? (
              <tr><td colSpan={7} className="px-6 py-8 text-center text-slate-400">No activities found</td></tr>
            ) : (
              activities.map((a) => (
                <tr key={a.activity_id} className="hover:bg-slate-700/30 transition-colors">
                  <td className="px-6 py-3 font-medium text-slate-100">{a.activity_name || '-'}</td>
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
