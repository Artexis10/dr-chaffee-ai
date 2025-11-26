'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Settings, BarChart3, Zap, Search, Home, LogOut, Menu, X } from 'lucide-react';
import '../../styles/tuning.css';

export default function TuningLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      if (pathname === '/tuning/auth') {
        setIsLoading(false);
        return;
      }
      
      try {
        const res = await fetch('/api/tuning/models', {
          method: 'GET',
          credentials: 'include',
        });
        
        if (res.ok) {
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
          router.replace('/tuning/auth');
        }
      } catch (error) {
        console.error('[Tuning Layout] Auth check failed:', error);
        setIsAuthenticated(false);
        router.replace('/tuning/auth');
      } finally {
        setIsLoading(false);
      }
    };
    
    checkAuth();
  }, [pathname, router]);

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  // Close mobile menu on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsMobileMenuOpen(false);
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, []);
  
  const getCurrentTab = () => {
    if (!pathname) return 'overview';
    if (pathname === '/tuning' || pathname === '/tuning/') return 'overview';
    if (pathname.includes('/tuning/models')) return 'models';
    if (pathname.includes('/tuning/search')) return 'search';
    if (pathname.includes('/tuning/instructions')) return 'instructions';
    return 'overview';
  };

  const activeTab = getCurrentTab();

  const handleLogout = async () => {
    try {
      await fetch('/api/tuning/auth/logout', { method: 'POST', credentials: 'include' });
    } catch (e) {
      // Ignore errors
    }
    window.location.href = '/';
  };

  const handleNavClick = (href: string) => {
    router.push(href);
    setIsMobileMenuOpen(false);
  };

  const navItems = [
    { id: 'overview', label: 'Overview', icon: BarChart3, href: '/tuning' },
    { id: 'models', label: 'Models', icon: Zap, href: '/tuning/models' },
    { id: 'search', label: 'Search Config', icon: Search, href: '/tuning/search' },
    { id: 'instructions', label: 'Instructions', icon: Settings, href: '/tuning/instructions' }
  ];

  // Loading state - simple centered spinner
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-neutral-950">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  // Auth page - render children directly without dashboard wrapper
  if (pathname === '/tuning/auth') {
    return <>{children}</>;
  }

  // Not authenticated - redirect happening
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-neutral-950">
        <p className="text-gray-500">Redirecting to login...</p>
      </div>
    );
  }

  // Authenticated dashboard with sidebar
  return (
    <div className="tuning-dashboard">
      {/* Mobile Header */}
      <header className="tuning-mobile-header">
        <div className="tuning-mobile-brand">
          <div className="tuning-mobile-brand-icon">
            <Settings />
          </div>
          <h1 className="tuning-mobile-title">AI Tuning</h1>
        </div>
        <button 
          className="tuning-hamburger"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
        >
          {isMobileMenuOpen ? <X /> : <Menu />}
        </button>
      </header>

      {/* Mobile Overlay */}
      <div 
        className={`tuning-overlay ${isMobileMenuOpen ? 'visible' : ''}`}
        onClick={() => setIsMobileMenuOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`tuning-sidebar ${isMobileMenuOpen ? 'open' : ''}`}>
        <div className="tuning-sidebar-header">
          <div className="tuning-sidebar-brand">
            <div className="tuning-sidebar-icon">
              <Settings />
            </div>
            <div>
              <h1 className="tuning-sidebar-title">AI Tuning</h1>
              <p className="tuning-sidebar-subtitle">Dashboard</p>
            </div>
          </div>
        </div>

        <nav className="tuning-nav">
          {navItems.map(({ id, label, icon: Icon, href }) => (
            <button
              key={id}
              onClick={() => handleNavClick(href)}
              className={`tuning-nav-item ${activeTab === id ? 'active' : ''}`}
            >
              <Icon />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="tuning-sidebar-footer">
          <button
            onClick={() => { window.location.href = '/'; }}
            className="tuning-footer-btn"
          >
            <Home />
            <span>Back to App</span>
          </button>
          <button
            onClick={handleLogout}
            className="tuning-footer-btn logout"
          >
            <LogOut />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="tuning-main">
        {children}
      </main>
    </div>
  );
}
