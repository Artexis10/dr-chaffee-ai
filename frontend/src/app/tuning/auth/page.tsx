'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Lock, Home } from 'lucide-react';

export default function TuningAuth() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Verify password via API (same as main app)
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });

      if (response.ok) {
        // Set auth cookie
        document.cookie = 'tuning_auth=true; path=/tuning; max-age=86400';
        
        // Redirect to tuning dashboard
        router.push('/tuning');
        router.refresh();
      } else {
        setError('Incorrect password');
        setPassword('');
      }
    } catch (err) {
      setError('Authentication failed. Please try again.');
      setPassword('');
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Back to Home Link */}
        <Link 
          href="/" 
          className="inline-flex items-center gap-2 mb-6 text-slate-400 hover:text-white transition-colors"
        >
          <Home className="w-4 h-4" />
          <span className="text-sm">Back to Home</span>
        </Link>

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
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Password
              </label>
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

          <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-slate-300 text-sm">
              <strong>How to access:</strong> Click Dr. Chaffee's logo on the home page 3 times to reach this page.
            </p>
          </div>

          <p className="text-slate-500 text-xs text-center mt-4">
            Contact Hugo or Dr. Chaffee for the password
          </p>
        </div>
      </div>
    </div>
  );
}
