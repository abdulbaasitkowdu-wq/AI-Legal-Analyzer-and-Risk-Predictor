import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, X, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import axios from 'axios';
import { useUser } from '../context/UserContext';
import AnalysisResultView from './AnalysisResultView';

const Uploader = () => {
  const { user } = useUser();
  const userId = user?.currentUser?.id;
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // 'success' or 'error'
  /** Shown while waiting between 503 retries */
  const [retryNote, setRetryNote] = useState(null);
  const [uploadErrorMessage, setUploadErrorMessage] = useState('');

  /** Same shape as POST /api/documents/analyze JSON (persisted as analysis_json). */
  const [analyzeResult, setAnalyzeResult] = useState(null);

  const fileInputRef = useRef(null);

  const ANALYZE_503_RETRY_MS = 120_000;
  const RETRY_INITIAL_MS = 2000;
  const RETRY_MAX_BACKOFF_MS = 15000;

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // Drag and Drop Event Handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (validTypes.includes(selectedFile.type)) {
      setFile(selectedFile);
      setUploadStatus(null);
      setAnalyzeResult(null);
    } else {
      alert("Invalid file type. Please upload a PDF or DOCX file.");
    }
  };

  const removeFile = () => {
    setFile(null);
    setUploadStatus(null);
    setAnalyzeResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // --- THE REAL API CONNECTION ---
  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setUploadStatus(null);
    setRetryNote(null);
    setUploadErrorMessage('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', String(userId));

    const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
    const started = Date.now();
    let attempt = 0;

    try {
      // Retry on 503 (service unavailable / model overloaded) for up to ANALYZE_503_RETRY_MS
      while (true) {
        attempt += 1;
        try {
          const response = await axios.post(`${API_URL}/api/documents/analyze`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          setAnalyzeResult(response.data);
          setUploadStatus('success');
          return;
        } catch (error) {
          const status = error.response?.status;
          const elapsed = Date.now() - started;
          const remaining = ANALYZE_503_RETRY_MS - elapsed;

          if (status !== 503 || remaining <= 0) {
            throw error;
          }

          const backoff = Math.min(
            RETRY_INITIAL_MS * 2 ** (attempt - 1),
            RETRY_MAX_BACKOFF_MS,
          );
          const waitMs = Math.min(backoff, Math.max(0, remaining));
          if (waitMs <= 0) {
            throw error;
          }

          const secWait = Math.ceil(waitMs / 1000);
          const secLeft = Math.ceil(remaining / 1000);
          setRetryNote(
            `Server temporarily unavailable (503). Retrying in ${secWait}s… (about ${secLeft}s left in retry window)`,
          );
          await sleep(waitMs);
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus('error');
      const detail = error?.response?.data?.detail;
      setUploadErrorMessage(
        typeof detail === 'string' && detail.trim()
          ? detail
          : 'Analysis failed. Check that the API is running and try again.',
      );
    } finally {
      setRetryNote(null);
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in text-gray-800">
      
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Upload Document</h1>
        <p className="text-gray-500 mt-1">Upload legal contracts, NDAs, or agreements for AI risk analysis.</p>
      </div>

      <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm">
        
        {/* Only show the upload box if we haven't successfully analyzed a file yet */}
        {uploadStatus !== 'success' ? (
          <div 
            className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 ease-in-out ${
              isDragging 
                ? 'border-blue-500 bg-blue-50' 
                : file ? 'border-gray-200 bg-gray-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input 
              type="file" 
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf,.docx"
              className="hidden" 
            />

            {!file ? (
              <div className="flex flex-col items-center justify-center space-y-4">
                <div className="p-4 bg-blue-100 rounded-full text-blue-600">
                  <UploadCloud className="w-10 h-10" />
                </div>
                <div>
                  <p className="text-lg font-bold text-slate-800">Drag & drop your document here</p>
                  <p className="text-sm text-gray-500 mt-1">or click to browse your files</p>
                </div>
                <button 
                  onClick={() => fileInputRef.current?.click()}
                  className="px-6 py-2.5 bg-white border border-gray-300 rounded-lg text-sm font-bold text-slate-700 hover:bg-gray-50 transition-colors shadow-sm mt-4"
                >
                  Browse Files
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center space-y-6">
                <div className="flex items-center gap-4 bg-white p-4 pr-6 rounded-lg border border-gray-200 shadow-sm w-full max-w-md relative">
                  <div className="p-3 bg-blue-50 rounded-lg text-blue-600">
                    <FileText className="w-8 h-8" />
                  </div>
                  <div className="text-left flex-1 overflow-hidden">
                    <p className="font-bold text-slate-800 truncate">{file.name}</p>
                    <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                  {!isUploading && (
                     <button onClick={removeFile} className="absolute -top-3 -right-3 p-1.5 bg-white border border-gray-200 rounded-full text-gray-400 hover:text-red-500 transition-colors">
                       <X className="w-4 h-4" />
                     </button>
                  )}
                </div>

                {uploadStatus === 'error' && (
                  <div className="flex items-center gap-2 text-red-600 bg-red-50 px-4 py-2 rounded-lg font-medium text-sm">
                    <AlertCircle className="w-5 h-5 shrink-0" />
                    <span>{uploadErrorMessage || 'Analysis failed. Check that the API is running and try again.'}</span>
                  </div>
                )}

                {retryNote && (
                  <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 px-4 py-2 rounded-lg max-w-md">
                    {retryNote}
                  </p>
                )}

                <div className="flex gap-4">
                  <button onClick={removeFile} disabled={isUploading} className="px-6 py-2.5 border border-gray-300 rounded-lg text-sm font-bold text-slate-700 hover:bg-gray-50 disabled:opacity-50">
                    Cancel
                  </button>
                  <button onClick={handleUpload} disabled={isUploading} className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50">
                    {isUploading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" /> Analyzing Document…
                      </>
                    ) : (
                      'Analyze Document'
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          
          /* --- ANALYSIS RESULTS VIEW --- */
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center justify-between border-b border-gray-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 text-green-600 rounded-full"><CheckCircle className="w-6 h-6" /></div>
                <div>
                  <h3 className="text-lg font-bold text-slate-800">Analysis Complete</h3>
                  <p className="text-sm text-gray-500">{file.name}</p>
                </div>
              </div>
              <button onClick={removeFile} className="text-sm font-bold text-blue-600 hover:text-blue-700">Upload Another</button>
            </div>

            {analyzeResult && (
              <AnalysisResultView
                analysis={analyzeResult.analysis}
                calendarEvents={analyzeResult.calendar_events}
                filename={analyzeResult.filename || file.name}
                summaries={analyzeResult.summaries}
                showDashboardLink
                benchmark={analyzeResult.benchmark}
              />
            )}
          </div>
        )}

      </div>
    </div>
  );
};

export default Uploader;