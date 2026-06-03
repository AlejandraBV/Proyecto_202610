/**
 * /evaluation — RAGAS-style quality evaluation dashboard
 *
 * Shows per-turn and conversation-level metrics:
 *   • Faithfulness      — content grounded in source material
 *   • Answer Relevance  — content addresses the user query
 *   • Context Precision — retrieved context was relevant & used
 *   • Overall           — weighted average
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/store/appStore';
import { EvaluationResult, EvaluationTurn } from '@/types';
import { ArrowLeft, BarChart2, CheckCircle, Zap, BookOpen, Star } from 'lucide-react';
import toast from 'react-hot-toast';

// ── Mini progress bar ─────────────────────────────────────────────────────────

const ScoreBar: React.FC<{ label: string; score: number; color: string }> = ({
  label, score, color,
}) => {
  const pct = Math.round(score * 100);
  const colorMap: Record<string, string> = {
    green:  'bg-green-500',
    blue:   'bg-blue-500',
    indigo: 'bg-indigo-500',
    amber:  'bg-amber-500',
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-600 font-medium">{label}</span>
        <span className="font-semibold text-gray-800">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colorMap[color] || 'bg-gray-400'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

// ── Turn row ──────────────────────────────────────────────────────────────────

const TurnRow: React.FC<{ turn: EvaluationTurn; index: number }> = ({ turn, index }) => (
  <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-xs text-gray-500 font-medium mb-0.5">Turn {index + 1} — User query</p>
        <p className="text-sm text-gray-800 truncate">{turn.user_query_preview}…</p>
      </div>
      <span
        className={`flex-shrink-0 text-sm font-bold px-2 py-0.5 rounded-full ${
          turn.overall >= 0.7
            ? 'bg-green-100 text-green-700'
            : turn.overall >= 0.5
            ? 'bg-yellow-100 text-yellow-700'
            : 'bg-red-100 text-red-700'
        }`}
      >
        {Math.round(turn.overall * 100)}%
      </span>
    </div>

    <div className="grid grid-cols-3 gap-3">
      <ScoreBar label="Faithfulness"      score={turn.faithfulness}      color="green" />
      <ScoreBar label="Answer Relevance"  score={turn.answer_relevance}  color="blue" />
      <ScoreBar label="Context Precision" score={turn.context_precision} color="indigo" />
    </div>
  </div>
);

// ── Stat card ────────────────────────────────────────────────────────────────

const StatCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
  description: string;
}> = ({ icon, label, value, color, description }) => {
  const colorMap: Record<string, string> = {
    green:  'border-green-200 bg-green-50',
    blue:   'border-blue-200 bg-blue-50',
    indigo: 'border-indigo-200 bg-indigo-50',
    amber:  'border-amber-200 bg-amber-50',
  };

  return (
    <div className={`rounded-xl border p-4 ${colorMap[color] || 'border-gray-200 bg-white'}`}>
      <div className="flex items-center gap-2 mb-2">{icon}<span className="text-sm font-medium text-gray-700">{label}</span></div>
      <p className="text-3xl font-bold text-gray-900">{Math.round(value * 100)}%</p>
      <p className="mt-1 text-xs text-gray-500">{description}</p>
    </div>
  );
};

// ── Page ──────────────────────────────────────────────────────────────────────

const EvaluationPage: React.FC = () => {
  const router = useRouter();
  const { conversations, currentConversation } = useAppStore();
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedConvId, setSelectedConvId] = useState<string>(
    currentConversation?.id ?? ''
  );

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) router.push('/login');
  }, [router]);

  const handleEvaluate = async () => {
    if (!selectedConvId) return;
    setLoading(true);
    try {
      const res = await apiClient.evaluateConversation(selectedConvId);
      setResult((res as any).data as EvaluationResult);
    } catch {
      toast.error('Evaluation failed. Make sure the conversation has messages.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4 flex items-center gap-3">
        <button onClick={() => router.back()} className="rounded-lg p-1.5 hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5 text-gray-600" />
        </button>
        <BarChart2 className="h-5 w-5 text-indigo-600" />
        <h1 className="text-xl font-semibold text-gray-900">RAGAS Evaluation</h1>
      </div>

      <div className="mx-auto max-w-4xl px-6 py-6 space-y-6">

        {/* Selector + run */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex gap-3">
          <select
            value={selectedConvId}
            onChange={(e) => { setSelectedConvId(e.target.value); setResult(null); }}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">— select a conversation —</option>
            {conversations.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
          <button
            onClick={handleEvaluate}
            disabled={!selectedConvId || loading}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Zap className="h-4 w-4" />
            {loading ? 'Evaluating…' : 'Run Evaluation'}
          </button>
        </div>

        {/* Results */}
        {result && (
          <>
            {/* Average score cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                icon={<CheckCircle className="h-4 w-4 text-green-600" />}
                label="Faithfulness"
                value={result.averages.faithfulness}
                color="green"
                description="Content grounded in source material"
              />
              <StatCard
                icon={<Zap className="h-4 w-4 text-blue-600" />}
                label="Answer Relevance"
                value={result.averages.answer_relevance}
                color="blue"
                description="Response addresses the query"
              />
              <StatCard
                icon={<BookOpen className="h-4 w-4 text-indigo-600" />}
                label="Context Precision"
                value={result.averages.context_precision}
                color="indigo"
                description="Retrieved context was used"
              />
              <StatCard
                icon={<Star className="h-4 w-4 text-amber-600" />}
                label="Overall"
                value={result.averages.overall}
                color="amber"
                description="Weighted average score"
              />
            </div>

            {/* Per-turn breakdown */}
            {result.turns.length > 0 ? (
              <div className="space-y-3">
                <h2 className="text-base font-semibold text-gray-800">Per-turn breakdown</h2>
                {result.turns.map((turn, i) => (
                  <TurnRow key={turn.message_id} turn={turn} index={i} />
                ))}
              </div>
            ) : (
              <p className="text-center text-sm text-gray-500 py-6">
                No turns with paired query + response found.
              </p>
            )}
          </>
        )}

        {!result && !loading && selectedConvId && (
          <p className="text-center text-sm text-gray-400 py-8">
            Click <strong>Run Evaluation</strong> to compute quality metrics for this conversation.
          </p>
        )}
      </div>
    </div>
  );
};

export default EvaluationPage;
