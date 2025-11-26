'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Settings, BarChart3, Zap, Search, Home, LogOut } from 'lucide-react';

export default function TuningLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user has tuning_auth cookie with correct value
    const cookies = document.cookie.split(';').map(c => c.trim());
    const tuningCookie = cookies.find(c => c.startsWith('tuning_auth='));
    const isAuthed = tuningCookie === 'tuning_auth=authenticated';
    
    setIsAuthenticated(isAuthed);
    setIsLoading(false);
    
    // If not authenticated and not already on auth page, redirect to tuning login
    if (!isAuthed && pathname !== '/tuning/auth') {
      router.replace('/tuning/auth');
    }
  }, [pathname, router]);
  
  // Extract current tab from pathname
  const getCurrentTab = () => {
    if (!pathname) return 'overview';
    if (pathname === '/tuning' || pathname === '/tuning/') return 'overview';
    if (pathname.includes('/tuning/models')) return 'models';
    if (pathname.includes('/tuning/search')) return 'search';
    if (pathname.includes('/tuning/instructions')) return 'instructions';
    return 'overview';
  };

  const activeTab = getCurrentTab() || 'overview';

  const handleLogout = () => {
    document.cookie = 'tuning_auth=; path=/tuning; max-age=0';
    window.location.href = '/';
  };

  const navItems = [
    { id: 'overview', label: 'Overview', icon: BarChart3, href: '/tuning' },
    { id: 'models', label: 'Models', icon: Zap, href: '/tuning/models' },
    { id: 'search', label: 'Search Config', icon: Search, href: '/tuning/search' },
    { id: 'instructions', label: 'Instructions', icon: Settings, href: '/tuning/instructions' }
  ];

  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '100vh',
        background: 'linear-gradient(to bottom right, #f8fafc, #f1f5f9)'
      }}>
        <div style={{ color: '#6b7280' }}>Loading...</div>
      </div>
    );
  }

  // If on auth page, render children directly (no sidebar)
  if (pathname === '/tuning/auth') {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(to bottom right, #f8fafc, #f1f5f9)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
        {children}
      </div>
    );
  }

  // If not authenticated and not on auth page, show nothing (redirect is happening)
  if (!isAuthenticated) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '100vh',
        background: 'linear-gradient(to bottom right, #f8fafc, #f1f5f9)'
      }}>
        <div style={{ color: '#6b7280' }}>Redirecting to login...</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'linear-gradient(to bottom right, #f8fafc, #f1f5f9)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      {/* Sidebar - only show if authenticated */}
      <aside style={{ width: '256px', background: 'white', borderRight: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', position: 'fixed', height: '100vh', overflowY: 'auto' }}>
        <div style={{ padding: '1.5rem', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ padding: '0.5rem', background: 'linear-gradient(to bottom right, #3b82f6, #a855f7)', borderRadius: '0.5rem' }}>
              <Settings style={{ width: '1.5rem', height: '1.5rem', color: 'white' }} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1f2937' }}>AI Tuning</h1>
              <p style={{ fontSize: '0.75rem', color: '#6b7280' }}>Dashboard</p>
            </div>
          </div>
        </div>

        <nav style={{ flex: 1, padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {navItems.map(({ id, label, icon: Icon, href }) => (
            <button
              key={id}
              onClick={() => router.push(href)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.75rem 1rem',
                borderRadius: '0.5rem',
                border: 'none',
                background: activeTab === id ? '#eff6ff' : 'transparent',
                color: activeTab === id ? '#2563eb' : '#4b5563',
                cursor: 'pointer',
                transition: 'all 0.2s',
                fontSize: '0.95rem',
                fontWeight: activeTab === id ? 600 : 500
              }}
              onMouseEnter={(e) => {
                if (activeTab !== id) e.currentTarget.style.background = '#f3f4f6';
              }}
              onMouseLeave={(e) => {
                if (activeTab !== id) e.currentTarget.style.background = 'transparent';
              }}
            >
              <Icon style={{ width: '1.25rem', height: '1.25rem' }} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div style={{ padding: '1rem', borderTop: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            onClick={() => window.location.href = '/'}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.75rem 1rem',
              borderRadius: '0.5rem',
              border: 'none',
              background: 'transparent',
              color: '#4b5563',
              cursor: 'pointer',
              transition: 'all 0.2s',
              fontSize: '0.95rem',
              fontWeight: 500
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#f3f4f6'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <Home style={{ width: '1.25rem', height: '1.25rem' }} />
            <span>Back to App</span>
          </button>
          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.75rem 1rem',
              borderRadius: '0.5rem',
              border: 'none',
              background: 'transparent',
              color: '#dc2626',
              cursor: 'pointer',
              transition: 'all 0.2s',
              fontSize: '0.95rem',
              fontWeight: 500
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#fee2e2'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <LogOut style={{ width: '1.25rem', height: '1.25rem' }} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ marginLeft: '256px', flex: 1, overflow: 'auto' }}>
        {children}
      </main>
    </div>
  );
}
