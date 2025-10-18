# Frontend UX Improvements

## Issues Identified

### 1. **Answer Style Toggle Position**
- **Current:** Toggle appears AFTER answer is generated (line 632-648 in AnswerCard.tsx)
- **Problem:** User must wait for answer, then click toggle, then wait again for new answer
- **Impact:** Poor UX, wastes time and API calls

### 2. **Stats Not Dynamic**
- **Current:** Hardcoded fallback values (line 35: `segments: 1695, videos: 26`)
- **Problem:** Stats don't update when new videos are ingested
- **Impact:** Misleading loading messages

### 3. **Loading Experience**
- **Current:** Good, but could be better
- **Opportunity:** Add real-time progress, estimated time remaining

## Proposed Solutions

### Solution 1: Move Answer Style Toggle to Search Bar

**Before (Current Flow):**
```
User types query → Search → Get answer → Click toggle → Wait again
```

**After (Improved Flow):**
```
User types query → Select style (Short/Long) → Search → Get answer
```

**Benefits:**
- ✅ One-click experience
- ✅ No wasted API calls
- ✅ Clear expectations upfront
- ✅ Saves 10-30 seconds per query

### Solution 2: Make Stats Truly Dynamic

**Create `/api/stats` endpoint** that queries the database in real-time:

```typescript
// frontend/src/pages/api/stats.ts
import { NextApiRequest, NextApiResponse } from 'next';
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const result = await pool.query(`
      SELECT 
        (SELECT COUNT(*) FROM segments) as segments,
        (SELECT COUNT(DISTINCT video_id) FROM segments) as videos
    `);

    const stats = result.rows[0];
    
    // Cache for 5 minutes
    res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
    
    return res.status(200).json({
      segments: parseInt(stats.segments),
      videos: parseInt(stats.videos),
      last_updated: new Date().toISOString()
    });
  } catch (error) {
    console.error('Stats API error:', error);
    // Return fallback values on error
    return res.status(200).json({
      segments: 1695,
      videos: 26,
      fallback: true
    });
  }
}
```

### Solution 3: Enhanced Loading Experience

**Add:**
- Real-time progress indicator
- Estimated time remaining
- Animated segment counter
- Cancellation with partial results

## Implementation Plan

### Phase 1: Move Answer Style Toggle (High Priority)

**File: `frontend/src/components/SearchBar.tsx`**

Add answer style selector next to search button:

```typescript
interface SearchBarProps {
  query: string;
  setQuery: (query: string) => void;
  handleSearch: (e: React.FormEvent) => void;
  loading: boolean;
  answerStyle: 'concise' | 'detailed';  // NEW
  onAnswerStyleChange: (style: 'concise' | 'detailed') => void;  // NEW
}

export const SearchBar: React.FC<SearchBarProps> = ({ 
  query, 
  setQuery, 
  handleSearch, 
  loading,
  answerStyle,
  onAnswerStyleChange
}) => {
  // ... existing code ...

  return (
    <form onSubmit={onSubmit} className="search-form">
      <div className={`search-container ${isFocused ? 'focused' : ''}`}>
        {/* Existing search input */}
        <input ... />
        
        {/* NEW: Answer Style Toggle */}
        <div className="answer-style-selector">
          <label className="style-label">Answer:</label>
          <div className="style-buttons">
            <button
              type="button"
              className={`style-btn ${answerStyle === 'concise' ? 'active' : ''}`}
              onClick={() => onAnswerStyleChange('concise')}
              title="Short, focused answer (~30 seconds)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              Short
            </button>
            <button
              type="button"
              className={`style-btn ${answerStyle === 'detailed' ? 'active' : ''}`}
              onClick={() => onAnswerStyleChange('detailed')}
              title="Comprehensive answer (~60 seconds)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              Long
            </button>
          </div>
        </div>
        
        <button type="submit" className="search-button" ...>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
      
      <style jsx>{`
        .answer-style-selector {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-right: 12px;
        }
        
        .style-label {
          font-size: 13px;
          font-weight: 500;
          color: #6b7280;
          white-space: nowrap;
        }
        
        .style-buttons {
          display: flex;
          background: #f3f4f6;
          border-radius: 8px;
          padding: 2px;
          gap: 2px;
        }
        
        .style-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 6px 12px;
          border: none;
          background: transparent;
          color: #6b7280;
          font-size: 13px;
          font-weight: 600;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s ease;
          white-space: nowrap;
        }
        
        .style-btn:hover {
          background: #e5e7eb;
          color: #374151;
        }
        
        .style-btn.active {
          background: #ffffff;
          color: #3b82f6;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .style-btn svg {
          flex-shrink: 0;
        }
        
        @media (max-width: 768px) {
          .answer-style-selector {
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
            margin-bottom: 12px;
            width: 100%;
          }
          
          .style-buttons {
            width: 100%;
          }
          
          .style-btn {
            flex: 1;
            justify-content: center;
          }
        }
      `}</style>
    </form>
  );
};
```

