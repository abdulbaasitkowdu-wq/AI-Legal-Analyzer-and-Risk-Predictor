import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import ChatWindow from './ChatWindow';
import ChatSidebar from './ChatSidebar';
import { useUser } from '../../context/UserContext.jsx';
import { deleteSession, getSessions, renameSession } from '../../services/chatApi';

/**
 * Full-screen chat UI (sidebar + main) modeled after the SLIIT my_ai_assistant_project frontend.
 */
export default function LegalChatAssistant() {
  const [searchParams] = useSearchParams();
  const docParam = searchParams.get('documentId');
  const linkedDocumentId =
    docParam != null && docParam !== '' && !Number.isNaN(Number(docParam)) ? Number(docParam) : null;

  const { user } = useUser();
  const userId = user?.currentUser?.id ?? 1;

  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  /** Bump to remount ChatWindow so "New Chat" always clears UI (even when sessionId was already null). */
  const [composerKey, setComposerKey] = useState(0);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('chatDarkMode') === 'true');

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('chatDarkMode', 'true');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('chatDarkMode', 'false');
    }
  }, [darkMode]);

  const fetchSessions = useCallback(async () => {
    try {
      setSessions(await getSessions(userId));
    } catch (e) {
      console.error('Error fetching sessions:', e);
    }
  }, [userId]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleRenameSession = async (id, title) => {
    try {
      await renameSession(id, title, userId);
      fetchSessions();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteSession = async (id) => {
    if (!window.confirm('Delete this chat?')) return;
    try {
      await deleteSession(id, userId);
      if (currentSessionId === id) {
        setCurrentSessionId(null);
        setComposerKey((k) => k + 1);
      }
      fetchSessions();
    } catch (e) {
      console.error(e);
    }
  };

  const currentSession = sessions.find((s) => s.id === currentSessionId);

  return (
    <div className="flex h-full min-h-0 w-full flex-1 overflow-hidden bg-white dark:bg-gray-950">
      <ChatSidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={setCurrentSessionId}
        onNewSession={() => {
          setCurrentSessionId(null);
          setComposerKey((k) => k + 1);
        }}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode((d) => !d)}
      />
      <ChatWindow
        key={composerKey}
        sessionId={currentSessionId}
        currentSession={currentSession}
        onSessionCreated={(id) => {
          setCurrentSessionId(id);
          fetchSessions();
        }}
        userId={userId}
        linkedDocumentId={linkedDocumentId}
      />
    </div>
  );
}
