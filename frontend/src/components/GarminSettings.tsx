import { useEffect, useState } from 'react';
import { api } from '../api/client';

export default function GarminSettings() {
  const [health, setHealth] = useState<{
    status: string;
    postgres: string;
    neo4j: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section style={cardStyle}>
      <h2 style={{ marginTop: 0, color: '#38bdf8' }}>⚙️ 시스템 상태</h2>
      {loading && <p>불러오는 중...</p>}
      {health && (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          <StatusRow label="전체 상태" value={health.status} ok={health.status === 'ok'} />
          <StatusRow label="PostgreSQL" value={health.postgres} ok={health.postgres === 'ok'} />
          <StatusRow label="Neo4j" value={health.neo4j} ok={health.neo4j === 'ok'} />
        </div>
      )}
      <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#0f172a', borderRadius: '8px' }}>
        <p style={{ margin: 0, fontSize: '0.875rem', color: '#94a3b8' }}>
          💡 <strong>가민 연동 설정</strong>은 <code>docker-compose.yml</code> 환경 변수(
          <code>GARMIN_EMAIL</code>, <code>GARMIN_PASSWORD</code>)로 관리됩니다.
          Worker가 30분마다 자동 동기화합니다.
        </p>
      </div>
    </section>
  );
}

function StatusRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <span style={{ color: '#cbd5e1' }}>{label}</span>
      <span
        style={{
          fontWeight: 700,
          color: ok ? '#4ade80' : '#f87171',
          background: ok ? '#14532d' : '#7f1d1d',
          padding: '0.25rem 0.75rem',
          borderRadius: '999px',
          fontSize: '0.875rem',
        }}
      >
        {value}
      </span>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '12px',
  padding: '1.5rem',
};
