#!/usr/bin/env python3

import os
import sys

# List of files to clean up
files_to_remove = [
    'add_collaborator.sh',
    'cleanup.py'  # This script will also remove itself
]

def cleanup_files():
    """Remove unwanted files from the repository"""
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✓ Removed {file_path}")
            except Exception as e:
                print(f"✗ Failed to remove {file_path}: {str(e)}")
        else:
            print(f"! File {file_path} does not exist")

if __name__ == "__main__":
    print("Starting cleanup of unwanted files...")
    cleanup_files()
    print("Cleanup complete!")
    print("\nNext steps:")
    print("1. git add .")
    print("2. git commit -m 'Remove unwanted files'")
    print("3. git push origin main")