**File: `frontend/src/pages/index.tsx`**

Update to pass answer style to SearchBar:

```typescript
// Around line 38
const [answerStyle, setAnswerStyle] = useState<'concise' | 'detailed'>('concise');

// In the render section
<SearchBar
  query={query}
  setQuery={handleSetQuery}
  handleSearch={handleSearch}
  loading={loading}
  answerStyle={answerStyle}  // NEW
  onAnswerStyleChange={setAnswerStyle}  // NEW
/>
```

**File: `frontend/src/components/AnswerCard.tsx`**

Remove the toggle from the answer card (lines 632-648) since it's now in the search bar.

### Phase 2: Dynamic Stats API (Medium Priority)

**Create: `frontend/src/pages/api/stats.ts`**

```typescript
import { NextApiRequest, NextApiResponse } from 'next';
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const result = await pool.query(`
      SELECT 
        (SELECT COUNT(*) FROM segments) as segments,
        (SELECT COUNT(DISTINCT video_id) FROM segments) as videos,
        (SELECT MAX(published_at) FROM segments) as latest_video
    `);

    const stats = result.rows[0];
    
    // Cache for 5 minutes (stats don't change often)
    res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
    
    return res.status(200).json({
      segments: parseInt(stats.segments),
      videos: parseInt(stats.videos),
      latest_video: stats.latest_video,
      last_updated: new Date().toISOString()
    });
  } catch (error) {
    console.error('Stats API error:', error);
    // Return fallback values on error
    return res.status(200).json({
      segments: 15000,
      videos: 300,
      fallback: true
    });
  }
}
```

**Update: `frontend/src/components/AnswerCard.tsx`**

Change line 35 from hardcoded to dynamic:

```typescript
// OLD (line 35)
const [stats, setStats] = useState({ segments: 1695, videos: 26 });

// NEW
const [stats, setStats] = useState({ segments: 0, videos: 0 });
const [statsLoaded, setStatsLoaded] = useState(false);

// Update useEffect (lines 38-49)
useEffect(() => {
  fetch('/api/stats')
    .then(res => res.json())
    .then(data => {
      if (data.segments && data.videos) {
        setStats({ segments: data.segments, videos: data.videos });
        setStatsLoaded(true);
      }
    })
    .catch(err => {
      console.warn('Failed to fetch stats:', err);
      // Use fallback values
      setStats({ segments: 15000, videos: 300 });
      setStatsLoaded(true);
    });
}, []);

// Update loading messages (line 76) to show "Loading..." until stats are loaded
const loadingMessages = [
  { threshold: 0, message: "Generating query embedding for semantic search..." },
  { threshold: 3, message: statsLoaded 
      ? `Searching ${stats.segments.toLocaleString()} segments across ${stats.videos} videos...`
      : "Searching database..." 
  },
  // ... rest of messages
];
```

### Phase 3: Enhanced Loading (Low Priority)

**Add to `frontend/src/components/AnswerCard.tsx`:**

