'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock } from 'lucide-react';

export default function TuningAuth() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const correctPassword = process.env.NEXT_PUBLIC_TUNING_PASSWORD || 'chaffee2024';

    if (password === correctPassword) {
      // Set auth cookie (httpOnly would be better, but we'll use a simple approach)
      document.cookie = 'tuning_auth=true; path=/tuning; max-age=86400';
      
      // Redirect to tuning dashboard
      router.push('/tuning');
      router.refresh();
    } else {
      setError('Incorrect password');
      setPassword('');
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-2xl p-8 shadow-2xl">
          <div className="flex justify-center mb-6">
            <div className="bg-blue-500/20 p-4 rounded-full">
              <Lock className="w-8 h-8 text-blue-400" />
            </div>
          </div>

          <h1 className="text-3xl font-bold text-white text-center mb-2">
            Tuning Dashboard
          </h1>
          <p className="text-slate-400 text-center mb-8">QA & Admin Access Only</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                autoFocus
                disabled={loading}
              />
            </div>

            {error && (
              <div className="bg-red-500/20 border border-red-500 text-red-300 px-4 py-2 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              {loading ? 'Unlocking...' : 'Unlock Dashboard'}
            </button>
          </form>

          <p className="text-slate-500 text-xs text-center mt-6">
            Contact Hugo or Dr. Chaffee for access
          </p>
        </div>
      </div>
    </div>
  );
}
