/*
 * UI Theme Guardrail:
 * DO NOT modify this file unless Hugo explicitly instructs.
 * This file defines the locked-in Dr Chaffee visual system.
 * See: frontend/docs/ui-theme-guidelines.md
 */

import React from 'react';
import { VideoGroup, SearchResult } from '../types';
import styles from './VideoCard.module.css';

interface VideoCardProps {
  group: VideoGroup;
  query: string;
  highlightSearchTerms: (text: string, query: string) => string;
  seekToTimestamp: (videoId: string, seconds: number) => void;
  copyTimestampLink: (url: string) => void;
}

export const VideoCard: React.FC<VideoCardProps> = ({ 
  group, 
  query, 
  highlightSearchTerms, 
  seekToTimestamp, 
  copyTimestampLink 
}) => {
  return (
    <div key={group.videoId} className={styles['video-card']}>
      <div className={styles['video-header']}>
        <h3>
          <span className={styles['video-icon']}>{group.source_type === 'youtube' ? '📺' : '💼'}</span>
          {group.videoTitle}
        </h3>
      </div>
      
      <div className={styles['clips-container']}>
        {group.clips.map((clip: SearchResult) => (
          <div key={clip.id} className={styles['clip-card']}>
            <div className={styles['clip-content']}>
              <p 
                className={styles['transcript-text']}
                dangerouslySetInnerHTML={{
                  __html: highlightSearchTerms(clip.text, query)
                }}
              ></p>
            </div>
            <div className={styles['clip-footer']}>
              <button 
                className={styles.timestamp}
                onClick={() => {
                  console.log('Timestamp clicked:', group.videoId, 'at', clip.start_time_seconds);
                  seekToTimestamp(group.videoId, Math.floor(clip.start_time_seconds));
                }}
                title="Play this clip"
              >
                {formatTime(clip.start_time_seconds)}
              </button>
              <div className={styles['clip-actions']}>
                {group.source_type === 'youtube' && (
                  <a 
                    href={`https://www.youtube.com/watch?v=${group.videoId}&t=${Math.floor(clip.start_time_seconds)}s`}
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className={styles['watch-link']}
                    onClick={(e) => {
                      console.log('Watch on YouTube clicked:', group.videoId, 'at', clip.start_time_seconds);
                      if (typeof window !== 'undefined') {
                        window.dispatchEvent(new CustomEvent('analytics', {
                          detail: { event: 'result_clicked_youtube', url: `https://www.youtube.com/watch?v=${group.videoId}&t=${Math.floor(clip.start_time_seconds)}s` }
                        }));
                      }
                    }}
                  >
                    Watch on YouTube
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Helper function to format time in MM:SS format
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
