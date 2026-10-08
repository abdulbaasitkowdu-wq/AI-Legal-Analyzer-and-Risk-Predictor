// frontend/src/components/Dashboard.jsx
import React, { useEffect, useState, useCallback } from 'react';
import { FileText, AlertTriangle, TrendingUp, Calendar, UploadCloud, User } from 'lucide-react';
import { useUser } from '../context/UserContext';
import { Link } from 'react-router-dom';
import axios from 'axios';
import DocumentAnalysisModal from './DocumentAnalysisModal';

const API = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

function riskToColor(level) {
  if (level === 'High') return 'text-red-600 bg-red-50 border-red-100';
  if (level === 'Medium') return 'text-yellow-700 bg-yellow-50 border-yellow-100';
  return 'text-green-600 bg-green-50 border-green-100';
}

const Dashboard = () => {
  const { user } = useUser();
  const userId = user?.currentUser?.id;

  const [loading, setLoading] = useState(true);
  const [docs, setDocs] = useState([]);
  const [stats, setStats] = useState({
    docsAnalyzed: 0,
    avgRiskScore: 'N/A',
    clausesDetected: 0,
    upcomingDeadlines: 0,
  });
  const [selected, setSelected] = useState(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/api/documents/my`, {
        params: { user_id: userId },
      });
      const list = data.documents || [];
      setDocs(list);

      const scores = list
        .map((d) => d.result?.analysis?.risk_score ?? d.snapshot?.analysis?.risk_score)
        .filter((x) => typeof x === 'number');
      const avgRiskScore = scores.length
        ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
        : 'N/A';
      const clausesDetected = list.reduce((s, d) => s + (d.clauses_detected || 0), 0);

      setStats({
        docsAnalyzed: list.length,
        avgRiskScore,
        clausesDetected,
        upcomingDeadlines: 0,
      });
    } catch (e) {
      console.error('Failed to load documents', e);
      setDocs([]);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const dynamicStats = [
    { title: 'DOCUMENTS ANALYZED', value: stats.docsAnalyzed, icon: FileText, iconColor: 'text-blue-500', bgColor: 'bg-blue-50' },
    { title: 'AVG RISK SCORE', value: stats.avgRiskScore, icon: AlertTriangle, iconColor: 'text-yellow-500', bgColor: 'bg-yellow-50' },
    { title: 'CLAUSES DETECTED', value: stats.clausesDetected, icon: TrendingUp, iconColor: 'text-green-500', bgColor: 'bg-green-50' },
    { title: 'UPCOMING DEADLINES', value: stats.upcomingDeadlines, icon: Calendar, iconColor: 'text-blue-500', bgColor: 'bg-blue-50' },
  ];

  const recentActivity = docs.map((d) => ({
    id: d.id,
    name: d.filename,
    date: d.uploaded_at
      ? new Date(d.uploaded_at).toLocaleString()
      : '',
    risk: d.risk_level,
    riskColor: riskToColor(d.risk_level),
    result: d.result ?? d.snapshot,
    snapshot: d.snapshot,
  }));

  const openDetail = (row) => {
    setSelected(row);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in text-gray-800">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Document Analysis Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of your document analysis activity and quick actions.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {dynamicStats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-gray-500 tracking-wider mb-2">{stat.title}</p>
                <p className="text-3xl font-black text-slate-800">{stat.value}</p>
              </div>
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <Icon className={`w-6 h-6 ${stat.iconColor}`} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm">
        <h2 className="text-lg font-bold mb-4 text-slate-800">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/upload" className="flex flex-col items-center justify-center p-6 border border-gray-200 rounded-xl hover:bg-blue-50 hover:border-blue-200 transition-colors group">
            <UploadCloud className="w-6 h-6 text-blue-500 mb-2 group-hover:scale-110 transition-transform" />
            <span className="font-medium">Upload & Scan</span>
          </Link>
          <Link to="/calendar" className="flex flex-col items-center justify-center p-6 border border-gray-200 rounded-xl hover:bg-blue-50 hover:border-blue-200 transition-colors group">
            <Calendar className="w-6 h-6 text-blue-500 mb-2 group-hover:scale-110 transition-transform" />
            <span className="font-medium">View Deadlines</span>
          </Link>
          <Link to="/profile" className="flex flex-col items-center justify-center p-6 border border-gray-200 rounded-xl hover:bg-blue-50 hover:border-blue-200 transition-colors group">
            <User className="w-6 h-6 text-green-500 mb-2 group-hover:scale-110 transition-transform" />
            <span className="font-medium">My Profile</span>
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <h2 className="text-lg font-bold text-slate-800">Recent analyses</h2>
          <button
            type="button"
            onClick={() => loadDocuments()}
            className="text-blue-600 text-sm font-medium hover:text-blue-800"
          >
            Refresh
          </button>
        </div>
        <div className="divide-y divide-gray-100">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading…</div>
          ) : recentActivity.length > 0 ? (
            recentActivity.map((doc) => (
              <div
                key={doc.id}
                className="w-full p-4 px-6 flex items-center justify-between gap-3 hover:bg-gray-50 transition-colors"
              >
                <button
                  type="button"
                  onClick={() => openDetail(doc)}
                  className="flex-1 min-w-0 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="p-2 bg-gray-100 rounded-lg text-gray-500 shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-800 truncate">{doc.name}</p>
                      <p className="text-sm text-gray-500">{doc.date}</p>
                    </div>
                  </div>
                  <span className={`shrink-0 px-3 py-1 text-xs font-bold border rounded-full ${doc.riskColor}`}>
                    {doc.risk}
                  </span>
                </button>
                <Link
                  to={`/assistant?documentId=${doc.id}`}
                  className="shrink-0 text-xs font-semibold text-blue-600 hover:text-blue-800 whitespace-nowrap"
                >
                  Chat with AI
                </Link>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-gray-500 flex flex-col items-center justify-center gap-2">
              <FileText className="w-10 h-10 text-gray-300" />
              <p>No documents analyzed yet.</p>
              <Link to="/upload" className="text-blue-500 text-sm hover:underline">
                Upload your first document
              </Link>
            </div>
          )}
        </div>
      </div>

      <DocumentAnalysisModal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.name}
        subtitle={selected?.date}
        result={selected?.result}
        snapshot={selected?.snapshot}
      />
    </div>
  );
};

export default Dashboard;
