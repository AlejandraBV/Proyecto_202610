/**
 * /question-bank — Question Bank page
 *
 * Browse, search, filter, add, and delete saved questions.
 * Questions are automatically extracted from generated exams and can
 * also be added manually.
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { apiClient } from '@/lib/api';
import { Question, QuestionCreate } from '@/types';
import {
  BookmarkPlus, Search, Trash2, ChevronDown, ChevronUp,
  Plus, ArrowLeft, Filter, RefreshCw,
} from 'lucide-react';
import toast from 'react-hot-toast';

// ── Bloom badge colors ────────────────────────────────────────────────────────
const BLOOM_COLORS: Record<string, string> = {
  Remember:   'bg-green-100 text-green-700',
  Understand: 'bg-blue-100 text-blue-700',
  Apply:      'bg-yellow-100 text-yellow-700',
  Analyze:    'bg-orange-100 text-orange-700',
  Evaluate:   'bg-red-100 text-red-700',
  Create:     'bg-purple-100 text-purple-700',
};

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner:     'bg-gray-100 text-gray-600',
  intermediate: 'bg-blue-50 text-blue-700',
  advanced:     'bg-red-50 text-red-700',
};

// ── Question card ─────────────────────────────────────────────────────────────

const QuestionCard: React.FC<{
  question: Question;
  onDelete: (id: string) => void;
}> = ({ question: q, onDelete }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 hover:border-indigo-200 transition-colors">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-gray-800 flex-1 leading-relaxed">{q.content}</p>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="rounded p-1 hover:bg-gray-100 text-gray-400 hover:text-gray-600"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          <button
            onClick={() => onDelete(q.id)}
            className="rounded p-1 hover:bg-red-50 text-gray-400 hover:text-red-500"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Badge row */}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {q.subject && (
          <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full border border-indigo-200">
            {q.subject}
          </span>
        )}
        {q.topic && (
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
            {q.topic}
          </span>
        )}
        {q.bloom_level && (
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${BLOOM_COLORS[q.bloom_level] || 'bg-gray-100 text-gray-600'}`}>
            {q.bloom_level}
          </span>
        )}
        {q.difficulty && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${DIFFICULTY_COLORS[q.difficulty] || 'bg-gray-100 text-gray-600'}`}>
            {q.difficulty}
          </span>
        )}
        {(q.tags || []).map((tag) => (
          <span key={tag} className="text-xs bg-gray-50 text-gray-500 px-2 py-0.5 rounded-full border border-gray-200">
            #{tag}
          </span>
        ))}
      </div>

      {/* Expanded answer */}
      {expanded && q.answer && (
        <div className="mt-3 rounded-lg bg-gray-50 border border-gray-200 p-3">
          <p className="text-xs font-medium text-gray-500 mb-1">Answer / Solution</p>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{q.answer}</p>
        </div>
      )}
    </div>
  );
};

// ── Add question modal ────────────────────────────────────────────────────────

