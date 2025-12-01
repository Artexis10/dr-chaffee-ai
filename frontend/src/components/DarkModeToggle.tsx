/*
 * UI Theme Guardrail:
 * DO NOT modify this file unless Hugo explicitly instructs.
 * This file defines the locked-in Dr Chaffee visual system.
 * See: frontend/docs/ui-theme-guidelines.md
 */

import React, { useState, useEffect } from 'react';

const THEME_KEY = 'askdrchaffee.theme';

export const DarkModeToggle: React.FC = () => {
  // Initialize to null to prevent hydration mismatch, then update on client
  const [isDarkMode, setIsDarkMode] = useState<boolean | null>(null);
  const [mounted, setMounted] = useState(false);

  // Initialize theme on mount - check localStorage first, then system preference, then default to DARK
  useEffect(() => {
    setMounted(true);
    
    const storedTheme = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Determine initial theme: stored > system preference > default DARK
    let shouldBeDark: boolean;
    if (storedTheme === 'dark') {
      shouldBeDark = true;
    } else if (storedTheme === 'light') {
      shouldBeDark = false;
    } else {
      // No stored preference - use system preference, default to DARK if no system preference
      shouldBeDark = prefersDark !== false; // Default to dark unless system explicitly prefers light
    }
    
    setIsDarkMode(shouldBeDark);
    applyTheme(shouldBeDark);
    
    // Persist if not already stored
    if (!storedTheme) {
      localStorage.setItem(THEME_KEY, shouldBeDark ? 'dark' : 'light');
    }
  }, []);

  // Apply theme classes to document
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

  // Toggle dark mode
  const toggleDarkMode = () => {
    const newMode = !isDarkMode;
    setIsDarkMode(newMode);
    applyTheme(newMode);
    localStorage.setItem(THEME_KEY, newMode ? 'dark' : 'light');
  };

  // Don't render until mounted (prevents hydration mismatch)
  if (!mounted || isDarkMode === null) {
    // Return a placeholder with same dimensions to prevent layout shift
    return (
      <div 
        className="dark-mode-toggle-placeholder"
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 48,
          height: 48,
          borderRadius: '50%',
          background: 'transparent'
        }}
      />
    );
  }

  return (
    <button 
      onClick={toggleDarkMode} 
      className="dark-mode-toggle"
      aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
      title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
    >
      {isDarkMode ? (
        /* Sun icon - shown in dark mode to switch to light */
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2"/>
          <path d="M12 2V4M12 20V22M4 12H2M22 12H20M5.64 5.64L4.22 4.22M19.78 19.78L18.36 18.36M5.64 18.36L4.22 19.78M19.78 4.22L18.36 5.64" 
            stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      ) : (
        /* Moon icon - shown in light mode to switch to dark */
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" 
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
      
      <style jsx>{`
        .dark-mode-toggle {
          position: fixed;
          bottom: 24px;
          right: 24px;
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background: ${isDarkMode ? 'rgba(30, 30, 30, 0.95)' : 'rgba(255, 255, 255, 0.95)'};
          border: 1px solid ${isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'};
          color: ${isDarkMode ? '#fafafa' : '#1a1a1a'};
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          z-index: 1000;
          box-shadow: ${isDarkMode 
            ? '0 4px 16px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05)' 
            : '0 4px 16px rgba(0, 0, 0, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.8)'};
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
        }
        
        .dark-mode-toggle:hover {
          transform: translateY(-2px) scale(1.05);
          background: ${isDarkMode ? 'rgba(40, 40, 40, 0.98)' : 'rgba(255, 255, 255, 0.98)'};
          border-color: ${isDarkMode ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.2)'};
          box-shadow: ${isDarkMode 
            ? '0 8px 24px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.08)' 
            : '0 8px 24px rgba(0, 0, 0, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.9)'};
        }
        
        .dark-mode-toggle:active {
          transform: translateY(0) scale(0.98);
        }
        
        .dark-mode-toggle svg {
          width: 20px;
          height: 20px;
          flex-shrink: 0;
          display: block;
        }
        
        @media (max-width: 768px) {
          .dark-mode-toggle {
            width: 44px;
            height: 44px;
            bottom: 16px;
            right: 16px;
          }
        }
      `}</style>
    </button>
  );
};
