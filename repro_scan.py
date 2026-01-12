import os
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from core.git_status_provider import GitStatusProvider, FileStatus

def test_current_logic(folder):
    print(f"Testing current logic (os.walk) on {folder}...")
    start = time.time()
    
    all_files = []
    ignored_count = 0
    total_size = 0
    count = 0
    
    # Simulate the logic in main_window.py _calculate_upload_stats
    # Note: excluding the provider.is_ignored call for a fair baseline of walk speed
    # or we can mock it.
    
    for root, dirs, files in os.walk(folder):
        if '.git' in dirs: dirs.remove('.git')
        
        for f in files:
            count += 1
            if count % 5000 == 0:
                print(f"Scanned {count} files...")
            
            # Simulate basic ignore check overhead
            rel_path = os.path.relpath(os.path.join(root, f), folder)
            if "node_modules" in rel_path or "venv" in rel_path:
                ignored_count += 1
            else:
                all_files.append(rel_path)
                
    end = time.time()
    print(f"Current logic took {end - start:.4f}s. Files: {len(all_files)}, Ignored: {ignored_count}, Total scanned: {count}")

def test_proposed_logic(folder):
    print(f"Testing proposed logic (GitStatusProvider) on {folder}...")
    start = time.time()
    
    provider = GitStatusProvider(folder)
    files = provider.get_detailed_status()
    
    end = time.time()
    print(f"Proposed logic took {end - start:.4f}s. Files found: {len(files)}")

if __name__ == "__main__":
    folder = os.getcwd() # Assumption: running in the repo root
    # If standard user path
    user_path = r"C:\Users\Administrator.DESKTOP-EGNE9ND\Desktop\GitHub-git"
    if os.path.exists(user_path):
        folder = user_path
        
    print(f"Target folder: {folder}")
    if os.path.exists(os.path.join(folder, ".gitignore")):
        print("Found .gitignore")
    
    test_proposed_logic(folder)
    print("-" * 20)
    test_current_logic(folder)
