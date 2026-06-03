/**
 * /history — HITL Audit Trail page
 *
 * Shows a chronological log of all human-in-the-loop events for the
 * currently selected conversation:
 *   • Message ratings (👍)
 *   • AI refinements triggered by professor edits
 *   • Subject reclassification corrections
 *   • Agent decisions (Analyze / Generate / Review)
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/store/appStore';
import { AuditEvent } from '@/types';
import {
  ThumbsUp, Pencil, Tag, Brain, ChevronDown, ChevronUp,
  Clock, ArrowLeft,
} from 'lucide-react';
import toast from 'react-hot-toast';

// ── Event card ────────────────────────────────────────────────────────────────

const EventCard: React.FC<{ event: AuditEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(false);

  const icons: Record<string, React.ReactNode> = {
    message_rating:   <ThumbsUp className="h-4 w-4 text-green-600" />,
    refinement:       <Pencil className="h-4 w-4 text-indigo-600" />,
    reclassification: <Tag className="h-4 w-4 text-amber-600" />,
    agent_decision:   <Brain className="h-4 w-4 text-gray-500" />,
  };

  const labels: Record<string, string> = {
    message_rating:   'Message rated helpful',
    refinement:       'AI refinement triggered',
    reclassification: 'Subject corrected',
    agent_decision:   'Agent decision recorded',
  };

  const colors: Record<string, string> = {
    message_rating:   'border-green-200 bg-green-50',
    refinement:       'border-indigo-200 bg-indigo-50',
    reclassification: 'border-amber-200 bg-amber-50',
    agent_decision:   'border-gray-200 bg-gray-50',
  };

  const ts = new Date(event.timestamp).toLocaleString();

  return (
    <div className={`rounded-lg border p-3 ${colors[event.type] || 'border-gray-200 bg-white'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icons[event.type]}
          <span className="text-sm font-medium text-gray-800">{labels[event.type]}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Clock className="h-3 w-3" />
          {ts}
          <button onClick={() => setExpanded((v) => !v)} className="ml-1">
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-2 space-y-1 text-xs text-gray-700 pl-6 border-l-2 border-gray-300 ml-2">
          {event.type === 'message_rating' && (
            <>
              <p><span className="font-medium">Rating:</span> {event.rating === 1 ? '👍 Helpful' : '👎 Not helpful'}</p>
              {event.feedback_text && <p><span className="font-medium">Note:</span> {event.feedback_text}</p>}
            </>
          )}
          {event.type === 'reclassification' && (
            <>
              <p><span className="font-medium">Original:</span> {event.original_subject || '—'}</p>
              <p><span className="font-medium">Corrected to:</span> {event.corrected_subject}</p>
              {event.sample_prompt && (
                <p className="italic text-gray-500">"{event.sample_prompt}"</p>
              )}
            </>
          )}
          {event.type === 'agent_decision' && (
            <>
              <p><span className="font-medium">Agent:</span> {event.agent_name} (iteration {event.iteration})</p>
              <p><span className="font-medium">Decision:</span> {event.decision}</p>
              {event.quality_score !== undefined && (
                <p><span className="font-medium">Score:</span> {(event.quality_score * 100).toFixed(0)}%</p>
              )}
              {event.reasoning && <p className="text-gray-600">{event.reasoning}</p>}
            </>
          )}
          {event.type === 'refinement' && (
            <>
              <p><span className="font-medium">Refined message preview:</span></p>
              <p className="text-gray-600 line-clamp-3">{event.content_preview}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
};

// ── Page ──────────────────────────────────────────────────────────────────────

const HistoryPage: React.FC = () => {
  const router = useRouter();
  const { conversations, currentConversation } = useAppStore();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedConvId, setSelectedConvId] = useState<string>(
    currentConversation?.id ?? ''
  );

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) router.push('/login');
  }, [router]);

  useEffect(() => {
    if (!selectedConvId) return;
    setLoading(true);
    apiClient.getAuditTrail(selectedConvId)
      .then((res) => setEvents((res as any).data as AuditEvent[]))
      .catch(() => toast.error('Could not load audit trail'))
      .finally(() => setLoading(false));
  }, [selectedConvId]);

  const typeCounts = events.reduce<Record<string, number>>((acc, e) => {
    acc[e.type] = (acc[e.type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4 flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="rounded-lg p-1.5 hover:bg-gray-100"
        >
          <ArrowLeft className="h-5 w-5 text-gray-600" />
        </button>
        <h1 className="text-xl font-semibold text-gray-900">HITL Audit Trail</h1>
      </div>

      <div className="mx-auto max-w-4xl px-6 py-6 space-y-6">

        {/* Conversation selector */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select conversation
          </label>
          <select
            value={selectedConvId}
            onChange={(e) => setSelectedConvId(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">— choose a conversation —</option>
            {conversations.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        </div>

        {/* Summary chips */}
        {events.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(typeCounts).map(([type, count]) => (
              <span key={type} className="inline-flex items-center gap-1 rounded-full bg-white border border-gray-200 px-3 py-1 text-xs font-medium text-gray-700">
                {count}× {type.replace('_', ' ')}
              </span>
            ))}
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 border border-indigo-200 px-3 py-1 text-xs font-medium text-indigo-700">
              {events.length} total events
            </span>
          </div>
        )}

        {/* Event list */}
        {loading && (
          <p className="text-center text-sm text-gray-500 py-8">Loading audit trail…</p>
        )}
        {!loading && selectedConvId && events.length === 0 && (
          <p className="text-center text-sm text-gray-500 py-8">
            No HITL events recorded for this conversation yet.
          </p>
        )}
        {!loading && !selectedConvId && (
          <p className="text-center text-sm text-gray-400 py-8">
            Select a conversation above to view its audit trail.
          </p>
        )}

        <div className="space-y-3">
          {events.map((event, i) => (
            <EventCard key={i} event={event} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
