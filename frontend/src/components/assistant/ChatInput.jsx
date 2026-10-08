import React, { useState, useRef } from 'react';

const AttachIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
    <path
      fillRule="evenodd"
      d="M15.621 4.379a3 3 0 00-4.242 0l-7 7a1.5 1.5 0 002.122 2.121L14 6.243a1.5 1.5 0 012.121 2.122l-7.5 7.499a3 3 0 01-4.243-4.243l7.5-7.5a.75.75 0 011.061 1.061l-7.5 7.5a1.5 1.5 0 002.121 2.122l7.5-7.5a3 3 0 000-4.243z"
      clipRule="evenodd"
    />
  </svg>
);
const MicIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
    <path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
    <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z" />
  </svg>
);
const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
    <path d="M3.105 2.289a.75.75 0 00-.826.95l1.414 4.925A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.086l-1.414 4.926a.75.75 0 00.826.95 28.896 28.896 0 0015.293-7.154.75.75 0 000-1.115A28.897 28.897 0 003.105 2.289z" />
  </svg>
);

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const fileRef = useRef(null);
  const textareaRef = useRef(null);

  const canSend = text.trim() && !disabled;

  const submit = () => {
    if (!canSend) return;
    onSend(text, file);
    setText('');
    setFile(null);
    if (fileRef.current) fileRef.current.value = '';
    if (textareaRef.current) textareaRef.current.style.height = '24px';
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onResize = (e) => {
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  return (
    <div>
      {file && (
        <div className="flex items-center gap-2 mb-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs px-3 py-1.5 rounded-full w-fit">
          <span>📄</span>
          <span className="truncate max-w-[200px]">{file.name}</span>
          <button
            type="button"
            onClick={() => {
              setFile(null);
              if (fileRef.current) fileRef.current.value = '';
            }}
            className="ml-1 text-blue-400 hover:text-red-500 transition-colors font-bold"
          >
            ×
          </button>
        </div>
      )}

      <div
        className={`flex items-end gap-3 bg-gray-50 dark:bg-gray-900 border rounded-2xl px-4 py-3 shadow-sm transition-all duration-200
        ${disabled ? 'opacity-60 border-gray-200 dark:border-gray-700' : 'border-gray-200 dark:border-gray-700 focus-within:border-blue-400 dark:focus-within:border-blue-500 focus-within:shadow-md'}`}
      >
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors shrink-0 mb-0.5"
        >
          <AttachIcon />
        </button>
        <input ref={fileRef} type="file" accept="image/*,.pdf" onChange={(e) => setFile(e.target.files[0] || null)} className="hidden" />

        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            onResize(e);
          }}
          onKeyDown={onKey}
          placeholder="Ask a question, upload a file, or start a conversation..."
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent resize-none outline-none text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-600 leading-relaxed max-h-28"
          style={{ height: '24px' }}
        />

        <div className="flex items-end gap-2 shrink-0 mb-0.5">
          <button type="button" disabled={disabled} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
            <MicIcon />
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!canSend}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
              canSend
                ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
            }`}
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}
