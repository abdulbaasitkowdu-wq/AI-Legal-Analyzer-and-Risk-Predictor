import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import { getHistory, sendMessage, getMyDocuments } from '../../services/chatApi';

const ShareIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
    <path d="M13 4.5a2.5 2.5 0 11.702 1.737L6.97 9.604a2.518 2.518 0 010 .792l6.733 3.367a2.5 2.5 0 11-.671 1.341l-6.733-3.367a2.5 2.5 0 110-3.475l6.733-3.366A2.52 2.52 0 0113 4.5z" />
  </svg>
);
const DotsIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
    <path d="M3 10a1.5 1.5 0 113 0 1.5 1.5 0 01-3 0zM8.5 10a1.5 1.5 0 113 0 1.5 1.5 0 01-3 0zM15.5 8.5a1.5 1.5 0 100 3 1.5 1.5 0 000-3z" />
  </svg>
);

export default function ChatWindow({ sessionId, currentSession, onSessionCreated, userId, linkedDocumentId = null }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [docList, setDocList] = useState([]);
  const [contextDocumentId, setContextDocumentId] = useState(linkedDocumentId);
  const endRef = useRef(null);

  useEffect(() => {
    setContextDocumentId(linkedDocumentId);
  }, [linkedDocumentId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const docs = await getMyDocuments(userId);
        if (!cancelled) setDocList(Array.isArray(docs) ? docs : []);
      } catch (e) {
        console.error(e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  useEffect(() => {
    const load = async () => {
      if (!sessionId) {
        setMessages([]);
        return;
      }
      try {
        const history = await getHistory(sessionId, userId);
        setMessages(
          history.flatMap((h) => [
            { text: h.message, isUser: true, document_name: h.document_name },
            { text: h.response, isUser: false },
          ]),
        );
      } catch (e) {
        console.error(e);
      }
    };
    load();
  }, [sessionId, userId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text, file) => {
    const documentName = file ? file.name : null;
    const next = [...messages, { text, isUser: true, document_name: documentName }];
    setMessages(next);
    setLoading(true);
    try {
      const { response, session_id: newSid } = await sendMessage(
        text,
        sessionId,
        file,
        userId,
        contextDocumentId,
      );
      setMessages([...next, { text: response, isUser: false }]);
      if (!sessionId && newSid) onSessionCreated?.(newSid);
    } catch (e) {
      console.error(e);
      setMessages([
        ...next,
        {
          text: e.response?.data?.detail || e.message || 'Request failed.',
          isUser: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const title = currentSession?.title || 'AI Legal Assistant';

  return (
    <main className="flex-1 flex flex-col min-h-0 min-w-0 bg-white dark:bg-gray-950">
      <header className="flex items-center justify-between px-6 py-3.5 border-b border-gray-100 dark:border-gray-800 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            to="/"
            className="text-xs font-medium text-gray-500 hover:text-blue-600 dark:text-gray-400 shrink-0 mr-1"
          >
            ← App
          </Link>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-sm">
            A
          </div>
          <h1 className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">{title}</h1>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <ShareIcon />
          </button>
          <button
            type="button"
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <DotsIcon />
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        {!sessionId && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-2xl shadow-lg">
              ✦
            </div>
            <div>
              <h2 className="text-2xl font-semibold text-gray-800 dark:text-gray-100 mb-2">How can I help you today?</h2>
              <p className="text-gray-500 dark:text-gray-400 text-sm max-w-xs">
                Ask about contracts and clauses, or upload an image / PDF for context.
              </p>
            </div>
          </div>
        )}

        <div className="max-w-3xl mx-auto space-y-1">
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              text={msg.text}
              isUser={msg.isUser}
              document_name={msg.document_name}
            />
          ))}

          {loading && (
            <div className="flex items-center gap-3 py-3 pl-1">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-xs shrink-0">
                ✦
              </div>
              <div className="flex gap-1.5">
                {[0, 150, 300].map((delay) => (
                  <span
                    key={delay}
                    className="w-2 h-2 bg-gray-300 dark:bg-gray-600 rounded-full animate-bounce"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="px-4 pb-5 pt-2 shrink-0">
        <div className="max-w-3xl mx-auto space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
            <label htmlFor="chat-doc-context" className="shrink-0 font-medium">
              Document context
            </label>
            <select
              id="chat-doc-context"
              value={contextDocumentId ?? ''}
              onChange={(e) => {
                const v = e.target.value;
                setContextDocumentId(v === '' ? null : Number(v));
              }}
              disabled={loading}
              className="flex-1 min-w-[12rem] max-w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1.5 text-xs text-gray-800 dark:text-gray-100"
            >
              <option value="">None — general chat</option>
              {docList.map((d) => (
                <option key={d.id} value={d.id}>
                  {(d.filename || 'Untitled').slice(0, 80)}
                  {d.id != null ? ` (#${d.id})` : ''}
                </option>
              ))}
            </select>
          </div>
          <ChatInput onSend={handleSend} disabled={loading} />
          <p className="text-center text-[11px] text-gray-400 dark:text-gray-600 mt-2.5">
            AI can make mistakes. This is not legal advice — verify important information.
          </p>
        </div>
      </div>
    </main>
  );
}
