import { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { api } from '../api/client';

export default function GraphViewer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    api.graphData(200)
      .then((data) => {
        const elements: cytoscape.ElementDefinition[] = [];

        data.nodes.forEach((n: any) => {
          const label =
            n.properties.name ||
            n.properties.id ||
            n.properties.date ||
            n.labels[0];
          elements.push({
            data: {
              id: n.id,
              label: String(label),
              type: n.labels[0],
              ...n.properties,
            },
          });
        });

        data.edges.forEach((e: any) => {
          elements.push({
            data: {
              id: `${e.source}-${e.target}-${e.type}`,
              source: e.source,
              target: e.target,
              label: e.type,
            },
          });
        });

        const cy = cytoscape({
          container: containerRef.current,
          elements,
          style: [
            {
              selector: 'node',
              style: {
                'background-color': '#38bdf8',
                'label': 'data(label)',
                'color': '#e2e8f0',
                'font-size': '10px',
                'text-valign': 'center',
                'text-halign': 'center',
                'width': '40px',
                'height': '40px',
                'border-width': 2,
                'border-color': '#0ea5e9',
              },
            },
            {
              selector: 'node[type="Activity"]',
              style: {
                'background-color': '#f472b6',
                'border-color': '#db2777',
              },
            },
            {
              selector: 'node[type="DailyHealth"]',
              style: {
                'background-color': '#a78bfa',
                'border-color': '#7c3aed',
              },
            },
            {
              selector: 'edge',
              style: {
                'width': 2,
                'line-color': '#475569',
                'target-arrow-color': '#475569',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'label': 'data(label)',
                'font-size': '8px',
                'color': '#94a3b8',
              },
            },
          ],
          layout: {
            name: 'cose',
            padding: 20,
            nodeRepulsion: 400000,
            idealEdgeLength: 100,
            gravity: 0.5,
          } as any,
        });

        cyRef.current = cy;
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
      });

    return () => {
      cyRef.current?.destroy();
    };
  }, []);

  return (
    <section style={cardStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0, color: '#38bdf8' }}>📊 그래프 뷰어</h2>
        {loading && <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>불러오는 중...</span>}
      </div>
      {error && (
        <div style={{ padding: '1rem', background: '#7f1d1d', borderRadius: '8px', marginBottom: '1rem' }}>
          <p style={{ margin: 0, color: '#fca5a5' }}>❌ {error}</p>
        </div>
      )}
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: '600px',
          background: '#0f172a',
          borderRadius: '8px',
          border: '1px solid #334155',
        }}
      />
    </section>
  );
}

const cardStyle: React.CSSProperties = {
  background: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '12px',
  padding: '1.5rem',
};
