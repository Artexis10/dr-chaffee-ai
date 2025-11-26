'use client';

import { useState, useEffect } from 'react';
import { Database, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';
import Link from 'next/link';

interface Stats {
  total_videos: number;
  total_segments: number;
  segments_with_embeddings: number;
  segments_missing_embeddings: number;
  embedding_coverage: string;
  embedding_dimensions: number;
}

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) {
        throw new Error(`Failed to load stats: ${res.status}`);
      }
      const data = await res.json();
      setStats(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load stats:', err);
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[300px]">
        <p className="text-gray-500">Loading stats...</p>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg">
          <AlertCircle className="w-5 h-5" />
          {error || 'Failed to load stats'}
        </div>
      </div>
    );
  }

  const coveragePct = parseFloat(stats.embedding_coverage);
  const isCoverageGood = coveragePct >= 95;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
          Dashboard Overview
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Real-time statistics and embedding coverage
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {/* Total Videos */}
        <div className="bg-black dark:bg-neutral-800 rounded-xl p-5 text-white">
          <div className="flex items-center gap-2 mb-3 opacity-80">
            <Database className="w-5 h-5" />
            <span className="text-sm font-medium">Videos</span>
          </div>
          <div className="text-3xl font-bold mb-1">
            {stats.total_videos.toLocaleString()}
          </div>
          <div className="text-sm opacity-70">Total Videos Indexed</div>
        </div>

        {/* Total Segments */}
        <div className="bg-black dark:bg-neutral-800 rounded-xl p-5 text-white">
          <div className="flex items-center gap-2 mb-3 opacity-80">
            <TrendingUp className="w-5 h-5" />
            <span className="text-sm font-medium">Segments</span>
          </div>
          <div className="text-3xl font-bold mb-1">
            {stats.total_segments.toLocaleString()}
          </div>
          <div className="text-sm opacity-70">Total Segments</div>
        </div>

        {/* Embedding Coverage */}
        <div className="bg-black dark:bg-neutral-800 rounded-xl p-5 text-white">
          <div className="flex items-center gap-2 mb-3 opacity-80">
            {isCoverageGood ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            <span className="text-sm font-medium">Coverage</span>
          </div>
          <div className="text-3xl font-bold mb-1">
            {stats.embedding_coverage}
          </div>
          <div className="text-sm opacity-70">
            {stats.segments_with_embeddings.toLocaleString()} of {stats.total_segments.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Missing Embeddings Alert */}
      {stats.segments_missing_embeddings > 0 && (
        <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300 rounded-lg mb-8">
          <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-semibold mb-1">Missing Embeddings</p>
            <p className="text-sm opacity-90">
              {stats.segments_missing_embeddings.toLocaleString()} segments don't have embeddings yet.
              Run the embedding pipeline to process these segments.
            </p>
          </div>
        </div>
      )}

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Embedding Info */}
        <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-xl p-5">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Embedding Configuration</h3>
          <div className="mb-3">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Dimensions</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">
              {stats.embedding_dimensions}
            </p>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 pt-3 border-t border-gray-100 dark:border-neutral-800">
            Embeddings help the AI find the most relevant clips. 384 is a good balance of speed and accuracy.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-xl p-5">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>
          <div className="flex flex-col gap-3">
            <Link 
              href="/tuning/models" 
              className="block w-full py-2.5 px-4 bg-black dark:bg-white text-white dark:text-black text-center font-medium rounded-lg hover:opacity-90 transition-opacity"
            >
              View Embedding Models
            </Link>
            <Link 
              href="/tuning/search" 
              className="block w-full py-2.5 px-4 bg-gray-100 dark:bg-neutral-800 text-gray-900 dark:text-white text-center font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-neutral-700 transition-colors"
            >
              Configure Search
            </Link>
            <Link 
              href="/tuning/instructions" 
              className="block w-full py-2.5 px-4 bg-gray-100 dark:bg-neutral-800 text-gray-900 dark:text-white text-center font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-neutral-700 transition-colors"
            >
              Custom Instructions
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
