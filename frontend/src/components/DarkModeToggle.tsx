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

  // Initialize theme on mount - check localStorage first, then system preference, then default to light
  useEffect(() => {
    setMounted(true);
    
    const storedTheme = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Determine initial theme: stored > system preference > default light
    let shouldBeDark: boolean;
    if (storedTheme === 'dark') {
      shouldBeDark = true;
    } else if (storedTheme === 'light') {
      shouldBeDark = false;
    } else {
      // No stored preference - use system preference, default to light
      shouldBeDark = prefersDark;
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
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 3V4M12 20V21M21 12H20M4 12H3M18.364 18.364L17.657 17.657M6.343 6.343L5.636 5.636M18.364 5.636L17.657 6.343M6.343 17.657L5.636 18.364M16 12C16 14.2091 14.2091 16 12 16C9.79086 16 8 14.2091 8 12C8 9.79086 9.79086 8 12 8C14.2091 8 16 9.79086 16 12Z" 
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M21.752 15.002C20.5633 15.4975 19.2879 15.7517 18 15.75C13.4436 15.75 9.75 12.0564 9.75 7.5C9.75 6.21226 10.0043 4.93692 10.5 3.74805C5.81563 4.97317 2.75 9.28043 2.75 14.25C2.75 20.1825 7.56751 25 13.5 25C18.4693 25 22.7764 21.9348 24.002 17.251C24.0008 17.2539 24.0015 17.2539 24.002 17.251C24.0005 17.2481 23.9989 17.2452 23.9974 17.2424C23.3644 16.386 22.5926 15.6142 21.7362 14.9813C21.7334 14.9797 21.7305 14.9781 21.7277 14.9766C21.7365 14.9919 21.7444 15.0076 21.752 15.0233V15.002Z" 
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
