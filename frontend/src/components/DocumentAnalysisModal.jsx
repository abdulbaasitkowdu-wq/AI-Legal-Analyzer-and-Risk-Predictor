import React from 'react';
import { X } from 'lucide-react';
import AnalysisResultView from './AnalysisResultView';

/**
 * Full saved analysis: Overview tab + Highlighted document + summaries/deadlines.
 * `result` / `snapshot` are the normalized payload from analysis_json (same shape as POST /api/documents/analyze body).
 */
export default function DocumentAnalysisModal({
  open,
  onClose,
  title,
  subtitle,
  result,
  snapshot,
}) {
  if (!open) return null;
  const data = result || snapshot;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-gray-200"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-analysis-modal-title"
      >
        <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex justify-between items-center z-10">
          <div>
            <h3 id="document-analysis-modal-title" className="text-lg font-bold text-slate-900">
              {title}
            </h3>
            {subtitle ? <p className="text-sm text-gray-500">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-500"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {data ? (
            <AnalysisResultView
              analysis={data.analysis}
              calendarEvents={data.calendar_events || []}
              filename={title}
              summaries={data.summaries}
              showDashboardLink={false}
            />
          ) : (
            <p className="text-sm text-gray-500">
              No saved analysis for this document. Run{' '}
              <code className="bg-gray-100 px-1 rounded">migrations/001_add_analysis_json.sql</code> and analyze
              again.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
