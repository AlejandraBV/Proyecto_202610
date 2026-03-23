import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { GeneratedContent } from '@/types';

interface ContentEditorProps {
  content: GeneratedContent;
  onSave?: (updatedContent: string) => Promise<void>;
  readOnly?: boolean;
}

/**
 * Inline editor for generated academic content.
 * Toggles between a live markdown preview and a plain-text editing mode.
 */
export const ContentEditor: React.FC<ContentEditorProps> = ({
  content,
  onSave,
  readOnly = false,
}) => {
  const [editMode, setEditMode] = useState(false);
  const [text, setText] = useState(content.content);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    if (!onSave) return;
    setIsSaving(true);
    try {
      await onSave(text);
      setEditMode(false);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      {!readOnly && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setEditMode(!editMode)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 transition-colors"
          >
            {editMode ? '👁 Preview' : '✏️ Edit'}
          </button>
          {editMode && onSave && (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {isSaving ? 'Saving…' : 'Save'}
            </button>
          )}
          {editMode && (
            <button
              onClick={() => { setText(content.content); setEditMode(false); }}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      )}

      {/* Editor / Preview */}
      {editMode ? (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={20}
          className="w-full rounded-lg border border-gray-300 p-4 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      ) : (
        <div className="prose prose-sm max-w-none rounded-lg border border-gray-200 bg-white p-6">
          <ReactMarkdown>{text}</ReactMarkdown>
        </div>
      )}
    </div>
  );
};
