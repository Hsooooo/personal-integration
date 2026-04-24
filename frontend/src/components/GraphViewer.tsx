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

    api.get('/graph/data?limit=200')
      .then((res) => {
        const data = res.data;
        const elements: cytoscape.ElementDefinition[] = [];

        data.nodes.forEach((n: any) => {
          const label =
            n.properties?.name ||
            n.properties?.id ||
            n.properties?.date ||
            n.labels?.[0] ||
            'Node';
          elements.push({
            data: {
              id: n.id,
              label: String(label),
              type: n.labels?.[0] || 'Node',
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
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-sky-400">📊 Graph Viewer</h2>
        {loading && <span className="text-sm text-slate-400">Loading...</span>}
      </div>
      {error && (
        <div className="p-4 bg-red-900/50 border border-red-700 rounded-lg mb-4">
          <p className="text-red-300 text-sm">❌ {error}</p>
        </div>
      )}
      <div
        ref={containerRef}
        className="w-full h-[600px] bg-slate-950 rounded-lg border border-slate-700"
      />
    </div>
  );
}
