#!/usr/bin/env python3
"""Compare yt-dlp vs YouTube API data sources"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("YOUTUBE_API_KEY")
channel_url = "https://www.youtube.com/@anthonychaffeemd"

print("=" * 80)
print("COMPARING YT-DLP vs YOUTUBE API DATA SOURCES")
print("=" * 80)

# ===== YT-DLP SOURCE =====
print("\n📥 FETCHING DATA FROM YT-DLP...")
from scripts.common.list_videos_yt_dlp import YtDlpVideoLister

yt_dlp_lister = YtDlpVideoLister()
yt_dlp_videos = yt_dlp_lister.list_channel_videos(
    channel_url,
    use_cache=False,
    skip_members_only=False
)

print(f"✅ yt-dlp fetched: {len(yt_dlp_videos)} videos")

# ===== YOUTUBE API SOURCE =====
print("\n📥 FETCHING DATA FROM YOUTUBE API...")
from scripts.common.list_videos_api import YouTubeAPILister

api_lister = YouTubeAPILister(api_key)
api_videos = api_lister.list_channel_videos(
    channel_url,
    max_results=None,
    skip_live=False,
    skip_upcoming=False,
    skip_members_only=False
)

print(f"✅ YouTube API fetched: {len(api_videos)} videos")

# ===== COMPARISON =====
print("\n" + "=" * 80)
print("COMPARISON ANALYSIS")
print("=" * 80)

# Create lookup maps
yt_dlp_map = {v.video_id: v for v in yt_dlp_videos}
api_map = {v.video_id: v for v in api_videos}

yt_dlp_ids = set(yt_dlp_map.keys())
api_ids = set(api_map.keys())

overlap = yt_dlp_ids & api_ids
only_yt_dlp = yt_dlp_ids - api_ids
only_api = api_ids - yt_dlp_ids

print(f"\n📊 OVERLAP STATISTICS:")
print(f"  Total in yt-dlp: {len(yt_dlp_ids)}")
print(f"  Total in API: {len(api_ids)}")
print(f"  Overlap (both): {len(overlap)} ({len(overlap)/len(api_ids)*100:.1f}%)")
print(f"  Only in yt-dlp: {len(only_yt_dlp)}")
print(f"  Only in API: {len(only_api)} ({len(only_api)/len(api_ids)*100:.1f}%)")

# ===== DATA QUALITY COMPARISON =====
print(f"\n📋 DATA QUALITY COMPARISON (for overlapping videos):")

# Sample 10 overlapping videos
sample_ids = list(overlap)[:10]
print(f"\nSampling {len(sample_ids)} overlapping videos:\n")

for vid_id in sample_ids:
    yt_dlp_v = yt_dlp_map[vid_id]
    api_v = api_map[vid_id]
    
    print(f"Video: {vid_id}")
    print(f"  Title match: {yt_dlp_v.title == api_v.title}")
    if yt_dlp_v.title != api_v.title:
        print(f"    yt-dlp: {yt_dlp_v.title[:50]}")
        print(f"    API:    {api_v.title[:50]}")
    
    print(f"  Duration: yt-dlp={yt_dlp_v.duration_s}s, API={api_v.duration_s}s")
    
    print(f"  Published date: yt-dlp={yt_dlp_v.published_at}, API={api_v.published_at}")
    
    print(f"  View count: yt-dlp={yt_dlp_v.view_count}, API={api_v.view_count}")
    
    print(f"  Description: yt-dlp={bool(yt_dlp_v.description)}, API={bool(api_v.description)}")
    print()

# ===== MISSING IN YT-DLP =====
print(f"\n⚠️  VIDEOS ONLY IN YOUTUBE API ({len(only_api)} total):")
print(f"Showing first 20:\n")

for i, vid_id in enumerate(list(only_api)[:20], 1):
    v = api_map[vid_id]
    duration_str = f"{v.duration_s}s" if v.duration_s else "Unknown"
    print(f"{i:2d}. {vid_id} - {v.title[:60]}... ({duration_str})")

# ===== ANALYSIS BY DURATION =====
print(f"\n📊 DURATION ANALYSIS (API videos):")

shorts_api = [v for v in api_videos if v.duration_s and v.duration_s < 120]
regular_api = [v for v in api_videos if v.duration_s and v.duration_s >= 120]
unknown_api = [v for v in api_videos if not v.duration_s]

shorts_yt = [v for v in yt_dlp_videos if v.duration_s and v.duration_s < 120]
regular_yt = [v for v in yt_dlp_videos if v.duration_s and v.duration_s >= 120]
unknown_yt = [v for v in yt_dlp_videos if not v.duration_s]

print(f"\nAPI breakdown:")
print(f"  Shorts (<2min): {len(shorts_api)} ({len(shorts_api)/len(api_videos)*100:.1f}%)")
print(f"  Regular (≥2min): {len(regular_api)} ({len(regular_api)/len(api_videos)*100:.1f}%)")
print(f"  Unknown duration: {len(unknown_api)} ({len(unknown_api)/len(api_videos)*100:.1f}%)")

print(f"\nyt-dlp breakdown:")
print(f"  Shorts (<2min): {len(shorts_yt)} ({len(shorts_yt)/len(yt_dlp_videos)*100:.1f}%)")
print(f"  Regular (≥2min): {len(regular_yt)} ({len(regular_yt)/len(yt_dlp_videos)*100:.1f}%)")
print(f"  Unknown duration: {len(unknown_yt)} ({len(unknown_yt)/len(yt_dlp_videos)*100:.1f}%)")

# ===== MISSING DATA FIELDS =====
print(f"\n📋 DATA COMPLETENESS (API videos):")

has_duration = sum(1 for v in api_videos if v.duration_s)
has_views = sum(1 for v in api_videos if v.view_count)
has_published = sum(1 for v in api_videos if v.published_at)
has_description = sum(1 for v in api_videos if v.description)
has_thumbnail = sum(1 for v in api_videos if v.thumbnail_url)

print(f"  Duration: {has_duration}/{len(api_videos)} ({has_duration/len(api_videos)*100:.1f}%)")
print(f"  View count: {has_views}/{len(api_videos)} ({has_views/len(api_videos)*100:.1f}%)")
print(f"  Published date: {has_published}/{len(api_videos)} ({has_published/len(api_videos)*100:.1f}%)")
print(f"  Description: {has_description}/{len(api_videos)} ({has_description/len(api_videos)*100:.1f}%)")
print(f"  Thumbnail: {has_thumbnail}/{len(api_videos)} ({has_thumbnail/len(api_videos)*100:.1f}%)")

# ===== RECOMMENDATION =====
print(f"\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

print(f"""
✅ YOUTUBE API ADVANTAGES:
  • Fetches ALL {len(api_videos)} videos (vs {len(yt_dlp_videos)} with yt-dlp)
  • Better metadata: view counts, publish dates, descriptions
  • More reliable (official API, not scraping)
  • Covers {len(only_api)} videos that yt-dlp misses

⚠️  YT-DLP ADVANTAGES:
  • No API key required
  • Can fetch video availability status (members-only detection)
  • Faster for small batches

🎯 RECOMMENDED ARCHITECTURE:
  1. Use YouTube API as PRIMARY source for video listing
  2. Use yt-dlp for:
     - Downloading audio/video
     - Detecting members-only content
     - Fallback if API fails
  3. Merge metadata: API for metadata, yt-dlp for availability
""")

print("=" * 80)
