/**
 * /settings - User profile and application settings page.
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { Sidebar } from '@/components/Sidebar';
import { useAppStore } from '@/store/appStore';
import { useConversations } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
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
  } = useAppStore();
  const { fetchConversations } = useConversations();

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
      // Profile update would call a PATCH /users/me endpoint (if implemented)
      setCurrentUser({ ...currentUser, name, institution, subject, level });
      toast.success('Settings saved');
    } catch {
      toast.error('Failed to save settings');
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
              toast.success('Conversation deleted');
            } catch {
              toast.error('Failed to delete conversation');
            }
          }}
          onNewConversation={() => router.push('/')}
        />
      }
    >
      <div className="flex h-full flex-col overflow-y-auto p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900">Settings</h1>

        <form onSubmit={handleSave} className="max-w-lg space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Institution</label>
            <input
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default Subject</label>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g. Biology, Mathematics"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default Level</label>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="elementary">Elementary</option>
              <option value="secondary">Secondary</option>
              <option value="university">University</option>
              <option value="professional">Professional</option>
            </select>
          </div>

          <div className="flex items-center gap-4 pt-2">
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {isSaving ? 'Saving…' : 'Save Changes'}
            </button>

            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
            >
              Log Out
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default SettingsPage;
