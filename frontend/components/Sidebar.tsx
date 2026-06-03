import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { ConversationThread, Folder } from '@/types';
import {
  Trash2, Clock, ChevronDown, ChevronRight,
  FolderPlus, Folder as FolderIcon,
  MoreHorizontal, X, Check, LogOut, Moon, Sun, Pencil, Languages, Tag,
  History, BarChart2, BookmarkPlus,
} from 'lucide-react';
import { format, isToday, isThisWeek } from 'date-fns';
import { useAppStore } from '@/store/appStore';
import { useT } from '@/hooks/useT';
import { useSubject } from '@/hooks/useSubject';
import { tr } from '@/lib/translations';
import { apiClient } from '@/lib/api';
import toast from 'react-hot-toast';

interface SidebarProps {
  conversations: ConversationThread[];
  folders?: Folder[];
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onNewConversation: () => void;
  onCreateFolder?: (name: string, color?: string) => Promise<void>;
  onDeleteFolder?: (folderId: string) => Promise<void>;
  onUpdateFolder?: (folderId: string, data: { color?: string }) => Promise<void>;
  onMoveConversation?: (conversationId: string, folderId: string | null) => Promise<void>;
  /**
   * Called after a successful reclassification so the parent can update its
   * conversations state without a full re-fetch.
   * Args: (conversationId, newSubject, newFolderId | null, newTitle)
   */
  onReclassify?: (convId: string, newSubject: string, folderId: string | null, newTitle: string) => void;
  loading?: boolean;
}

const FOLDER_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
  '#8B5CF6', '#EC4899', '#06B6D4', '#6366F1', '#64748B',
];

/** Returns an emoji that represents the academic subject */
function getSubjectEmoji(subject?: string | null): string {
  const emojiMap: Record<string, string> = {
    Biology: '🧬',
    History: '📚',
    Mathematics: '🔢',
    Chemistry: '⚗️',
    Physics: '⚛️',
    Literature: '📖',
    Geography: '🌍',
    Economics: '📈',
    General: '💡',
  };
  return emojiMap[subject || 'General'] || '📝';
}

/** Format a timestamp: time if today, day+time if this week, date otherwise.
 *  Backend returns UTC strings without a trailing 'Z'; append it so JS parses
 *  them correctly as UTC instead of local time. */
function formatTimestamp(dateStr: string): string {
  try {
    // Ensure we parse as UTC — backend omits the trailing 'Z'
    const utcStr =
      dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z';
    const d = new Date(utcStr);
    if (isToday(d)) return format(d, 'h:mm a');
    if (isThisWeek(d)) return format(d, 'EEE h:mm a');
    return format(d, 'MMM d');
  } catch {
    return '';
  }
}

// ── User menu (profile / logout / dark mode / language) ──────────────────────

