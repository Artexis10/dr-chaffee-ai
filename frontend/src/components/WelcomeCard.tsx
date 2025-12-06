/**
 * WelcomeCard Component
 * 
 * Displays a welcome message with the user's Discord role and role color.
 * Fetches user data from /api/auth/me which handles token refresh automatically.
 */

import React, { useEffect, useState } from 'react';

interface User {
  id: number;
  displayName: string;
  discordId: string | null;
  discordUsername: string | null;
  discordAvatar: string | null;
  tier: string | null;
  tierLabel: string | null;
  tierColor: string | null;
  isDiscordUser: boolean;
}

interface WelcomeCardProps {
  className?: string;
  onLogout?: () => void;
}

export default function WelcomeCard({ className = '', onLogout }: WelcomeCardProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchUser() {
      try {
        const response = await fetch('/api/auth/me', {
          credentials: 'include',
        });

        if (!response.ok) {
          if (response.status === 401) {
            // Not authenticated - this is expected for logged out users
            setUser(null);
            return;
          }
          throw new Error('Failed to fetch user');
        }

        const data = await response.json();
        
        if (data.authenticated && data.user) {
          setUser(data.user);
        } else {
          setUser(null);
        }
      } catch (err) {
        console.error('[WelcomeCard] Error fetching user:', err);
        setError('Failed to load user info');
      } finally {
        setLoading(false);
      }
    }

    fetchUser();
  }, []);

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (err) {
      console.error('[WelcomeCard] Logout error:', err);
    }
    
    // Always redirect to login, even if API call fails
    if (onLogout) {
      onLogout();
    } else {
      window.location.href = '/login';
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className={`welcome-card welcome-card--loading ${className}`}>
        <div className="welcome-card__skeleton">
          <div className="welcome-card__skeleton-avatar" />
          <div className="welcome-card__skeleton-text">
            <div className="welcome-card__skeleton-line welcome-card__skeleton-line--short" />
            <div className="welcome-card__skeleton-line" />
          </div>
        </div>
        <style jsx>{`
          .welcome-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
          }
          .welcome-card__skeleton {
            display: flex;
            align-items: center;
            gap: 12px;
            width: 100%;
          }
          .welcome-card__skeleton-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(90deg, rgba(255,255,255,0.1) 25%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.1) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
          }
          .welcome-card__skeleton-text {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
          }
          .welcome-card__skeleton-line {
            height: 12px;
            border-radius: 4px;
            background: linear-gradient(90deg, rgba(255,255,255,0.1) 25%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.1) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
          }
          .welcome-card__skeleton-line--short {
            width: 60%;
          }
          @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
          }
        `}</style>
      </div>
    );
  }

  // Error state
  if (error) {
    return null; // Silently hide on error
  }

  // Not authenticated
  if (!user) {
    return null;
  }

  // Get avatar URL
  const avatarUrl = user.discordAvatar && user.discordId
    ? `https://cdn.discordapp.com/avatars/${user.discordId}/${user.discordAvatar}.png?size=96`
    : null;

  return (
    <div className={`welcome-card ${className}`}>
      <div className="welcome-card__content">
        {avatarUrl && (
          <img 
            src={avatarUrl} 
            alt={user.displayName}
            className="welcome-card__avatar"
          />
        )}
        {!avatarUrl && (
          <div className="welcome-card__avatar welcome-card__avatar--placeholder">
            {user.displayName.charAt(0).toUpperCase()}
          </div>
        )}
        
        <div className="welcome-card__info">
          <div className="welcome-card__greeting">
            Welcome back, <strong>{user.displayName}</strong>
          </div>
          
          {user.tierLabel && (
            <div className="welcome-card__tier">
              <span className="welcome-card__tier-label">Discord access level:</span>
              <span 
                className="welcome-card__tier-badge"
                style={{ 
                  backgroundColor: user.tierColor ? `${user.tierColor}20` : 'rgba(255,255,255,0.1)',
                  color: user.tierColor || '#ffffff',
                  borderColor: user.tierColor || 'rgba(255,255,255,0.2)',
                }}
              >
                {user.tierLabel}
              </span>
            </div>
          )}
          
          {!user.isDiscordUser && (
            <div className="welcome-card__tier">
              <span className="welcome-card__tier-label">Logged in with password</span>
            </div>
          )}
        </div>
      </div>
      
      <button 
        onClick={handleLogout}
        className="welcome-card__logout"
        title="Log out"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5m0 0l-5-5m5 5H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      <style jsx>{`
        .welcome-card {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .welcome-card__content {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .welcome-card__avatar {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          object-fit: cover;
          border: 2px solid rgba(255, 255, 255, 0.2);
        }
        .welcome-card__avatar--placeholder {
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #5865F2 0%, #7289DA 100%);
          color: white;
          font-weight: 600;
          font-size: 20px;
        }
        .welcome-card__info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .welcome-card__greeting {
          font-size: 14px;
          color: rgba(255, 255, 255, 0.9);
        }
        .welcome-card__greeting strong {
          color: #ffffff;
        }
        .welcome-card__tier {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
        }
        .welcome-card__tier-label {
          color: rgba(255, 255, 255, 0.6);
        }
        .welcome-card__tier-badge {
          padding: 2px 8px;
          border-radius: 4px;
          font-weight: 500;
          border: 1px solid;
          font-size: 11px;
        }
        .welcome-card__logout {
          background: transparent;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 8px;
          padding: 8px;
          cursor: pointer;
          color: rgba(255, 255, 255, 0.7);
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .welcome-card__logout:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #ffffff;
          border-color: rgba(255, 255, 255, 0.3);
        }
        
        /* Light mode support */
        @media (prefers-color-scheme: light) {
          .welcome-card {
            background: rgba(0, 0, 0, 0.03);
            border-color: rgba(0, 0, 0, 0.1);
          }
          .welcome-card__greeting {
            color: rgba(0, 0, 0, 0.8);
          }
          .welcome-card__greeting strong {
            color: #000000;
          }
          .welcome-card__tier-label {
            color: rgba(0, 0, 0, 0.6);
          }
          .welcome-card__logout {
            border-color: rgba(0, 0, 0, 0.2);
            color: rgba(0, 0, 0, 0.6);
          }
          .welcome-card__logout:hover {
            background: rgba(0, 0, 0, 0.05);
            color: #000000;
          }
        }
      `}</style>
    </div>
  );
}