const AddQuestionModal: React.FC<{
  onClose: () => void;
  onSave: (data: QuestionCreate) => Promise<void>;
}> = ({ onClose, onSave }) => {
  const [content, setContent] = useState('');
  const [answer, setAnswer] = useState('');
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [bloomLevel, setBloomLevel] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    setSaving(true);
    try {
      await onSave({
        content: content.trim(),
        answer: answer.trim() || undefined,
        subject: subject.trim() || undefined,
        topic: topic.trim() || undefined,
        bloom_level: bloomLevel || undefined,
        difficulty: difficulty || undefined,
      });
      onClose();
    } catch {
      toast.error('Could not save question');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Add Question Manually</h2>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Question *</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={3}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              placeholder="Enter question text…"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Answer / Solution (optional)</label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              placeholder="Model answer or key points…"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Subject</label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                placeholder="e.g. Biology"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Topic</label>
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                placeholder="e.g. Cell division"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Bloom level</label>
              <select
                value={bloomLevel}
                onChange={(e) => setBloomLevel(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                <option value="">— none —</option>
                {['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'].map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                <option value="">— none —</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !content.trim()}
              className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save Question'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ── Page ──────────────────────────────────────────────────────────────────────

const QuestionBankPage: React.FC = () => {
  const router = useRouter();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);

  // Filters
  const [searchQ, setSearchQ] = useState('');
  const [filterSubject, setFilterSubject] = useState('');
  const [filterBloom, setFilterBloom] = useState('');
  const [filterDiff, setFilterDiff] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) router.push('/login');
    else loadQuestions();
  }, [router]);

  const loadQuestions = async (params?: any) => {
    setLoading(true);
    try {
      const res = await apiClient.listQuestions(params);
      setQuestions(((res as any).data as Question[]) || []);
    } catch {
      toast.error('Could not load questions');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadQuestions({
      q: searchQ || undefined,
      subject: filterSubject || undefined,
      bloom_level: filterBloom || undefined,
      difficulty: filterDiff || undefined,
    });
  };

  const handleDelete = async (id: string) => {
    try {
      await apiClient.deleteQuestion(id);
      setQuestions((qs) => qs.filter((q) => q.id !== id));
      toast.success('Question deleted');
    } catch {
      toast.error('Could not delete question');
    }
  };

  const handleSave = async (data: QuestionCreate) => {
    const res = await apiClient.createQuestion(data);
    const saved = (res as any).data as Question;
    setQuestions((qs) => [saved, ...qs]);
    toast.success('Question saved!');
  };

  // Unique subjects for filter dropdown
  const subjects = Array.from(new Set(questions.map((q) => q.subject).filter(Boolean)));

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="rounded-lg p-1.5 hover:bg-gray-100">
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </button>
          <BookmarkPlus className="h-5 w-5 text-emerald-600" />
          <h1 className="text-xl font-semibold text-gray-900">Question Bank</h1>
          <span className="text-sm text-gray-500 ml-2">({questions.length} questions)</span>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        >
          <Plus className="h-4 w-4" />
          Add Manually
        </button>
      </div>

      <div className="mx-auto max-w-4xl px-6 py-6 space-y-6">

        {/* Search / filter bar */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search questions…"
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <button
              onClick={handleSearch}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              <Filter className="h-4 w-4" />
              Filter
            </button>
            <button
              onClick={() => { setSearchQ(''); setFilterSubject(''); setFilterBloom(''); setFilterDiff(''); loadQuestions(); }}
              className="rounded-lg border border-gray-300 p-2 hover:bg-gray-50"
              title="Reset filters"
            >
              <RefreshCw className="h-4 w-4 text-gray-500" />
            </button>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <select
              value={filterSubject}
              onChange={(e) => setFilterSubject(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none"
            >
              <option value="">All subjects</option>
              {subjects.map((s) => <option key={s} value={s!}>{s}</option>)}
            </select>

            <select
              value={filterBloom}
              onChange={(e) => setFilterBloom(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none"
            >
              <option value="">All Bloom levels</option>
              {['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>

            <select
              value={filterDiff}
              onChange={(e) => setFilterDiff(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none"
            >
              <option value="">All difficulties</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
        </div>

        {/* Questions list */}
        {loading && (
          <p className="text-center text-sm text-gray-500 py-8">Loading question bank…</p>
        )}
        {!loading && questions.length === 0 && (
          <div className="text-center py-12">
            <BookmarkPlus className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No questions yet.</p>
            <p className="text-gray-400 text-xs mt-1">
              Generate an exam and click <strong>Save to Bank</strong> on any message,
              or use <strong>Add Manually</strong> above.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {questions.map((q) => (
            <QuestionCard key={q.id} question={q} onDelete={handleDelete} />
          ))}
        </div>
      </div>

      {showAdd && (
        <AddQuestionModal onClose={() => setShowAdd(false)} onSave={handleSave} />
      )}
    </div>
  );
};

export default QuestionBankPage;
