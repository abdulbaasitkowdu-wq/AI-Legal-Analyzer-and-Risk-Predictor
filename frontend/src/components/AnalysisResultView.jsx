import React, { useState } from 'react';
import { Calendar, ShieldAlert, BookOpen, Highlighter, Scale, CheckCircle2, ListChecks } from 'lucide-react';
import { Link } from 'react-router-dom';

const RISK_LEVEL_CLASS = {
  high: 'bg-red-100 text-red-950',
  medium: 'bg-orange-100 text-orange-950',
  low: 'bg-green-100 text-green-950',
};

/**
 * Same layout as the post-upload success view: risk grid + deadlines (+ optional AI summaries).
 * `analysis` / `calendarEvents` match `response.data` from POST /api/documents/analyze.
 */
export default function AnalysisResultView({
  analysis,
  calendarEvents = [],
  filename,
  summaries = null,
  showDashboardLink = false,
  benchmark: storedBenchmark = null,
}) {
  const [summaryTab, setSummaryTab] = useState('technical');
  const [viewTab, setViewTab] = useState('overview');
  const benchmarkStatus = storedBenchmark?.status || (storedBenchmark ? 'error' : 'missing');
  const benchmarkErrorMessage =
    storedBenchmark?.confidence_note || 'Benchmarking is currently unavailable for this analysis.';


  const riskSegments = analysis?.risk_segments;
  const hasRiskSegments = Array.isArray(riskSegments) && riskSegments.length > 0;

  const hasSummaries =
    summaries &&
    typeof summaries === 'object' &&
    ['technical', 'layman', 'actionable'].some((k) =>
      String(summaries[k] ?? '').trim(),
    );

  return (
    <div className="space-y-6 animate-fade-in">
      {showDashboardLink && filename && (
        <p className="text-sm text-blue-600">
          <Link to="/" className="font-semibold hover:underline">
            Open Dashboard
          </Link>
          <span className="text-gray-500 font-normal"> to see this analysis anytime.</span>
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setViewTab('overview')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
            viewTab === 'overview'
              ? 'bg-slate-800 text-white shadow-sm'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
          }`}
        >
          Overview
        </button>
        <button
          type="button"
          onClick={() => setViewTab('document')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors inline-flex items-center gap-2 ${
            viewTab === 'document'
              ? 'bg-slate-800 text-white shadow-sm'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
          }`}
        >
          <Highlighter className="w-4 h-4" />
          Highlighted document
        </button>
        <button
          type="button"
          onClick={() => setViewTab('benchmarking')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors inline-flex items-center gap-2 ${
            viewTab === 'benchmarking'
              ? 'bg-slate-800 text-white shadow-sm'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
          }`}
        >
          <Scale className="w-4 h-4" />
          Benchmarking
        </button>
      </div>

      {viewTab === 'document' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
            <span className="font-semibold text-slate-700">Legend:</span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-3 rounded-sm bg-red-100 border border-red-200" />
              High
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-3 rounded-sm bg-orange-100 border border-orange-200" />
              Medium
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-3 rounded-sm bg-green-100 border border-green-200" />
              Low
            </span>
          </div>
          {hasRiskSegments ? (
            <div className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed max-h-[min(70vh,40rem)] overflow-y-auto p-4 bg-slate-50 rounded-lg border border-slate-100 font-serif">
              {riskSegments.map((seg, idx) => {
                const level = seg?.level;
                const cls =
                  level && RISK_LEVEL_CLASS[level] ? RISK_LEVEL_CLASS[level] : '';
                return (
                  <span key={`${idx}-${String(level)}`} className={cls}>
                    {seg?.text ?? ''}
                  </span>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">
              No highlighted text for this analysis. Re-run analysis on a document to generate risk highlights, or this
              may be an older saved result from before highlights were stored.
            </p>
          )}
        </div>
      )}

      {viewTab === 'overview' && (
        <>
      {hasSummaries && (
        <div className="bg-gradient-to-br from-slate-50 to-blue-50/30 p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2 mb-4 text-slate-800 font-bold">
            <BookOpen className="w-5 h-5 text-blue-600" />
            AI summaries
          </div>
          <div className="flex flex-wrap gap-2 mb-4">
            {['technical', 'layman', 'actionable'].map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => setSummaryTab(id)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  summaryTab === id
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                {id.charAt(0).toUpperCase() + id.slice(1)}
              </button>
            ))}
          </div>
          <div className="bg-white p-4 rounded-lg border border-slate-200 text-sm text-slate-700 whitespace-pre-wrap max-h-[28rem] overflow-y-auto leading-relaxed">
            {summaries[summaryTab] || '—'}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-50 p-6 rounded-xl border border-slate-200">
          <div className="flex items-center gap-2 mb-4 text-slate-800 font-bold">
            <ShieldAlert className="w-5 h-5 text-red-500" /> Risk Assessment
          </div>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-slate-500 font-medium">Risk Level</p>
              <p
                className={`text-xl font-black ${
                  analysis?.risk_level === 'High'
                    ? 'text-red-600'
                    : analysis?.risk_level === 'Medium'
                      ? 'text-yellow-600'
                      : 'text-green-600'
                }`}
              >
                {analysis?.risk_level || 'Unknown'}
              </p>
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Risk Score</p>
              <p className="text-lg font-bold text-slate-800">{analysis?.risk_score ?? 0} / 100</p>
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Risky Clauses Detected</p>
              <p className="text-lg font-bold text-slate-800">{analysis?.clauses_detected ?? 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-50 p-6 rounded-xl border border-slate-200">
          <div className="flex items-center gap-2 mb-4 text-slate-800 font-bold">
            <Calendar className="w-5 h-5 text-purple-500" /> Extracted Deadlines
          </div>
          {calendarEvents && calendarEvents.length > 0 ? (
            <ul className="space-y-3">
              {calendarEvents.map((event, idx) => (
                <li
                  key={idx}
                  className="bg-white p-3 rounded border border-slate-200 shadow-sm flex flex-col"
                >
                  <span className="font-bold text-sm text-slate-800">{event.title}</span>
                  <span className="text-xs text-slate-500 mt-1">
                    {event.date} at {event.time}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500 italic">
              No dates or deadlines detected in this document.
            </p>
          )}
        </div>
      </div>
        </>
      )}
      {viewTab === 'benchmarking' && (
        <div className="space-y-4">
          {!storedBenchmark ? (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-600">
              No saved benchmark for this analysis. Re-run Analyze to generate one.
            </div>
          ) : benchmarkStatus !== 'success' ? (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-900">
              <p className="font-semibold mb-1">Benchmark unavailable for this run</p>
              <p>{benchmarkErrorMessage}</p>
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50 via-white to-slate-50 p-6 shadow-sm">
                <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm mb-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Alignment with common practice
                </div>
                {storedBenchmark.alignment_score != null && (
                  <p className="text-4xl font-black text-emerald-700">
                    {storedBenchmark.alignment_score}
                    <span className="text-xl font-bold text-emerald-600">/100</span>
                  </p>
                )}
                {storedBenchmark.reassurance_summary && (
                  <p className="text-sm text-slate-700 mt-4 leading-relaxed">{storedBenchmark.reassurance_summary}</p>
                )}
              </div>
              {Array.isArray(storedBenchmark.similarities) && storedBenchmark.similarities.length > 0 && (
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-4 text-slate-900 font-bold">
                    <ListChecks className="w-5 h-5 text-indigo-600" />
                    Similarities to industry-standard patterns
                  </div>
                  <ul className="space-y-3">
                    {storedBenchmark.similarities.map((item, idx) => (
                      <li key={idx} className="border-l-4 border-indigo-200 pl-4 py-1 text-sm text-slate-700">
                        <p className="font-semibold text-slate-900">{item.title || 'Theme'}</p>
                        {item.detail && <p className="mt-1 leading-relaxed">{item.detail}</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
