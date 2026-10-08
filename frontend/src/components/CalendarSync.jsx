import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import {
  Calendar as CalendarIcon,
  Clock,
  RefreshCw,
  Cloud,
  CloudOff,
  Trash2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Plus,
  X,
  Pencil,
} from 'lucide-react';
import axios from 'axios';
import { useUser } from '../context/UserContext';

const API = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
const GOOGLE_STATUS_POLL_MS = 3 * 1000;

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function pad2(n) {
  return String(n).padStart(2, '0');
}

function toISODateLocal(year, monthIndex, day) {
  return `${year}-${pad2(monthIndex + 1)}-${pad2(day)}`;
}

function monthMeta(year, monthIndex) {
  const first = new Date(year, monthIndex, 1);
  const lastDay = new Date(year, monthIndex + 1, 0).getDate();
  const leading = (first.getDay() + 6) % 7;
  return { first, lastDay, leading };
}

function buildCalendarCells(year, monthIndex) {
  const { lastDay, leading } = monthMeta(year, monthIndex);
  const cells = [];
  for (let i = 0; i < leading; i++) {
    cells.push({ kind: 'empty', key: `e-${i}` });
  }
  for (let d = 1; d <= lastDay; d++) {
    cells.push({
      kind: 'day',
      day: d,
      iso: toISODateLocal(year, monthIndex, d),
      key: `d-${d}`,
    });
  }
  while (cells.length % 7 !== 0) {
    cells.push({ kind: 'empty', key: `t-${cells.length}` });
  }
  return cells;
}