const UserMenu: React.FC = () => {
  const router = useRouter();
  const T = useT();
  const { currentUser, darkMode, setDarkMode, language, setLanguage } = useAppStore();
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('token');
    // Keep darkMode and language preferences across sessions (user chose them intentionally)
    router.push('/login');
  };

  // Derive initials from name or email
  const initials = currentUser?.name
    ? currentUser.name
        .split(' ')
        .map((n: string) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : (currentUser?.email?.[0]?.toUpperCase() ?? '?');

  const displayName = currentUser?.name || 'User';
  const displayEmail = currentUser?.email || '';

  return (
    <div className="relative">
      {/* Popup menu — renders above the trigger */}
      {open && (
        <>
          {/* Invisible backdrop to close on click-outside */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />

          <div className="absolute bottom-14 left-2 right-2 z-20 rounded-xl border border-gray-200 bg-white shadow-xl overflow-hidden">
            {/* User info header */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 border-b border-gray-100">
              <div className="flex items-center gap-2.5">
                <div className="h-9 w-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0 shadow-sm">
                  {initials}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-900 truncate">{displayName}</p>
                  <p className="text-xs text-gray-500 truncate">{displayEmail}</p>
                </div>
              </div>
              {currentUser && (
                <div className="mt-2 flex items-center gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                    {T(tr.sidebar.loggedIn)}
                  </span>
                </div>
              )}
            </div>

            {/* Menu items */}
            <div className="py-1">
              {/* Dark mode toggle */}
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {darkMode
                  ? <Sun className="h-4 w-4 text-amber-500" />
                  : <Moon className="h-4 w-4 text-indigo-500" />}
                <span>{darkMode ? T(tr.sidebar.toLightMode) : T(tr.sidebar.toDarkMode)}</span>
              </button>

              {/* Language toggle */}
              <div className="flex items-center gap-2.5 px-4 py-2 text-sm text-gray-700">
                <Languages className="h-4 w-4 text-indigo-400 flex-shrink-0" />
                <span className="flex-1">{T(tr.sidebar.language)}</span>
                <div className="flex rounded border border-gray-200 overflow-hidden text-xs">
                  <button
                    onClick={() => setLanguage('en')}
                    className={`px-2 py-1 font-medium transition-colors ${
                      language === 'en' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    EN
                  </button>
                  <button
                    onClick={() => setLanguage('es')}
                    className={`px-2 py-1 font-medium transition-colors border-l border-gray-200 ${
                      language === 'es' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    ES
                  </button>
                </div>
              </div>
            </div>

            <div className="border-t border-gray-100 py-1">
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                {T(tr.sidebar.logOut)}
              </button>
            </div>
          </div>
        </>
      )}

      {/* Trigger row */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2.5 px-3 py-3 hover:bg-gray-50 transition-colors text-left"
      >
        <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 shadow-sm">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-800 truncate">{displayName}</p>
          <p className="text-xs text-gray-500 truncate">{displayEmail || 'Powered by Gemini'}</p>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-gray-400 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
    </div>
  );
};

// ── Conversation item ─────────────────────────────────────────────────────────

interface ConversationItemProps {
  conv: ConversationThread;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  folders: Folder[];
  onMove: (folderId: string | null) => void;
  /** Optional: parent receives corrected subject/folder so it can update state */
  onReclassify?: (convId: string, newSubject: string, folderId: string | null, newTitle: string) => void;
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conv, isActive, onSelect, onDelete, folders, onMove, onReclassify,
}) => {
  const T = useT();
  const ts = useSubject();
  const [showMenu, setShowMenu] = useState(false);
  const [showReclassify, setShowReclassify] = useState(false);
  const [reclassifyInput, setReclassifyInput] = useState('');
  const [reclassifySaving, setReclassifySaving] = useState(false);

  const subject = conv.primarySubject || conv.subject;
  const topic = conv.primaryTopic || conv.topic;
  // Build the display title from translated subject + original topic
  const displayTitle = subject && topic
    ? `${ts(subject)} - ${topic}`
    : ts(subject || '') || topic || conv.title;

  const handleOpenReclassify = () => {
    setReclassifyInput(subject || '');
    setShowReclassify(true);
    setShowMenu(false);
  };

  const handleReclassify = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = reclassifyInput.trim();
    if (!trimmed) return;
    setReclassifySaving(true);
    try {
      const response = await apiClient.reclassifyConversation(conv.id, trimmed);
      const { new_subject, folder_id, title } = response.data as any;
      toast.success(T(tr.hitl.saved));
      onReclassify?.(conv.id, new_subject, folder_id ?? null, title);
      setShowReclassify(false);
    } catch {
      toast.error(T(tr.hitl.error));
    } finally {
      setReclassifySaving(false);
    }
  };

  return (
    <div
      className={`group relative rounded-lg px-3 py-2 cursor-pointer transition-colors ${
        isActive ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50'
      }`}
    >
      <div onClick={!showReclassify ? onSelect : undefined} className="flex items-start gap-2 min-w-0">
        <span className="text-base flex-shrink-0 mt-0.5" aria-label={subject || 'General'}>
          {getSubjectEmoji(subject)}
        </span>
        <div className="min-w-0 flex-1">
          <p className={`truncate text-sm font-medium ${isActive ? 'text-blue-800' : 'text-gray-800'}`}>
            {displayTitle}
          </p>
          {topic && topic !== 'Untitled' && (
            <p className="truncate text-xs text-blue-600 font-medium">{topic}</p>
          )}
          <div className="flex items-center gap-1 mt-0.5 text-xs text-gray-400">
            <Clock className="h-3 w-3" />
            {formatTimestamp(conv.updatedAt)}
          </div>
        </div>

        {/* Context menu button */}
        {!showReclassify && (
          <button
            onClick={(e) => { e.stopPropagation(); setShowMenu((v) => !v); }}
            className="flex-shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-200 transition-opacity"
          >
            <MoreHorizontal className="h-3.5 w-3.5 text-gray-500" />
          </button>
        )}
      </div>

      {/* Inline reclassify form */}
      {showReclassify && (
        <form
          onSubmit={handleReclassify}
          onClick={(e) => e.stopPropagation()}
          className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-2 space-y-1.5"
        >
          <p className="text-xs font-medium text-amber-800">{T(tr.hitl.reclassifyHint)}</p>
          {subject && (
            <p className="text-xs text-amber-600">
              {T(tr.hitl.wasClassifiedAs)} <span className="font-semibold">{ts(subject)}</span>
            </p>
          )}
          <input
            autoFocus
            value={reclassifyInput}
            onChange={(e) => setReclassifyInput(e.target.value)}
            placeholder={T(tr.hitl.subjectPlaceholder)}
            className="w-full rounded border border-amber-300 bg-white px-2 py-1 text-xs focus:border-amber-500 focus:outline-none"
          />
          <div className="flex gap-1.5">
            <button
              type="submit"
              disabled={reclassifySaving || !reclassifyInput.trim()}
              className="flex-1 rounded bg-amber-600 px-2 py-1 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
            >
              {reclassifySaving ? '…' : T(tr.hitl.save)}
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setShowReclassify(false); }}
              className="rounded border border-gray-300 bg-white px-2 py-1 text-xs text-gray-600 hover:bg-gray-100"
            >
              {T(tr.hitl.cancel)}
            </button>
          </div>
        </form>
      )}

      {/* Context dropdown */}
      {showMenu && !showReclassify && (
        <div
          className="absolute right-0 top-8 z-20 w-48 rounded-md bg-white shadow-lg border border-gray-200 py-1"
          onMouseLeave={() => setShowMenu(false)}
        >
          {/* HITL: correct subject */}
          <button
            onClick={(e) => { e.stopPropagation(); handleOpenReclassify(); }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-amber-700 hover:bg-amber-50"
          >
            <Tag className="h-3.5 w-3.5" />
            {T(tr.sidebar.correctSubject)}
          </button>

          <div className="border-t border-gray-100 my-1" />

          <p className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide">{T(tr.sidebar.moveTo)}</p>
          <button
            onClick={() => { onMove(null); setShowMenu(false); }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            <FolderIcon className="h-3.5 w-3.5 text-gray-400" />
            {T(tr.sidebar.uncategorized)}
          </button>
          {folders.map((f) => (
            <button
              key={f.id}
              onClick={() => { onMove(f.id); setShowMenu(false); }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              <span
                className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: f.color }}
              />
              {ts(f.name)}
            </button>
          ))}
          <div className="border-t border-gray-100 mt-1 pt-1">
            <button
              onClick={() => { onDelete(); setShowMenu(false); }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {T(tr.sidebar.deleteChat)}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ── New folder form ───────────────────────────────────────────────────────────

interface NewFolderFormProps {
  onSubmit: (name: string, color: string) => Promise<void>;
  onCancel: () => void;
}

const NewFolderForm: React.FC<NewFolderFormProps> = ({ onSubmit, onCancel }) => {
  const T = useT();
  const [name, setName] = useState('');
  const [color, setColor] = useState(FOLDER_COLORS[0]);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSubmit(name.trim(), color);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-2 mb-2 rounded-lg border border-blue-200 bg-blue-50 p-2">
      <input
        autoFocus
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder={T(tr.sidebar.folderNamePlaceholder)}
        className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
      />
      <div className="mt-2 flex gap-1 flex-wrap">
        {FOLDER_COLORS.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setColor(c)}
            className={`h-5 w-5 rounded-full border-2 transition-all ${
              color === c ? 'border-gray-700 scale-110' : 'border-transparent'
            }`}
            style={{ backgroundColor: c }}
          />
        ))}
      </div>
      <div className="mt-2 flex gap-1">
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="flex-1 rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:bg-gray-300"
        >
          <Check className="inline h-3 w-3 mr-1" />
          {saving ? T(tr.sidebar.creating) : T(tr.sidebar.create)}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-100"
        >
          <X className="inline h-3 w-3" />
        </button>
      </div>
    </form>
  );
};

// ── Folder section ────────────────────────────────────────────────────────────

interface FolderSectionProps {
  folder: Folder | null; // null = "Uncategorized"
  conversations: ConversationThread[];
  currentConversationId: string | null;
  allFolders: Folder[];
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onMoveConversation: (conversationId: string, folderId: string | null) => Promise<void>;
  onDeleteFolder?: (folderId: string) => Promise<void>;
  onUpdateFolder?: (folderId: string, data: { color?: string }) => Promise<void>;
  onReclassify?: (convId: string, newSubject: string, folderId: string | null, newTitle: string) => void;
  defaultOpen?: boolean;
}

const FolderSection: React.FC<FolderSectionProps> = ({
  folder,
  conversations,
  currentConversationId,
  allFolders,
  onSelectConversation,
  onDeleteConversation,
  onMoveConversation,
  onDeleteFolder,
  onUpdateFolder,
  onReclassify,
  defaultOpen = true,
}) => {
  const T = useT();
  const ts = useSubject();
  const [open, setOpen] = useState(defaultOpen);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editingColor, setEditingColor] = useState(false);

  // Folder names are stored as English subject names in the DB — translate for display
  const name = folder ? ts(folder.name) : T(tr.sidebar.uncategorized);
  const color = folder?.color ?? '#94A3B8';
  const count = conversations.length;

  // Only hide the "Uncategorized" pseudo-folder when it's empty; always show real folders.
  if (count === 0 && !folder) return null;

  return (
    <div className="mb-1">
      {/* Folder header */}
      <div
        className="group flex items-center gap-1.5 rounded-md px-2 py-1.5 cursor-pointer hover:bg-gray-100 select-none"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-gray-400 flex-shrink-0">
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </span>
        {folder ? (
          <span
            className="h-3 w-3 rounded-sm flex-shrink-0"
            style={{ backgroundColor: color }}
          />
        ) : (
          <FolderIcon className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
        )}
        <span className="flex-1 truncate text-xs font-semibold text-gray-600 uppercase tracking-wide">
          {name}
        </span>
        <span className="text-xs text-gray-400 flex-shrink-0">{count}</span>

        {folder && onUpdateFolder && (
          <button
            onClick={(e) => { e.stopPropagation(); setEditingColor((v) => !v); }}
            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-blue-100 transition-opacity"
            title="Change color"
          >
            <Pencil className="h-3 w-3 text-blue-400" />
          </button>
        )}
        {folder && onDeleteFolder && (
          <button
            onClick={(e) => { e.stopPropagation(); setConfirmDelete(true); }}
            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-100 transition-opacity"
            title="Delete folder"
          >
            <Trash2 className="h-3 w-3 text-red-400" />
          </button>
        )}
      </div>

      {/* Edit color palette */}
      {editingColor && folder && (
        <div className="mx-2 mb-1 rounded border border-blue-200 bg-blue-50 p-2">
          <p className="mb-1.5 text-xs font-medium text-blue-700">{T(tr.sidebar.chooseColor)}</p>
          <div className="flex gap-1.5 flex-wrap">
            {FOLDER_COLORS.map((c) => (
              <button
                key={c}
                onClick={async () => {
                  await onUpdateFolder!(folder.id, { color: c });
                  setEditingColor(false);
                }}
                className={`h-5 w-5 rounded-full border-2 transition-all hover:scale-110 ${
                  folder.color === c ? 'border-gray-700 scale-110' : 'border-transparent'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
          <button
            onClick={() => setEditingColor(false)}
            className="mt-1.5 text-xs text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Delete folder confirmation */}
      {confirmDelete && folder && (
        <div className="mx-2 mb-1 rounded border border-red-200 bg-red-50 p-2 text-xs">
          <p className="text-red-700 mb-2">{T(tr.sidebar.deleteFolderConfirm).replace('folder', `"${ts(folder!.name)}"`)}</p>
          <div className="flex gap-1">
            <button
              onClick={async () => { await onDeleteFolder!(folder.id); setConfirmDelete(false); }}
              className="flex-1 rounded bg-red-600 px-2 py-1 text-white hover:bg-red-700"
            >{T(tr.sidebar.delete)}</button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="rounded px-2 py-1 text-gray-600 hover:bg-gray-100"
            >{T(tr.sidebar.cancel)}</button>
          </div>
        </div>
      )}

      {/* Conversations list */}
      {open && (
        <div className="ml-4 space-y-0.5">
          {conversations.map((conv) => (
            <ConversationItem
              key={conv.id}
              conv={conv}
              isActive={currentConversationId === conv.id}
              onSelect={() => onSelectConversation(conv.id)}
              onDelete={() => onDeleteConversation(conv.id)}
              folders={allFolders}
              onMove={(folderId) => onMoveConversation(conv.id, folderId)}
              onReclassify={onReclassify}
            />
          ))}
          {conversations.length === 0 && (
            <p className="px-3 py-2 text-xs text-gray-400 italic">{T(tr.sidebar.noChats)}</p>
          )}
        </div>
      )}
    </div>
  );
};

// ── Main Sidebar ──────────────────────────────────────────────────────────────

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  folders = [],
  currentConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewConversation,
  onCreateFolder,
  onDeleteFolder,
  onUpdateFolder,
  onMoveConversation = async () => {},
  onReclassify,
  loading = false,
}) => {
  const T = useT();
  const [showNewFolder, setShowNewFolder] = useState(false);

  // Group conversations by folder_id
  const grouped: Record<string, ConversationThread[]> = {};
  const uncategorized: ConversationThread[] = [];

  conversations.forEach((conv) => {
    if (conv.folderId) {
      if (!grouped[conv.folderId]) grouped[conv.folderId] = [];
      grouped[conv.folderId].push(conv);
    } else {
      uncategorized.push(conv);
    }
  });

  return (
    <div className="flex h-screen w-64 flex-col border-r border-gray-200 bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 p-3 space-y-2">
        <button
          onClick={onNewConversation}
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 transition-colors flex items-center justify-center gap-2"
        >
          <span className="text-base leading-none">+</span>
          {T(tr.sidebar.newChat)}
        </button>

        {onCreateFolder && (
          <button
            onClick={() => setShowNewFolder(true)}
            className="w-full rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors flex items-center justify-center gap-1.5"
          >
            <FolderPlus className="h-3.5 w-3.5" />
            {T(tr.sidebar.newFolder)}
          </button>
        )}
      </div>

      {/* New folder form */}
      {showNewFolder && (
        <div className="border-b border-gray-200 py-2">
          <NewFolderForm
            onSubmit={async (name, color) => {
              await onCreateFolder!(name, color);
              setShowNewFolder(false);
            }}
            onCancel={() => setShowNewFolder(false)}
          />
        </div>
      )}

      {/* Conversations grouped by folder */}
      <div className="flex-1 overflow-y-auto py-2 px-1">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            <p className="text-2xl mb-2">💬</p>
            <p>{T(tr.sidebar.noConversations)}</p>
            <p className="text-xs mt-1">{T(tr.sidebar.noConvsHint)}</p>
          </div>
        ) : (
          <>
            {/* Folders with their conversations */}
            {folders.map((folder) => (
              <FolderSection
                key={folder.id}
                folder={folder}
                conversations={grouped[folder.id] || []}
                currentConversationId={currentConversationId}
                allFolders={folders}
                onSelectConversation={onSelectConversation}
                onDeleteConversation={onDeleteConversation}
                onMoveConversation={onMoveConversation}
                onDeleteFolder={onDeleteFolder}
                onUpdateFolder={onUpdateFolder}
                onReclassify={onReclassify}
                defaultOpen={true}
              />
            ))}

            {/* Uncategorized conversations */}
            <FolderSection
              folder={null}
              conversations={uncategorized}
              currentConversationId={currentConversationId}
              allFolders={folders}
              onSelectConversation={onSelectConversation}
              onDeleteConversation={onDeleteConversation}
              onMoveConversation={onMoveConversation}
              onReclassify={onReclassify}
              defaultOpen={true}
            />
          </>
        )}
      </div>

      {/* Quick-access nav links */}
      <div className="border-t border-gray-100 px-2 py-2 space-y-0.5">
        <Link href="/history" className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 transition-colors">
          <History className="h-3.5 w-3.5 text-indigo-500" />
          Audit Trail
        </Link>
        <Link href="/evaluation" className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 transition-colors">
          <BarChart2 className="h-3.5 w-3.5 text-emerald-500" />
          Evaluation
        </Link>
        <Link href="/question-bank" className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 transition-colors">
          <BookmarkPlus className="h-3.5 w-3.5 text-amber-500" />
          Question Bank
        </Link>
      </div>

      {/* User profile footer */}
      <div className="border-t border-gray-200">
        <UserMenu />
      </div>
    </div>
  );
};
