const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetchJson<{
    status: string;
    postgres: string;
    neo4j: string;
  }>('/health'),

  activities: (limit = 50) =>
    fetchJson<Array<Record<string, unknown>>>(`/api/activities?limit=${limit}`),

  healthDaily: (limit = 30) =>
    fetchJson<Array<Record<string, unknown>>>(`/api/activities/health?limit=${limit}`),

  syncGraph: () =>
    fetchJson<{ synced_activities: number; synced_health: number }>('/api/graph/sync', {
      method: 'POST',
    }),

  graphData: (limit = 100) =>
    fetchJson<{ nodes: Array<Record<string, unknown>>; edges: Array<Record<string, unknown>> }>(
      `/api/graph/data?limit=${limit}`
    ),

  garminStatus: () =>
    fetchJson<{ status: string; interval_min: number }>('/api/garmin/status'),
};
