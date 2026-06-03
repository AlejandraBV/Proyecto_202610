import React, { useState, useRef } from 'react';
import { Send, Plus, Loader, Upload, Link, FileText, X, Paperclip, BookOpen } from 'lucide-react';
import { useDocuments } from '@/hooks/useApi';
import { useAppStore } from '@/store/appStore';
import { DocumentUploadRequest, DetectedMetadata } from '@/types';
import { translations, t } from '@/lib/translations';
import { apiClient } from '@/lib/api';
import toast from 'react-hot-toast';

export interface PendingDocument {
  id: string;
  filename: string;
}

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  loading?: boolean;
  /** Document that was just uploaded and will be attached to the next message */
  pendingDocument?: PendingDocument | null;
  /** Called when a document finishes uploading — pass id + filename up to parent */
  onDocumentUploaded?: (doc: PendingDocument) => void;
  /** Called when the user removes the pending document attachment */
  onClearDocument?: () => void;
  /** Auto-detected topic metadata returned by the backend after the last send */
  detectedMetadata?: DetectedMetadata | null;
}

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File, request: DocumentUploadRequest) => Promise<void>;
  onUrlUpload: (url: string, request: DocumentUploadRequest) => Promise<void>;
}

const UploadModal: React.FC<UploadModalProps> = ({ isOpen, onClose, onUpload, onUrlUpload }) => {
  const language = useAppStore((s) => s.language);
  const TM = (entry: { en: string; es: string }) => t(entry, language);
  const [uploadType, setUploadType] = useState<'file' | 'url'>('file');
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const request: DocumentUploadRequest = {
      subject: subject.trim() || undefined,
      description: description.trim() || undefined,
    };

    try {
      setUploading(true);
      if (uploadType === 'file' && file) {
        await onUpload(file, request);
      } else if (uploadType === 'url' && url) {
        await onUrlUpload(url, request);
      }
      onClose();
      setFile(null);
      setUrl('');
      setSubject('');
      setDescription('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch {
      // Error already handled in hook / parent
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">{TM(translations.uploadModal.title)}</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex gap-2 mb-4">
          <button
            type="button"
            onClick={() => setUploadType('file')}
            className={`flex-1 py-2 px-3 rounded ${uploadType === 'file' ? 'bg-indigo-600 text-white' : 'bg-gray-100'}`}
          >
            <FileText className="inline w-4 h-4 mr-1" />
            {TM(translations.uploadModal.file)}
          </button>
          <button
            type="button"
            onClick={() => setUploadType('url')}
            className={`flex-1 py-2 px-3 rounded ${uploadType === 'url' ? 'bg-indigo-600 text-white' : 'bg-gray-100'}`}
          >
            <Link className="inline w-4 h-4 mr-1" />
            {TM(translations.uploadModal.url)}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {uploadType === 'file' ? (
            <div>
              <label className="block text-sm font-medium mb-1">{TM(translations.uploadModal.selectFile)}</label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full p-2 border border-gray-300 rounded"
                required
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium mb-1">URL</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/document.pdf"
                className="w-full p-2 border border-gray-300 rounded"
                required
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">
              {TM(translations.uploadModal.subject)}{' '}
              <span className="text-gray-400 font-normal text-xs">{TM(translations.uploadModal.subjectHint)}</span>
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder={TM(translations.uploadModal.subjectPlaceholder)}
              className="w-full p-2 border border-gray-300 rounded"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 px-4 border border-gray-300 rounded hover:bg-gray-50"
            >
              {TM(translations.uploadModal.cancel)}
            </button>
            <button
              type="submit"
              disabled={uploading || (uploadType === 'file' && !file) || (uploadType === 'url' && !url)}
              className="flex-1 py-2 px-4 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:bg-gray-300"
            >
              {uploading ? <Loader className="inline w-4 h-4 animate-spin mr-1" /> : <Upload className="inline w-4 h-4 mr-1" />}
              {uploading ? TM(translations.uploadModal.uploading) : TM(translations.uploadModal.upload)}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ── Syllabus form modal ───────────────────────────────────────────────────────

interface SyllabusModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploaded: (doc: PendingDocument) => void;
}

const SyllabusModal: React.FC<SyllabusModalProps> = ({ isOpen, onClose, onUploaded }) => {
  const language = useAppStore((s) => s.language);
  const TM = (entry: { en: string; es: string }) => t(entry, language);

  const [courseName, setCourseName] = useState('');
  const [subject, setSubject] = useState('');
  const [week, setWeek] = useState('');
  const [objectives, setObjectives] = useState<string[]>(['']);
  const [topics, setTopics] = useState<Array<{ name: string; bloom_level: string }>>([
    { name: '', bloom_level: '' },
  ]);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  if (!isOpen) return null;

  const addObjective = () => setObjectives((o) => [...o, '']);
  const setObj = (i: number, v: string) =>
    setObjectives((o) => o.map((x, j) => (j === i ? v : x)));
  const removeObj = (i: number) => setObjectives((o) => o.filter((_, j) => j !== i));

  const addTopic = () => setTopics((t) => [...t, { name: '', bloom_level: '' }]);
  const setTopicField = (i: number, field: 'name' | 'bloom_level', v: string) =>
    setTopics((ts) => ts.map((t, j) => (j === i ? { ...t, [field]: v } : t)));
  const removeTopic = (i: number) => setTopics((ts) => ts.filter((_, j) => j !== i));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!courseName.trim() || !subject.trim()) return;
    setSaving(true);
    try {
      const res = await apiClient.uploadSyllabus({
        course_name: courseName.trim(),
        subject: subject.trim(),
        week: week ? parseInt(week, 10) : undefined,
        learning_objectives: objectives.filter((o) => o.trim()),
        topics: topics.filter((t) => t.name.trim()).map((t) => ({
          name: t.name.trim(),
          bloom_level: t.bloom_level || undefined,
        })),
        notes: notes.trim() || undefined,
      });
      const data = (res as any).data;
      onUploaded({ id: data.document_id, filename: `Syllabus: ${courseName}` });
      toast.success(`Syllabus "${courseName}" added as RAG context!`);
      onClose();
    } catch {
      toast.error('Could not upload syllabus');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto py-4">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-600" />
            Course Syllabus
          </h3>
          <button onClick={onClose}><X className="h-5 w-5 text-gray-400 hover:text-gray-600" /></button>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          Enter your course outline. It will be indexed as RAG context for smarter content generation.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Course name *</label>
              <input
                value={courseName}
                onChange={(e) => setCourseName(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g. Introduction to Biology"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Subject *</label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g. Biology"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Week (optional)</label>
            <input
              type="number"
              value={week}
              onChange={(e) => setWeek(e.target.value)}
              min={1}
              className="w-24 rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="e.g. 3"
            />
          </div>

          {/* Learning objectives */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-gray-600">Learning objectives</label>
              <button type="button" onClick={addObjective} className="text-xs text-indigo-600 hover:underline">+ Add</button>
            </div>
            {objectives.map((obj, i) => (
              <div key={i} className="flex gap-2 mb-1">
                <input
                  value={obj}
                  onChange={(e) => setObj(i, e.target.value)}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
                  placeholder="e.g. Understand cell division mechanisms"
                />
                {objectives.length > 1 && (
                  <button type="button" onClick={() => removeObj(i)} className="text-gray-400 hover:text-red-500">
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Topics */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-gray-600">Topics covered</label>
              <button type="button" onClick={addTopic} className="text-xs text-indigo-600 hover:underline">+ Add</button>
            </div>
            {topics.map((topic, i) => (
              <div key={i} className="flex gap-2 mb-1">
                <input
                  value={topic.name}
                  onChange={(e) => setTopicField(i, 'name', e.target.value)}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
                  placeholder="Topic name"
                />
                <select
                  value={topic.bloom_level}
                  onChange={(e) => setTopicField(i, 'bloom_level', e.target.value)}
                  className="w-32 rounded-lg border border-gray-300 px-2 py-1.5 text-xs"
                >
                  <option value="">Bloom level</option>
                  {['Remember','Understand','Apply','Analyze','Evaluate','Create'].map((l) => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
                {topics.length > 1 && (
                  <button type="button" onClick={() => removeTopic(i)} className="text-gray-400 hover:text-red-500">
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="Additional context or emphasis for content generation…"
            />
          </div>

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-gray-300 py-2 text-sm hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !courseName.trim() || !subject.trim()}
              className="flex-1 rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? <Loader className="inline h-4 w-4 animate-spin mr-1" /> : <Upload className="inline h-4 w-4 mr-1" />}
              {saving ? 'Uploading…' : 'Add as Context'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────

export const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSubmit,
  disabled = false,
  loading = false,
  pendingDocument,
  onDocumentUploaded,
  onClearDocument,
  detectedMetadata,
}) => {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showSyllabusModal, setShowSyllabusModal] = useState(false);
  const { uploadDocument, uploadFromUrl } = useDocuments();
  const language = useAppStore((s) => s.language);
  const T = (entry: { en: string; es: string }) => t(entry, language);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter alone → send; Shift+Enter → new line (default textarea behaviour)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && !loading && value.trim()) {
        onSubmit();
      }
    }
  };

  const handleFileUpload = async (file: File, request: DocumentUploadRequest) => {
    const result = await uploadDocument(file, request);
    if (result?.id) {
      onDocumentUploaded?.({ id: result.id, filename: file.name });
      toast.success(
        `"${file.name}" attached — now type your prompt and send!`,
        { duration: 5000 }
      );
    }
  };

  const handleUrlUpload = async (url: string, request: DocumentUploadRequest) => {
    const result = await uploadFromUrl(url, request);
    const shortName = url.split('/').pop() || url;
    if (result?.id) {
      onDocumentUploaded?.({ id: result.id, filename: shortName });
      toast.success(
        `URL document attached — now type your prompt and send!`,
        { duration: 5000 }
      );
    }
  };

  return (
    <>
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="mx-auto max-w-4xl">

          {/* Attached document chip */}
          {pendingDocument && (
            <div className="mb-2 flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 w-fit max-w-full">
              <Paperclip className="h-4 w-4 flex-shrink-0 text-blue-500" />
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-semibold text-blue-500 uppercase tracking-wide leading-none mb-0.5">
                  Document attached
                </span>
                <span className="truncate max-w-xs font-medium leading-tight" title={pendingDocument.filename}>
                  {pendingDocument.filename}
                </span>
              </div>
              <button
                onClick={onClearDocument}
                className="ml-1 text-blue-400 hover:text-red-500 flex-shrink-0 transition-colors"
                title="Remove attachment"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => setShowUploadModal(true)}
              className="flex items-center justify-center rounded-lg p-2 hover:bg-gray-100 transition-colors"
              title="Upload document for RAG"
            >
              <Plus className="h-5 w-5 text-gray-500" />
            </button>
            <button
              onClick={() => setShowSyllabusModal(true)}
              className="flex items-center justify-center rounded-lg p-2 hover:bg-gray-100 transition-colors"
              title="Add course syllabus as RAG context"
            >
              <BookOpen className="h-5 w-5 text-gray-500" />
            </button>

            <div className="flex-1 flex gap-2">
              <div className="flex-1 relative">
                <textarea
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    pendingDocument
                      ? `${language === 'es' ? 'Pídeme generar contenido de' : 'Ask me to generate content from'} "${pendingDocument.filename}"… ${T(translations.chatInput.placeholderDoc)}`
                      : T(translations.chatInput.placeholder)
                  }
                  disabled={disabled || loading}
                  rows={3}
                  className="w-full resize-none rounded-lg border border-gray-300 bg-white p-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:bg-gray-50 disabled:text-gray-500"
                />
              </div>

              <button
                onClick={onSubmit}
                disabled={disabled || loading || !value.trim()}
                className="flex items-center justify-center rounded-lg bg-primary px-4 py-3 text-white hover:bg-primary/90 disabled:bg-gray-300 transition-colors"
                aria-label="Send message"
              >
                {loading ? (
                  <Loader className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>

          <p className="mt-2 text-center text-xs text-gray-500">
            {T(translations.chatInput.uploadHint)}
          </p>

          {/* Auto-detected metadata badge */}
          {detectedMetadata && (detectedMetadata.subject || detectedMetadata.topic) && (
            <div className="mt-2 flex items-center justify-center gap-1 text-xs text-primary">
              <span>📚</span>
              {detectedMetadata.subject && <span>{detectedMetadata.subject}</span>}
              {detectedMetadata.subject && detectedMetadata.topic && <span>•</span>}
              {detectedMetadata.topic && <span>{detectedMetadata.topic}</span>}
              {detectedMetadata.contentType && (
                <>
                  <span>•</span>
                  <span className="capitalize">{detectedMetadata.contentType}</span>
                </>
              )}
              {detectedMetadata.detectionMethod && (
                <span className="ml-1 text-gray-400">
                  (via {detectedMetadata.detectionMethod})
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleFileUpload}
        onUrlUpload={handleUrlUpload}
      />

      <SyllabusModal
        isOpen={showSyllabusModal}
        onClose={() => setShowSyllabusModal(false)}
        onUploaded={(doc) => {
          onDocumentUploaded?.(doc);
          setShowSyllabusModal(false);
        }}
      />
    </>
  );
};
