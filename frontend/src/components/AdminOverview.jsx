import React, { useState, useEffect } from 'react';
import { Users, FileText, AlertTriangle, Activity, RefreshCw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const AdminOverview = () => {
  // Setup state to hold the real data from MySQL, including an empty chart by default
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalDocuments: 0,
    avgRiskScore: '0/100',
    activeSessions: 0,
    weeklyData: [
      { name: 'Mon', docs: 0 }, { name: 'Tue', docs: 0 }, { name: 'Wed', docs: 0 },
      { name: 'Thu', docs: 0 }, { name: 'Fri', docs: 0 }, { name: 'Sat', docs: 0 }, { name: 'Sun', docs: 0 }
    ]
  });
  const [refreshing, setRefreshing] = useState(false);

  // Fetch real stats and chart data from the Python backend
  const fetchStats = async () => {
    try {
      setRefreshing(true);
      const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
      const response = await axios.get(`${API_URL}/api/admin/stats`);
      setStats(response.data);
      console.log("Admin stats refreshed:", response.data);
    } catch (error) {
      console.error("Error fetching stats:", error);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in text-gray-800">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin Overview</h1>
          <p className="text-gray-500 mt-1">Platform-wide statistics and weekly activity.</p>
        </div>
        <button
          onClick={fetchStats}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-all"
        >
          <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Top Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Total Users</p>
            <p className="text-3xl font-black text-slate-800">{stats.totalUsers}</p>
            <p className="text-xs text-gray-500 mt-2">Registered accounts</p>
          </div>
          <div className="p-3 rounded-lg bg-blue-50 text-blue-500"><Users className="w-6 h-6" /></div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Total Documents</p>
            <p className="text-3xl font-black text-slate-800">{stats.totalDocuments}</p>
            <p className="text-xs text-gray-500 mt-2">Analyzed files</p>
          </div>
          <div className="p-3 rounded-lg bg-green-50 text-green-500"><FileText className="w-6 h-6" /></div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Avg Risk Score</p>
            <p className="text-3xl font-black text-slate-800">{stats.avgRiskScore}</p>
            <p className="text-xs text-gray-500 mt-2">Platform average</p>
          </div>
          <div className="p-3 rounded-lg bg-yellow-50 text-yellow-500"><AlertTriangle className="w-6 h-6" /></div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Active Sessions</p>
            <p className="text-3xl font-black text-slate-800">{stats.activeSessions}</p>
            <p className="text-xs text-gray-500 mt-2">Online now</p>
          </div>
          <div className="p-3 rounded-lg bg-cyan-50 text-cyan-500"><Activity className="w-6 h-6" /></div>
        </div>
      </div>

      {/* Bar Chart Section - NOW DYNAMIC */}
      <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm">
        <h2 className="text-lg font-bold mb-6 text-slate-800">Documents Analyzed This Week</h2>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats.weeklyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} dy={10} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} allowDecimals={false} />
              <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
              <Bar dataKey="docs" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={50} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
};

export default AdminOverview;