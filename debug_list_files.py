import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

from core.git_status_provider import GitStatusProvider

def main():
    folder = os.getcwd()
    print(f"Scanning: {folder}")
    
    provider = GitStatusProvider(folder)
    
    all_files = []
    total_size = 0
    
    for root, dirs, files in os.walk(folder):
        if '.git' in dirs: dirs.remove('.git')
        
        # Don't manually exclude venv, let provider logic do it to test the bug
        # if 'venv' in dirs: dirs.remove('venv') 
        
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, folder).replace("\\", "/")
            
            # Check if ignored
            ignored = provider.is_ignored(rel_path)
            
            f_size = os.path.getsize(full_path)
            
            if not ignored:
                all_files.append((rel_path, f_size))
                total_size += f_size
                if f_size > 1024*1024:
                    print(f"[LARGE] {rel_path} : {f_size/1024/1024:.2f} MB")
            
    print(f"Total Files: {len(all_files)}")
    print(f"Total Size: {total_size/1024/1024:.2f} MB")
    
    # Print top 10 largest
    print("\nTop 10 Largest Files:")
    all_files.sort(key=lambda x: x[1], reverse=True)
    for p, s in all_files[:10]:
        print(f"{s/1024/1024:.2f} MB - {p}")

if __name__ == "__main__":
    main()
