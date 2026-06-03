/**
 * /settings - User profile and application settings page.
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Globe, Moon, Sun } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { Sidebar } from '@/components/Sidebar';
import { useAppStore } from '@/store/appStore';
import { useConversations } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { useT } from '@/hooks/useT';
import { tr } from '@/lib/translations';
import toast from 'react-hot-toast';

const SettingsPage: React.FC = () => {
  const router = useRouter();
  const {
    conversations,
    currentConversation,
    currentUser,
    setCurrentUser,
    setConversations,
    setCurrentConversation,
    language,
    setLanguage,
    darkMode,
    setDarkMode,
  } = useAppStore();
  const { fetchConversations } = useConversations();

  const T = useT();

  const [name, setName] = useState(currentUser?.name || '');
  const [institution, setInstitution] = useState(currentUser?.institution || '');
  const [subject, setSubject] = useState(currentUser?.subject || '');
  const [level, setLevel] = useState(currentUser?.level || 'university');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchConversations();
    if (currentUser) {
      setName(currentUser.name || '');
      setInstitution(currentUser.institution || '');
      setSubject(currentUser.subject || '');
      setLevel(currentUser.level || 'university');
    }
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      setCurrentUser({ ...currentUser, name, institution, subject, level });
      toast.success(T(tr.settings.savedOk));
    } catch {
      toast.error(T(tr.settings.savedErr));
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
    setCurrentUser(null);
    router.push('/login');
  };

  return (
    <Layout
      sidebar={
        <Sidebar
          conversations={conversations}
          currentConversationId={currentConversation?.id || null}
          onSelectConversation={(id) => {
            const conv = conversations.find((c) => c.id === id);
            setCurrentConversation(conv || null);
            router.push('/');
          }}
          onDeleteConversation={async (id) => {
            try {
              await apiClient.deleteConversation(id);
              setConversations(conversations.filter((c) => c.id !== id));
              if (currentConversation?.id === id) setCurrentConversation(null);
              toast.success(T(tr.settings.convDeleted));
            } catch {
              toast.error(T(tr.settings.convDeleteErr));
            }
          }}
          onNewConversation={() => router.push('/')}
        />
      }
    >
      <div className="flex h-full flex-col overflow-y-auto p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900">
          {T(tr.settings.title)}
        </h1>

        {/* ── Profile section ──────────────────────────────────────────── */}
        <h2 className="mb-4 text-base font-semibold text-gray-700 uppercase tracking-wide">
          {T(tr.settings.profile)}
        </h2>

        <form onSubmit={handleSave} className="max-w-lg space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {T(tr.settings.fullName)}
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {T(tr.settings.institution)}
            </label>
            <input
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {T(tr.settings.defaultSubject)}
            </label>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder={T(tr.settings.subjectPlaceholder)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {T(tr.settings.defaultLevel)}
            </label>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="elementary">{T(tr.settings.elementary)}</option>
              <option value="secondary">{T(tr.settings.secondary)}</option>
              <option value="university">{T(tr.settings.university)}</option>
              <option value="professional">{T(tr.settings.professional)}</option>
            </select>
          </div>

          <div className="flex items-center gap-4 pt-2">
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {isSaving ? T(tr.settings.saving) : T(tr.settings.saveChanges)}
            </button>

            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
            >
              {T(tr.settings.logout)}
            </button>
          </div>
        </form>

        {/* ── Preferences section ───────────────────────────────────────── */}
        <div className="mt-10 max-w-lg">
          <h2 className="mb-4 text-base font-semibold text-gray-700 uppercase tracking-wide">
            {T(tr.settings.preferences)}
          </h2>

          {/* Dark mode toggle */}
          <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 mb-3">
            <div className="flex items-center gap-2">
              {darkMode
                ? <Sun className="h-4 w-4 text-amber-500" />
                : <Moon className="h-4 w-4 text-indigo-500" />}
              <span className="text-sm font-medium text-gray-700">
                {darkMode ? T(tr.settings.darkMode) : T(tr.settings.lightMode)}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setDarkMode(!darkMode)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                darkMode ? 'bg-indigo-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                  darkMode ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Language toggle */}
          <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">
                {T(tr.settings.language)}
              </span>
            </div>

            <div className="flex rounded-lg border border-gray-300 overflow-hidden">
              <button
                type="button"
                onClick={() => setLanguage('en')}
                className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                  language === 'en'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
              >
                🇬🇧 {T(tr.settings.langEn)}
              </button>
              <button
                type="button"
                onClick={() => setLanguage('es')}
                className={`px-4 py-1.5 text-sm font-medium transition-colors border-l border-gray-300 ${
                  language === 'es'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
              >
                🇪🇸 {T(tr.settings.langEs)}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default SettingsPage;
