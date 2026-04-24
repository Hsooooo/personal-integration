import GraphViewer from '../components/GraphViewer';

export default function GraphPage() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Graph Explorer</h2>
        <p className="text-sm text-slate-400">Visualize your activity and health data as a graph</p>
      </div>
      <GraphViewer />
    </div>
  );
}
