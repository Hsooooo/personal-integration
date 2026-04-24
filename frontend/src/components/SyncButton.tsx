import { useState } from 'react';
import { api } from '../api/client';

export default function SyncButton() {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<{
    synced_activities: number;
    synced_health: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSync = async () => {
    setSyncing(true);
    setResult(null);
    setError(null);
    try {
      const res = await api.syncGraph();
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <section style={cardStyle}>
      <h2 style={{ marginTop: 0, color: '#38bdf8' }}>🔄 동기화</h2>
      <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
        PostgreSQL에 저장된 데이터를 Neo4j 그래프로 동기화합니다.
        Worker가 주기적으로 실행하지만, 수동으로도 트리거할 수 있습니다.
      </p>
      <button
        onClick={handleSync}
        disabled={syncing}
        style={{
          marginTop: '1rem',
          padding: '0.75rem 1.5rem',
          background: syncing ? '#475569' : '#38bdf8',
          color: '#0f172a',
          border: 'none',
          borderRadius: '8px',
          fontWeight: 700,
          cursor: syncing ? 'not-allowed' : 'pointer',
          fontSize: '1rem',
        }}
      >
        {syncing ? '동기화 중...' : '🚀 지금 동기화'}
      </button>

      {result && (
        <div style={{ marginTop: '1rem', padding: '1rem', background: '#14532d', borderRadius: '8px' }}>
          <p style={{ margin: 0, color: '#4ade80', fontWeight: 600 }}>
            ✅ 동기화 완료!
          </p>
          <p style={{ margin: '0.5rem 0 0', color: '#bbf7d0', fontSize: '0.875rem' }}>
            Activities: {result.synced_activities}건, Health: {result.synced_health}건
          </p>
        </div>
      )}

      {error && (
        <div style={{ marginTop: '1rem', padding: '1rem', background: '#7f1d1d', borderRadius: '8px' }}>
          <p style={{ margin: 0, color: '#fca5a5', fontWeight: 600 }}>❌ 오류</p>
          <p style={{ margin: '0.5rem 0 0', color: '#fecaca', fontSize: '0.875rem' }}>{error}</p>
        </div>
      )}
    </section>
  );
}

const cardStyle: React.CSSProperties = {
  background: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '12px',
  padding: '1.5rem',
};
