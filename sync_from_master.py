#!/usr/bin/env python3

import os
import sys
import subprocess
import json

def main():
    """Sync necessary files from master branch"""
    # Define the files we need to copy from master if they don't exist
    required_files = [
        "adaptive_compressor.py",
        "marker_finder.py",
        "compression_methods.py", 
        "advanced_compression.py",
        "brotli_lzham_compression.py",
        "compression_analyzer.py",
        "simple_test.py",
        "test_compressor.py",
        "requirements.txt"
    ]
    
    # Check which files are missing
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if not missing_files:
        print("All required files are present.")
        return
    
    print(f"Missing {len(missing_files)} files. Will attempt to sync from master branch.")
    
    # Create a temporary branch to stage the sync
    temp_branch = "temp_sync_branch"
    
    try:
        # Checkout master to a temporary branch
        subprocess.run(["git", "checkout", "master", "-b", temp_branch], check=True)
        
        # Copy files to a temp location
        temp_dir = "temp_sync_files"
        os.makedirs(temp_dir, exist_ok=True)
        
        for file in missing_files:
            if os.path.exists(file):
                # Copy to temp directory
                subprocess.run(["cp", file, os.path.join(temp_dir, file)], check=True)
                print(f"Copied {file} to temp directory")
        
        # Checkout back to our branch
        subprocess.run(["git", "checkout", "detailed-documentation"], check=True)
        
        # Copy files from temp location
        for file in missing_files:
            temp_file = os.path.join(temp_dir, file)
            if os.path.exists(temp_file):
                subprocess.run(["cp", temp_file, file], check=True)
                print(f"Synced {file} from master")
        
        # Clean up temp directory
        subprocess.run(["rm", "-rf", temp_dir], check=True)
        
        # Delete temporary branch
        subprocess.run(["git", "branch", "-D", temp_branch], check=True)
        
        print("\nFiles synced successfully. You should now 'git add' the new files and commit them.")
    
    except subprocess.CalledProcessError as e:
        print(f"Error syncing files: {e}")
        print("\nManual sync required. Please checkout master branch, copy the missing files, and then check back to your branch.")

if __name__ == "__main__":
    main()