const CalendarSync = () => {
  const { user } = useUser();
  const userId = user?.currentUser?.id;

  const [syncToast, setSyncToast] = useState({
    show: false,
    type: 'success', // "success" | "error"
    message: '',
  });

  const showSyncToast = (message, type = 'success') => {
    setSyncToast({
      show: true,
      type,
      message,
    });

    setTimeout(() => {
      setSyncToast((prev) => ({ ...prev, show: false }));
    }, 3500);
  };

  const [events, setEvents] = useState([]);
  const [warning, setWarning] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);

  const [modalError, setModalError] = useState('');
  const [modalErrorFor, setModalErrorFor] = useState(null);

  const now = new Date();
  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth());

  const [modal, setModal] = useState(null);
  const googleStatusInFlight = useRef(false);

  const todayIso = toISODateLocal(now.getFullYear(), now.getMonth(), now.getDate());

  const load = useCallback(async () => {
    if (userId == null) return;
    setLoading(true);
    setError(null);
    setWarning(null);
    try {
      const { data } = await axios.get(`${API}/api/events`, { params: { user_id: userId } });
      setEvents(data.events || []);
      if (data.warning) setWarning(data.warning);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load events');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    load();
  }, [load]);

  const refreshGoogleStatuses = useCallback(async () => {
    if (userId == null || googleStatusInFlight.current) return;
    const hasSyncedEvents = events.some(
      (ev) => ev.status === 'synced' && ev.google_event_id
    );
    if (!hasSyncedEvents) return;

    googleStatusInFlight.current = true;
    try {
      const { data } = await axios.post(
        `${API}/api/events/refresh-google-status`,
        {},
        { params: { user_id: userId } }
      );
      const changedIds = data.changed_event_ids || [];
      if (changedIds.length === 0) return;

      const changedSet = new Set(changedIds);
      setEvents((prev) =>
        prev.map((ev) =>
          changedSet.has(ev.event_id)
            ? { ...ev, status: 'draft', google_event_id: null }
            : ev
        )
      );
    } catch (_e) {
      // Keep polling quiet; a temporary Google/API error should not interrupt the page.
    } finally {
      googleStatusInFlight.current = false;
    }
  }, [events, userId]);

  useEffect(() => {
    const timer = setInterval(refreshGoogleStatuses, GOOGLE_STATUS_POLL_MS);
    refreshGoogleStatuses();
    return () => clearInterval(timer);
  }, [refreshGoogleStatuses]);

  const eventsByDate = useMemo(() => {
    const map = {};
    for (const ev of events) {
      const d = ev.event_date;
      if (!d) continue;
      if (!map[d]) map[d] = [];
      map[d].push(ev);
    }
    return map;
  }, [events]);

  const upcomingSyncedEvents = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const nextWeek = new Date(today);
    nextWeek.setDate(today.getDate() + 7);

    return events
      .filter((ev) => {
        if (ev.status !== 'synced') return false;
        if (!ev.event_date) return false;
        const evDate = new Date(ev.event_date);
        evDate.setHours(0, 0, 0, 0);
        return evDate >= today && evDate <= nextWeek;
      })
      .sort((a, b) => new Date(a.event_date) - new Date(b.event_date));
  }, [events]);

  const futureEvents = useMemo(() => {
    return events.filter((ev) => {
      if (!ev.event_date) return false;
      return ev.event_date >= todayIso;
    });
  }, [events, todayIso]);

  const monthLabel = new Date(viewYear, viewMonth, 1).toLocaleString(undefined, {
    month: 'long',
    year: 'numeric',
  });

  const shiftMonth = (delta) => {
    if (delta < 0 && viewMonth === 0) {
      setViewYear((y) => y - 1);
      setViewMonth(11);
    } else if (delta > 0 && viewMonth === 11) {
      setViewYear((y) => y + 1);
      setViewMonth(0);
    } else {
      setViewMonth((m) => m + delta);
    }
  };

  const openDateModal = (isoDate) => {
    const dayEvents = (eventsByDate[isoDate] || [])
      .map((ev) => ({
        event_id: ev.event_id,
        title: ev.title || '',
        event_date: ev.event_date || isoDate,
        event_time: ev.event_time || '09:00',
        status: ev.status || 'draft',
      }))
      .sort((a, b) => (a.event_time || '').localeCompare(b.event_time || ''));

    setError(null);
    setModalError('');
    setModalErrorFor(null);

    setModal({
      selectedDate: isoDate,
      items: dayEvents,
      showAddForm: false,
      newItem: {
        title: 'New deadline',
        event_date: isoDate < todayIso ? todayIso : isoDate,
        event_time: '09:00',
      },
    });
  };

  const openSingleEditModal = (ev) => {
    setError(null);
    setModalError('');
    setModalErrorFor(null);

    setModal({
      selectedDate: ev.event_date,
      items: [
        {
          event_id: ev.event_id,
          title: ev.title || '',
          event_date: ev.event_date || todayIso,
          event_time: ev.event_time || '09:00',
          status: ev.status || 'draft',
        },
      ],
      showAddForm: false,
      newItem: {
        title: 'New deadline',
        event_date: ev.event_date < todayIso ? todayIso : ev.event_date,
        event_time: '09:00',
      },
    });
  };

  const updateModalEvent = (eventId, field, value) => {
    setModal((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        items: prev.items.map((item) =>
          item.event_id === eventId ? { ...item, [field]: value } : item
        ),
      };
    });
  };

  const saveEditedEvent = async (item) => {
    if (!userId) return;

    if (item.event_date < todayIso) {
      setModalError('⛔ You cannot move a deadline to a past date.');
      setModalErrorFor(item.event_id);
      return;
    }

    setBusyId(`edit-${item.event_id}`);
    setError(null);
    setModalError('');
    setModalErrorFor(null);

    try {
      await axios.put(
        `${API}/api/events/${item.event_id}`,
        {
          title: item.title,
          event_date: item.event_date,
          event_time: item.event_time || '09:00',
        },
        { params: { user_id: userId } }
      );

      await load();

      setModal(null);
    } catch (e) {
      const d = e.response?.data?.detail;
      setModalError(typeof d === 'string' ? d : e.message || 'Could not update event');
      setModalErrorFor(item.event_id);
    } finally {
      setBusyId(null);
    }
  };

  const updateNewModalItem = (field, value) => {
    setModal((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        newItem: {
          ...prev.newItem,
          [field]: value,
        },
      };
    });
  };

  const saveNewModalEvent = async () => {
    if (!modal || !userId) return;

    const title = (modal.newItem.title || '').trim();
    if (title.length < 3) {
      setError('Title must be at least 3 characters.');
      return;
    }

    if (modal.newItem.event_date < todayIso) {
      setError('⛔ You cannot save a deadline for a past date.');
      return;
    }

    setBusyId('modal-new');
    setError(null);

    try {
      const { data } = await axios.post(
        `${API}/api/events`,
        {
          title,
          event_date: modal.newItem.event_date,
          event_time: modal.newItem.event_time || '09:00',
        },
        { params: { user_id: userId } }
      );

      await load();

      setModal((prev) => {
        if (!prev) return prev;

        const newEvent = {
          event_id: data.event_id,
          title,
          event_date: modal.newItem.event_date,
          event_time: modal.newItem.event_time || '09:00',
          status: 'draft',
        };

        return {
          ...prev,
          items:
            newEvent.event_date === prev.selectedDate
              ? [...prev.items, newEvent].sort((a, b) =>
                  (a.event_time || '').localeCompare(b.event_time || '')
                )
              : prev.items,
          showAddForm: false,
          newItem: {
            title: 'New deadline',
            event_date: prev.selectedDate < todayIso ? todayIso : prev.selectedDate,
            event_time: '09:00',
          },
        };
      });
    } catch (e) {
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Could not save event');
    } finally {
      setBusyId(null);
    }
  };

  const sync = async (eventId) => {
    const target = events.find((ev) => ev.event_id === eventId);

    if (target) {
      const conflict = events.find(
        (ev) =>
          ev.event_id !== eventId &&
          ev.status === 'synced' &&
          ev.event_date === target.event_date &&
          (ev.event_time || '09:00') === (target.event_time || '09:00')
      );

      if (conflict) {
        showSyncToast(
          `"${target.title}" could not sync. Another synced event already exists on this date and time.`,
          'error'
        );
        return;
      }
    }

    setBusyId(eventId);
    setError(null);

    try {
      await axios.post(
        `${API}/api/events/${eventId}/sync`,
        {},
        { params: { user_id: userId } }
      );

      await load();

      if (target) {
        showSyncToast(`"${target.title}" synced to Google Calendar`, 'success');
      } else {
        showSyncToast('Event synced to Google Calendar', 'success');
      }
    } catch (e) {
      showSyncToast(
        e.response?.data?.detail || e.message || 'Sync failed',
        'error'
      );
    } finally {
      setBusyId(null);
    }
  };

  const unsync = async (eventId) => {
    setBusyId(eventId);
    setError(null);

    try {
      await axios.post(
        `${API}/api/events/${eventId}/unsync`,
        {},
        { params: { user_id: userId } }
      );

      await load();
      showSyncToast('Deadline removed from Google Calendar', 'success');
    } catch (e) {
      showSyncToast(
        e.response?.data?.detail || e.message || 'Unsync failed',
        'error'
      );
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (eventId) => {
    if (!window.confirm('Delete this deadline from the list?')) return;
    setBusyId(eventId);
    setError(null);
    try {
      await axios.delete(`${API}/api/events/${eventId}`, { params: { user_id: userId } });
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Delete failed');
    } finally {
      setBusyId(null);
    }
  };

  if (userId == null) {
    return (
      <div className="max-w-5xl mx-auto p-8 text-center text-gray-500">
        Sign in to view saved deadlines and sync with Google Calendar.
      </div>
    );
  }

  return (
    <div className="w-full px-2 py-6 space-y-8 animate-fade-in text-gray-800">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <CalendarIcon className="w-8 h-8 text-blue-600" />
            Calendar &amp; Deadlines
          </h1>
        </div>
        <button
          type="button"
          onClick={() => load()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 bg-white text-sm font-medium hover:bg-gray-50"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {upcomingSyncedEvents.length > 0 && (
        <div className="bg-blue-50 border border-red-200 rounded-xl p-5 shadow-sm animate-fade-in">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <h2 className="text-lg font-bold text-red-700">Upcoming Synced Deadlines (Next 7 Days)</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcomingSyncedEvents.map((ev) => (
              <div
                key={ev.event_id}
                className="bg-white border border-blue-100 rounded-lg p-3 shadow-sm flex flex-col hover:border-blue-300 transition-colors"
              >
                <span className="font-bold text-slate-800 truncate" title={ev.title}>
                  {ev.title}
                </span>
                <span className="text-sm font-medium text-blue-700 mt-2 flex items-center gap-1.5">
                  <CalendarIcon className="w-4 h-4 shrink-0" />
                  {ev.event_date}{' '}
                  {ev.event_time && (
                    <>
                      <Clock className="w-3.5 h-3.5 ml-1 shrink-0" /> {ev.event_time}
                    </>
                  )}
                </span>
                <span className="text-[10px] uppercase font-bold text-blue-500 mt-1 tracking-wider">
                  Synced to Google
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {warning && (
        <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-sm p-4">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <span>{warning}</span>
        </div>
      )}

      <div className="grid lg:grid-cols-[1fr_1.3fr] gap-8">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <div className="flex items-center justify-between mb-4">
            <button
              type="button"
              onClick={() => shiftMonth(-1)}
              className="p-2 rounded-lg hover:bg-gray-100"
              aria-label="Previous month"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="font-semibold text-slate-800">{monthLabel}</span>
            <button
              type="button"
              onClick={() => shiftMonth(1)}
              className="p-2 rounded-lg hover:bg-gray-100"
              aria-label="Next month"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-gray-400 mb-2">
            {WEEKDAYS.map((d) => (
              <div key={d}>{d}</div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {buildCalendarCells(viewYear, viewMonth).map((cell) => {
              if (cell.kind === 'empty') {
                return <div key={cell.key} className="aspect-square min-h-[2.5rem]" />;
              }
              const dayEvents = eventsByDate[cell.iso] || [];
              const isToday = cell.iso === todayIso;
              const isPast = cell.iso < todayIso;
              return (
                <button
                  key={cell.key}
                  type="button"
                  onClick={() => openDateModal(cell.iso)}
                  title={`View deadlines on ${cell.iso}`}
                  className={`aspect-square min-h-[2.5rem] rounded-lg border text-sm font-medium transition-colors flex flex-col items-center justify-start pt-1 px-0.5
                      ${
                        isPast
                          ? 'border-gray-100 bg-slate-50/80 text-slate-600 hover:border-blue-200 hover:bg-blue-50/40'
                          : isToday
                            ? 'border-blue-500 bg-blue-50 text-blue-900'
                            : 'border-gray-100 hover:border-blue-300 hover:bg-blue-50/50 text-slate-800'
                      }`}
                >
                  <span>{cell.day}</span>
                  {dayEvents.length > 0 && (
                    <span className="text-[10px] leading-tight text-blue-600 font-semibold mt-0.5">
                      {dayEvents.length} due
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 min-h-[320px]">
          <h2 className="text-lg font-bold text-slate-900 mb-3">Your deadlines</h2>
          {loading ? (
            <p className="text-gray-500 text-sm">Loading…</p>
          ) : futureEvents.length === 0 ? (
            <p className="text-gray-500 text-sm">
              No upcoming deadlines. Add one from the calendar or analyze a document.
            </p>
          ) : (
            <ul className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
              {futureEvents.map((ev) => (
                <li
                  key={ev.event_id}
                  className="flex flex-col sm:flex-row sm:items-center gap-2 border border-gray-100 rounded-lg p-3 bg-slate-50/50"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 truncate">{ev.title}</p>
                    <p className="text-xs text-gray-500 flex items-center gap-2 mt-1">
                      <span>
                        {ev.event_date}{' '}
                        {ev.event_time && (
                          <>
                            <Clock className="w-3 h-3 inline" /> {ev.event_time}
                          </>
                        )}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          ev.status === 'synced'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-200 text-gray-700'
                        }`}
                      >
                        {ev.status || 'draft'}
                      </span>
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    {ev.status === 'synced' ? (
                      <button
                        type="button"
                        disabled={busyId === ev.event_id}
                        onClick={() => unsync(ev.event_id)}
                        className="inline-flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium bg-white border border-gray-200 hover:bg-gray-50"
                      >
                        <CloudOff className="w-3.5 h-3.5" />
                        Unsync
                      </button>
                    ) : (
                      <button
                        type="button"
                        disabled={busyId === ev.event_id}
                        onClick={() => sync(ev.event_id)}
                        className="inline-flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium bg-blue-600 text-white hover:bg-blue-700"
                      >
                        <Cloud className="w-3.5 h-3.5" />
                        Sync
                      </button>
                    )}

                    <button
                      type="button"
                      disabled={busyId === ev.event_id}
                      onClick={() => openSingleEditModal(ev)}
                      className="inline-flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium bg-white border border-gray-200 hover:bg-gray-50"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                      Edit
                    </button>

                    <button
                      type="button"
                      disabled={busyId === ev.event_id}
                      onClick={() => remove(ev.event_id)}
                      className="inline-flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-start gap-3">
              <h3 className="text-lg font-bold text-slate-900">Deadlines on {modal.selectedDate}</h3>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() =>
                    setModal((prev) =>
                      prev
                        ? {
                            ...prev,
                            showAddForm: !prev.showAddForm,
                          }
                        : prev
                    )
                  }
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Plus className="w-4 h-4" />
                  New deadline
                </button>

                <button
                  type="button"
                  onClick={() => setModal(null)}
                  className="p-1 rounded hover:bg-gray-100"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm px-4 py-3">
                {error}
              </div>
            )}

            {modal.showAddForm && (
              <div className="border border-blue-200 rounded-xl p-4 bg-blue-50/50 space-y-4">
                <h4 className="font-semibold text-slate-900">Add new deadline</h4>

                <label className="block text-sm">
                  <span className="text-gray-600">Title</span>
                  <input
                    className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                    value={modal.newItem.title}
                    onChange={(e) => updateNewModalItem('title', e.target.value)}
                  />
                </label>

                <div className="grid sm:grid-cols-2 gap-4">
                  <label className="block text-sm">
                    <span className="text-gray-600">Date</span>
                    <input
                      type="date"
                      min={todayIso}
                      className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                      value={modal.newItem.event_date}
                      onChange={(e) => updateNewModalItem('event_date', e.target.value)}
                    />
                  </label>

                  <label className="block text-sm">
                    <span className="text-gray-600">Time (24h)</span>
                    <input
                      type="time"
                      className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                      value={modal.newItem.event_time}
                      onChange={(e) => updateNewModalItem('event_time', e.target.value)}
                    />
                  </label>
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      setModal((prev) =>
                        prev
                          ? {
                              ...prev,
                              showAddForm: false,
                              newItem: {
                                title: 'New deadline',
                                event_date:
                                  prev.selectedDate < todayIso ? todayIso : prev.selectedDate,
                                event_time: '09:00',
                              },
                            }
                          : prev
                      )
                    }
                    className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 hover:bg-gray-50 bg-white"
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    disabled={busyId === 'modal-new'}
                    onClick={saveNewModalEvent}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    Save
                  </button>
                </div>
              </div>
            )}

            {modal.items.length === 0 ? (
              <div className="rounded-lg border border-dashed border-gray-300 p-6 text-sm text-gray-500 text-center">
                No deadlines on this date.
              </div>
            ) : (
              <div className="space-y-4">
                {modal.items.map((item) => (
                  <div
                    key={item.event_id}
                    className="border border-gray-200 rounded-xl p-4 bg-slate-50/50"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-900">{item.title}</p>

                        {modalErrorFor === item.event_id && (
                          <p className="mt-1 text-sm text-red-600">{modalError}</p>
                        )}

                        <span
                          className={`inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            item.status === 'synced'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-200 text-gray-700'
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>
                    </div>

                    <label className="block text-sm mt-4">
                      <span className="text-gray-600">Title</span>
                      <input
                        className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                        value={item.title}
                        onChange={(e) => updateModalEvent(item.event_id, 'title', e.target.value)}
                      />
                    </label>

                    <div className="grid sm:grid-cols-2 gap-4 mt-4">
                      <label className="block text-sm">
                        <span className="text-gray-600">Date</span>
                        <input
                          type="date"
                          min={todayIso}
                          className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                          value={item.event_date}
                          onChange={(e) =>
                            updateModalEvent(item.event_id, 'event_date', e.target.value)
                          }
                        />
                      </label>

                      <label className="block text-sm">
                        <span className="text-gray-600">Time (24h)</span>
                        <input
                          type="time"
                          className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                          value={item.event_time || '09:00'}
                          onChange={(e) =>
                            updateModalEvent(item.event_id, 'event_time', e.target.value)
                          }
                        />
                      </label>
                    </div>

                    <div className="flex justify-end pt-4">
                      <button
                        type="button"
                        disabled={busyId === `edit-${item.event_id}`}
                        onClick={() => saveEditedEvent(item)}
                        className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        Save changes
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {syncToast.show && (
        <div
          className={`fixed top-5 right-5 z-[60] flex items-center gap-3 rounded-2xl px-6 py-4 shadow-2xl text-white min-w-[360px] max-w-[520px]
            ${syncToast.type === 'success' ? 'bg-[#08142b]' : 'bg-[#7f1d1d]'}`}
        >
          <div className="shrink-0">
            {syncToast.type === 'success' ? (
              <CalendarIcon className="w-5 h-5" />
            ) : (
              <AlertCircle className="w-5 h-5" />
            )}
          </div>

          <div className="text-sm font-medium leading-6">{syncToast.message}</div>
        </div>
      )}
    </div>
  );
};

export default CalendarSync;