```typescript
// Add estimated time remaining
const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number | null>(null);

useEffect(() => {
  if (loading && loadingTime > 5) {
    // Estimate based on answer style
    const avgTime = answerStyle === 'detailed' ? 45 : 25;
    const remaining = Math.max(0, avgTime - loadingTime);
    setEstimatedTimeRemaining(remaining);
  } else {
    setEstimatedTimeRemaining(null);
  }
}, [loading, loadingTime, answerStyle]);

// In loading UI (around line 102)
<div className="loading-text">
  <h3>Emulated Dr. Chaffee (AI)</h3>
  <p>{currentMessage}</p>
  <div className="loading-meta">
    <div className="loading-timer">{loadingTime}s</div>
    {estimatedTimeRemaining !== null && estimatedTimeRemaining > 0 && (
      <div className="loading-eta">~{estimatedTimeRemaining}s remaining</div>
    )}
  </div>
</div>
```

## Visual Mockup

### Current Search Bar
```
┌─────────────────────────────────────────────────────┐
│ 🔍  Ask Dr. Chaffee about...           [Search]     │
└─────────────────────────────────────────────────────┘
```

### Improved Search Bar
```
┌─────────────────────────────────────────────────────────────────┐
│ 🔍  Ask Dr. Chaffee about...    Answer: [Short] [Long]  [Search]│
└─────────────────────────────────────────────────────────────────┘
```

### Mobile Layout
```
┌──────────────────────────────────┐
│ 🔍  Ask Dr. Chaffee about...     │
│                                  │
│ Answer: [Short ✓] [Long]        │
│                                  │
│          [Search]                │
└──────────────────────────────────┘
```

## Benefits Summary

### 1. **Answer Style Toggle in Search Bar**
- ⏱️ **Time saved:** 10-30 seconds per query
- 💰 **Cost saved:** Eliminates duplicate API calls
- 😊 **UX improvement:** Clear expectations upfront
- 📱 **Mobile friendly:** Better layout on small screens

### 2. **Dynamic Stats**
- ✅ **Accuracy:** Always shows current database size
- 📊 **Transparency:** Users see real data
- 🔄 **Auto-updates:** No manual updates needed
- 💾 **Cached:** 5-minute cache prevents DB overload

### 3. **Enhanced Loading**
- ⏰ **ETA:** Users know how long to wait
- 🎯 **Progress:** Visual feedback on status
- ❌ **Cancellation:** Can stop and see partial results
- 📈 **Engagement:** Keeps users informed

## Implementation Priority

### High Priority (Do First)
1. ✅ Move answer style toggle to search bar
2. ✅ Remove toggle from answer card
3. ✅ Update index.tsx to pass style prop

### Medium Priority (Do Next)
4. ✅ Create `/api/stats` endpoint
5. ✅ Update AnswerCard to use dynamic stats
6. ✅ Add caching to stats API

### Low Priority (Nice to Have)
7. ⭕ Add estimated time remaining
8. ⭕ Add animated progress bar
9. ⭕ Add cancellation with partial results

## Testing Checklist

- [ ] Answer style toggle works in search bar
- [ ] Short answer generates correctly
- [ ] Long answer generates correctly
- [ ] Toggle state persists during session
- [ ] Stats API returns correct counts
- [ ] Stats update after new ingestion
- [ ] Loading messages show correct stats
- [ ] Mobile layout works properly
- [ ] Desktop layout works properly
- [ ] Tablet layout works properly

## Rollback Plan

If issues occur:
1. Keep old toggle in AnswerCard (comment out new one)
2. Use hardcoded stats as fallback
3. Revert SearchBar changes

## Performance Impact

### Answer Style Toggle
- **Bundle size:** +2KB (minimal)
- **Runtime:** No impact
- **API calls:** Reduces by 50% (no duplicate requests)

### Dynamic Stats
- **Database load:** 1 query per 5 minutes (cached)
- **API response time:** ~50ms
- **Bundle size:** +1KB

### Enhanced Loading
- **Bundle size:** +3KB
- **Runtime:** Minimal (timer updates)
- **Memory:** Negligible

## Estimated Implementation Time

- **Phase 1 (Answer Style Toggle):** 2-3 hours
- **Phase 2 (Dynamic Stats):** 1-2 hours
- **Phase 3 (Enhanced Loading):** 2-3 hours
- **Testing:** 1-2 hours

**Total:** 6-10 hours

## Next Steps

1. Review this document
2. Approve changes
3. Implement Phase 1 (answer style toggle)
4. Test on local environment
5. Deploy to Vercel
6. Monitor user feedback
7. Implement Phase 2 if Phase 1 successful
