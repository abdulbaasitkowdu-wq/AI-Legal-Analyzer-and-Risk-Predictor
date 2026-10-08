import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Search, MoreHorizontal, Trash2, Shield, History, X } from 'lucide-react';
import axios from 'axios';
import { useUser } from '../context/UserContext.jsx';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const UserManagement = () => {
  const { user } = useUser();
  const currentUserId = user?.currentUser?.id;
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);

  const [activityModal, setActivityModal] = useState(null);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityData, setActivityData] = useState(null);

  const fetchUsers = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/users`);
      setUsers(response.data.users || []);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  useEffect(() => {
    if (openMenuId === null) return;
    const onDoc = (e) => {
      const el = document.querySelector(`[data-user-menu="${openMenuId}"]`);
      if (el && !el.contains(e.target)) {
        setOpenMenuId(null);
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [openMenuId]);

  const filteredUsers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        (u.name || '').toLowerCase().includes(q) ||
        (u.email || '').toLowerCase().includes(q) ||
        (u.role || '').toLowerCase().includes(q)
    );
  }, [users, query]);

  const closeMenu = () => setOpenMenuId(null);

  const handleDelete = async (u) => {
    closeMenu();
    if (currentUserId != null && u.id === currentUserId) {
      alert('You cannot delete your own account from this list.');
      return;
    }
    const ok = window.confirm(
      `Delete user "${u.name}" (${u.email})? This removes their documents, events, and chat data. This cannot be undone.`
    );
    if (!ok) return;
    setBusyId(u.id);
    try {
      await axios.delete(`${API_URL}/api/admin/users/${u.id}`);
      await fetchUsers();
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Could not delete user');
    } finally {
      setBusyId(null);
    }
  };

  const handlePromoteAdmin = async (u) => {
    closeMenu();
    setBusyId(u.id);
    try {
      await axios.patch(`${API_URL}/api/admin/users/${u.id}`, { role: 'Admin' });
      await fetchUsers();
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Could not update role');
    } finally {
      setBusyId(null);
    }
  };

  const openActivity = async (u) => {
    closeMenu();
    setActivityModal(u.id);
    setActivityData(null);
    setActivityLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/admin/users/${u.id}/activity`);
      setActivityData(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Could not load activity');
      setActivityModal(null);
    } finally {
      setActivityLoading(false);
    }
  };

  const closeActivityModal = () => {
    setActivityModal(null);
    setActivityData(null);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in text-gray-800">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
        <p className="text-gray-500 mt-1">View and manage all registered users on the platform.</p>
      </div>

      <div className="flex items-center gap-4 py-2">
        <div className="relative flex-1 max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="block w-full pl-10 pr-3 py-2 border border-gray-200 rounded-lg text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Search users..."
          />
        </div>
        <div className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm font-medium">
          {filteredUsers.length} users
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                <th className="px-6 py-4">User</th>
                <th className="px-6 py-4">Role</th>
                <th className="px-6 py-4">Documents</th>
                <th className="px-6 py-4">Last Active</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan="6" className="text-center py-8 text-gray-500">
                    Loading user data...
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => {
                  const isBusy = busyId === u.id;
                  const isSelf = currentUserId != null && u.id === currentUserId;
                  const isAdminRole = u.role && u.role.includes('Admin');
                  const isStandardUser = u.role === 'User';
                  return (
                    <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm shrink-0 ${
                              isAdminRole ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'
                            }`}
                          >
                            {u.initials}
                          </div>
                          <div>
                            <p className="font-bold text-slate-800">{u.name}</p>
                            <p className="text-xs text-gray-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-xs font-semibold">
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-600 font-medium">{u.docs}</td>
                      <td className="px-6 py-4 text-slate-500 text-sm">{u.last_active}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-bold border ${
                            u.status === 'Active'
                              ? 'text-green-600 bg-green-50 border-green-200'
                              : 'text-amber-700 bg-amber-50 border-amber-200'
                          }`}
                        >
                          {u.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div
                          className="relative inline-flex justify-center"
                          data-user-menu={u.id}
                        >
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() => setOpenMenuId(openMenuId === u.id ? null : u.id)}
                            className="text-gray-400 hover:text-slate-700 p-2 rounded-full hover:bg-gray-100 transition-colors disabled:opacity-50"
                            aria-expanded={openMenuId === u.id}
                            aria-haspopup="true"
                            aria-label="Open actions menu"
                          >
                            <MoreHorizontal className="w-5 h-5" />
                          </button>
                          {openMenuId === u.id && (
                            <div className="absolute right-0 top-full mt-1 w-52 rounded-lg border border-gray-200 bg-white shadow-lg z-30 py-1 text-left">
                              {isStandardUser && (
                                <button
                                  type="button"
                                  className="w-full px-3 py-2 text-sm text-slate-700 hover:bg-gray-50 flex items-center gap-2"
                                  onClick={() => openActivity(u)}
                                >
                                  <History className="w-4 h-4 text-slate-500" />
                                  View activity
                                </button>
                              )}
                              {!isAdminRole && (
                                <button
                                  type="button"
                                  className="w-full px-3 py-2 text-sm text-slate-700 hover:bg-gray-50 flex items-center gap-2"
                                  onClick={() => handlePromoteAdmin(u)}
                                >
                                  <Shield className="w-4 h-4 text-slate-500" />
                                  Make admin
                                </button>
                              )}
                              <button
                                type="button"
                                disabled={isSelf}
                                className="w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                                onClick={() => handleDelete(u)}
                              >
                                <Trash2 className="w-4 h-4" />
                                Delete
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {activityModal != null && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-labelledby="activity-modal-title"
          onClick={closeActivityModal}
        >
          <div
            className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[85vh] overflow-hidden flex flex-col border border-gray-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <h2 id="activity-modal-title" className="text-lg font-bold text-slate-900">
                User activity
              </h2>
              <button
                type="button"
                onClick={closeActivityModal}
                className="p-2 rounded-lg text-gray-500 hover:bg-gray-100"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="overflow-y-auto p-4 space-y-4">
              {activityLoading && (
                <p className="text-sm text-gray-500 text-center py-8">Loading activity…</p>
              )}
              {!activityLoading && activityData && (
                <>
                  <div className="text-sm text-slate-600">
                    <p className="font-semibold text-slate-800">{activityData.user?.name}</p>
                    <p className="text-gray-500">{activityData.user?.email}</p>
                    <p className="mt-2">
                      <span className="text-gray-500">Last active:</span>{' '}
                      {activityData.user?.last_active || '—'}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2">
                      <p className="text-gray-500 text-xs uppercase tracking-wide">Documents</p>
                      <p className="font-bold text-slate-900">{activityData.documents_count}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2">
                      <p className="text-gray-500 text-xs uppercase tracking-wide">Chat sessions</p>
                      <p className="font-bold text-slate-900">{activityData.chat_sessions_count}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">
                      Recent uploads
                    </p>
                    {(!activityData.recent_documents || activityData.recent_documents.length === 0) && (
                      <p className="text-sm text-gray-400">No documents uploaded yet.</p>
                    )}
                    <ul className="space-y-2 max-h-48 overflow-y-auto">
                      {(activityData.recent_documents || []).map((d) => (
                        <li
                          key={d.id}
                          className="text-sm border border-gray-100 rounded-lg px-3 py-2 flex flex-col gap-0.5"
                        >
                          <span className="font-medium text-slate-800 truncate">{d.filename}</span>
                          <span className="text-xs text-gray-500">{d.uploaded_at}</span>
                          <span className="text-xs text-gray-500">
                            Risk: {d.risk_level || '—'} · Clauses: {d.clauses_detected ?? '—'}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
