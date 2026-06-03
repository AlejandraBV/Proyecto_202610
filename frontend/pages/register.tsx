import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { apiClient } from '@/lib/api';
import { useT } from '@/hooks/useT';
import { tr } from '@/lib/translations';
import toast from 'react-hot-toast';

const Register: React.FC = () => {
  const router = useRouter();
  const T = useT();
  const [formData, setFormData] = useState({ email: '', password: '', name: '' });
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.register(formData.email, formData.password, formData.name);
      toast.success(T(tr.auth.registerSuccess));
      router.push('/login');
    } catch {
      toast.error(T(tr.auth.registerError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
        <h1 className="mb-6 text-center text-2xl font-bold text-gray-900">
          {T(tr.auth.createAccount)}
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">{T(tr.auth.fullName)}</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder={T(tr.auth.namePlaceholder)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">{T(tr.auth.email)}</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">{T(tr.auth.password)}</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-primary px-4 py-2 text-white hover:bg-primary/90 disabled:bg-gray-300 transition-colors font-medium"
          >
            {loading ? T(tr.auth.creatingAccount) : T(tr.auth.signUp)}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          {T(tr.auth.alreadyAccount)}{' '}
          <Link href="/login" className="font-medium text-primary hover:underline">
            {T(tr.auth.login)}
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
