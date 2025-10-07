#!/usr/bin/env python3
"""
Move backup voice profiles to a separate directory.

This prevents backup profiles from being loaded during speaker identification,
which can cause confusion and incorrect margin calculations.
"""
import os
import shutil
from pathlib import Path

# Directories
VOICES_DIR = Path("voices")
BACKUPS_DIR = VOICES_DIR / "backups"

def move_backups():
    """Move all backup profiles to backups subdirectory."""
    
    # Create backups directory if it doesn't exist
    BACKUPS_DIR.mkdir(exist_ok=True)
    
    # Find all backup profiles
    backup_files = list(VOICES_DIR.glob("*_backup_*.json"))
    
    if not backup_files:
        print("OK: No backup profiles found in voices directory")
        return
    
    print(f"Found {len(backup_files)} backup profiles:")
    for backup_file in backup_files:
        print(f"  - {backup_file.name}")
    
    # Move each backup
    moved = 0
    for backup_file in backup_files:
        dest = BACKUPS_DIR / backup_file.name
        try:
            shutil.move(str(backup_file), str(dest))
            print(f"OK: Moved: {backup_file.name} -> backups/{backup_file.name}")
            moved += 1
        except Exception as e:
            print(f"ERROR: Failed to move {backup_file.name}: {e}")
    
    print(f"\nOK: Moved {moved}/{len(backup_files)} backup profiles to backups/")
    print(f"Backups location: {BACKUPS_DIR.absolute()}")
    
    # Show remaining profiles
    remaining = list(VOICES_DIR.glob("*.json"))
    print(f"\nActive profiles in voices/:")
    for profile in remaining:
        print(f"  - {profile.name}")

if __name__ == "__main__":
    move_backups()
