'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Settings, BarChart3, Sparkles, Search, Home, LogOut, Menu, X, Sun, Moon, FileText } from 'lucide-react';
import '../../styles/tuning.css';

// Theme constants - must match DarkModeToggle.tsx
const THEME_KEY = 'askdrchaffee.theme';

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
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [themeMounted, setThemeMounted] = useState(false);

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

  // Initialize theme on mount - sync with main app's DarkModeToggle (default to DARK)
  useEffect(() => {
    setThemeMounted(true);
    const storedTheme = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Determine initial theme: stored > system preference > default DARK
    let shouldBeDark: boolean;
    if (storedTheme === 'dark') {
      shouldBeDark = true;
    } else if (storedTheme === 'light') {
      shouldBeDark = false;
    } else {
      // No stored preference - default to DARK unless system explicitly prefers light
      shouldBeDark = prefersDark !== false;
    }
    
    setIsDarkMode(shouldBeDark);
    applyTheme(shouldBeDark);
    
    // Persist if not already stored
    if (!storedTheme) {
      localStorage.setItem(THEME_KEY, shouldBeDark ? 'dark' : 'light');
    }
  }, []);

  const applyTheme = (dark: boolean) => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add('dark-mode');
      root.classList.remove('light-mode');
    } else {
      root.classList.remove('dark-mode');
      root.classList.add('light-mode');
    }
  };

  const toggleDarkMode = () => {
    const newMode = !isDarkMode;
    setIsDarkMode(newMode);
    applyTheme(newMode);
    localStorage.setItem(THEME_KEY, newMode ? 'dark' : 'light');
  };
  
  const getCurrentTab = () => {
    if (!pathname) return 'overview';
    if (pathname === '/tuning' || pathname === '/tuning/') return 'overview';
    if (pathname.includes('/tuning/profiles')) return 'profiles';
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
    // Also clear localStorage auth token for complete logout
    localStorage.removeItem('auth_token');
    window.location.href = '/';
  };

  const handleNavClick = (href: string) => {
    router.push(href);
    setIsMobileMenuOpen(false);
  };

  const navItems = [
    { id: 'overview', label: 'Overview', icon: BarChart3, href: '/tuning' },
    { id: 'profiles', label: 'RAG Profiles', icon: FileText, href: '/tuning/profiles' },
    { id: 'models', label: 'Summarizer', icon: Sparkles, href: '/tuning/models' },
    { id: 'search', label: 'Search Config', icon: Search, href: '/tuning/search' },
    { id: 'instructions', label: 'Instructions', icon: Settings, href: '/tuning/instructions' }
  ];

  // Loading state - simple centered spinner
  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '100vh',
        background: 'var(--bg-body)',
        color: 'var(--text-muted)'
      }}>
        <p>Loading...</p>
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
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '100vh',
        background: 'var(--bg-body)',
        color: 'var(--text-muted)'
      }}>
        <p>Redirecting to login...</p>
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
          aria-label="Open menu"
          style={{ visibility: isMobileMenuOpen ? 'hidden' : 'visible' }}
        >
          <Menu />
        </button>
      </header>

      {/* Mobile Overlay */}
      <div 
        className={`tuning-overlay ${isMobileMenuOpen ? 'visible' : ''}`}
        onClick={() => setIsMobileMenuOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`tuning-sidebar ${isMobileMenuOpen ? 'open' : ''}`}>
        {/* Mobile Close Button - positioned absolutely in top-right */}
        {isMobileMenuOpen && (
          <button
            className="tuning-sidebar-close"
            onClick={() => setIsMobileMenuOpen(false)}
            aria-label="Close menu"
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              zIndex: 9999,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '40px',
              height: '40px',
              border: 'none',
              borderRadius: '8px',
              background: 'var(--bg-card-elevated, #f3f4f6)',
              color: 'var(--text-primary, #111)',
              cursor: 'pointer',
              transition: 'background 0.15s'
            }}
          >
            <X style={{ width: '22px', height: '22px' }} />
          </button>
        )}
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
          {themeMounted && (
            <button
              onClick={toggleDarkMode}
              className="tuning-footer-btn"
              aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDarkMode ? <Sun /> : <Moon />}
              <span>{isDarkMode ? 'Light Mode' : 'Dark Mode'}</span>
            </button>
          )}
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
