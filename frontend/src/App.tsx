import { useState } from 'react';
import GarminSettings from './components/GarminSettings';
import SyncButton from './components/SyncButton';
import GraphViewer from './components/GraphViewer';

function App() {
  const [activeTab, setActiveTab] = useState<'settings' | 'graph'>('settings');

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{
        padding: '1rem 2rem',
        borderBottom: '1px solid #334155',
        background: '#1e293b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <h1 style={{ margin: 0, fontSize: '1.25rem', color: '#38bdf8' }}>
          🏃 Personal Integration
        </h1>
        <nav style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={() => setActiveTab('settings')}
            style={{
              background: activeTab === 'settings' ? '#38bdf8' : 'transparent',
              color: activeTab === 'settings' ? '#0f172a' : '#94a3b8',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            ⚙️ 가민 설정
          </button>
          <button
            onClick={() => setActiveTab('graph')}
            style={{
              background: activeTab === 'graph' ? '#38bdf8' : 'transparent',
              color: activeTab === 'graph' ? '#0f172a' : '#94a3b8',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            📊 그래프 보기
          </button>
        </nav>
      </header>

      <main style={{ flex: 1, padding: '2rem', maxWidth: '1200px', width: '100%', margin: '0 auto' }}>
        {activeTab === 'settings' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <GarminSettings />
            <SyncButton />
          </div>
        )}
        {activeTab === 'graph' && <GraphViewer />}
      </main>
    </div>
  );
}

export default App;
