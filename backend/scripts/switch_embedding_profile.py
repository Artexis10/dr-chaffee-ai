#!/usr/bin/env python3
"""
Switch between embedding profiles (quality vs speed)
No database migration required - just updates .env
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def read_env_file(env_path):
    """Read .env file into dict"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def write_env_file(env_path, env_vars):
    """Write dict back to .env file, preserving comments"""
    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        return False
    
    # Read original file to preserve comments and structure
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update lines with new values
    updated_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in env_vars:
                # Update this line
                updated_lines.append(f"{key}={env_vars[key]}\n")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    return True


def main():
    """Switch embedding profile"""
    print("=" * 80)
    print("EMBEDDING PROFILE SWITCHER")
    print("=" * 80)
    
    # Find .env file
    env_path = Path(__file__).parent.parent.parent / '.env'
    
    if not env_path.exists():
        print(f"\n❌ .env file not found at {env_path}")
        print("Please create .env from .env.example first")
        return
    
    # Read current config
    env_vars = read_env_file(env_path)
    current_profile = env_vars.get('EMBEDDING_PROFILE', 'quality').lower()
    
    # Define profiles
    profiles = {
        'quality': {
            'model': 'Alibaba-NLP/gte-Qwen2-1.5B-instruct',
            'dimensions': '1536',
            'speed': '20-30 texts/sec',
            'vram': '~4GB',
            'description': 'Best quality embeddings'
        },
        'speed': {
            'model': 'BAAI/bge-small-en-v1.5',
            'dimensions': '384',
            'speed': '1500-2000 texts/sec',
            'vram': '~0.5GB',
            'description': '60-80x faster, good quality'
        }
    }
    
    print(f"\n📊 Current Profile: {current_profile.upper()}")
    if current_profile in profiles:
        p = profiles[current_profile]
        print(f"  Model: {p['model']}")
        print(f"  Dimensions: {p['dimensions']}")
        print(f"  Speed: {p['speed']}")
        print(f"  VRAM: {p['vram']}")
    
    print(f"\n🔄 Available Profiles:")
    print(f"\n1. QUALITY (GTE-Qwen2-1.5B)")
    print(f"   • Best embedding quality")
    print(f"   • Speed: 20-30 texts/sec")
    print(f"   • VRAM: ~4GB")
    print(f"   • Use for: Maximum search accuracy")
    
    print(f"\n2. SPEED (BGE-Small)")
    print(f"   • 60-80x faster than quality")
    print(f"   • Speed: 1500-2000 texts/sec")
    print(f"   • VRAM: ~0.5GB")
    print(f"   • Quality: 95% of GTE-Qwen2 (enable reranker for 98%)")
    print(f"   • Use for: Fast ingestion, large-scale processing")
    
    print(f"\n" + "=" * 80)
    choice = input("Select profile (1=quality, 2=speed, q=quit): ").strip().lower()
    
    if choice == 'q':
        print("Cancelled.")
        return
    
    if choice == '1':
        new_profile = 'quality'
        enable_reranker = 'false'
    elif choice == '2':
        new_profile = 'speed'
        # Ask about reranker for speed profile
        rerank_choice = input("\nEnable reranker for better quality? (y/n, default=y): ").strip().lower()
        enable_reranker = 'true' if rerank_choice != 'n' else 'false'
    else:
        print("Invalid choice.")
        return
    
    # Update .env
    env_vars['EMBEDDING_PROFILE'] = new_profile
    env_vars['ENABLE_RERANKER'] = enable_reranker
    
    if write_env_file(env_path, env_vars):
        print(f"\n✅ Profile switched to: {new_profile.upper()}")
        print(f"✅ Reranker: {enable_reranker}")
        
        p = profiles[new_profile]
        print(f"\n📊 New Configuration:")
        print(f"  Model: {p['model']}")
        print(f"  Dimensions: {p['dimensions']}")
        print(f"  Speed: {p['speed']}")
        print(f"  VRAM: {p['vram']}")
        
        print(f"\n⚠️  IMPORTANT:")
        print(f"  • Restart any running ingestion processes")
        print(f"  • Model will be downloaded on first use (~{p['vram']} VRAM)")
        if new_profile == 'speed':
            print(f"  • Embeddings will be 384-dim (not compatible with existing 1536-dim)")
            print(f"  • Consider running on new videos or re-ingesting existing ones")
        
        print(f"\n🚀 Ready to use! Run your ingestion script to test.")
    else:
        print(f"\n❌ Failed to update .env file")
    
    print("=" * 80)


if __name__ == '__main__':
    main()
