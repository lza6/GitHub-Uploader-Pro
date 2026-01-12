"""
GitHub Uploader Pro - Git Status Provider
解析本地 Git 状态，提供可视化数据支持
"""
import os
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from loguru import logger


@dataclass
class FileStatus:
    """单个文件状态"""
    path: str
    status: str       # M, A, D, R, C, U, ?, !
    staged: bool      # 是否在暂存区
    size: int         # 文件大小 (bytes)
    display_name: str # 相对路径


class GitStatusProvider:
    """
    Git 状态解析器
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
    
    def get_detailed_status(self) -> List[FileStatus]:
        """
        获取详细的文件状态列表
        """
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            # V4.7.2: 支持非 Git 目录的预览 - 全部标记为待上传
            files = []
            try:
                for root, dirs, filenames in os.walk(self.repo_path):
                    dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', 'venv')]
                    for filename in filenames:
                        abs_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(abs_path, self.repo_path)
                        files.append(FileStatus(
                            path=abs_path,
                            status="??", # 标记为未跟踪
                            staged=False,
                            size=os.path.getsize(abs_path),
                            display_name=rel_path
                        ))
            except Exception as e:
                logger.error(f"非 Git 目录扫描失败: {e}")
            return files
            
        try:
            # 使用 porcelain 格式解析状态
            # 格式: XY PATH [-> PATH2]
            # X: 暂存区状态, Y: 工作区状态
            result = subprocess.run(
                ["git", "status", "--porcelain", "-uall"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            
            if result.returncode != 0:
                return []
                
            files = []
            lines = result.stdout.splitlines()
            
            for line in lines:
                if len(line) < 4: continue
                
                status_code = line[:2]
                file_path = line[3:].strip('"') # 处理 Git 转义的引号
                
                # 处理重命名格式 "R  old -> new"
                if " -> " in file_path:
                    file_path = file_path.split(" -> ")[-1]
                
                abs_path = os.path.join(self.repo_path, file_path)
                size = 0
                if os.path.isfile(abs_path):
                    size = os.path.getsize(abs_path)
                
                # 状态逻辑简化
                # X != ' ' 表示在暂存区
                is_staged = status_code[0] != ' ' and status_code[0] != '?'
                
                files.append(FileStatus(
                    path=abs_path,
                    status=status_code,
                    staged=is_staged,
                    size=size,
                    display_name=file_path
                ))
                
            return files
            
        except Exception as e:
            logger.error(f"解析 Git 状态失败: {e}")
            return []

    def get_tracked_count(self) -> int:
        """获取当前已追踪（在仓库中）的文件数量"""
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            return 0
            
        try:
            # git ls-files 用于列出索引文件
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            if result.returncode != 0:
                return 0
            
            lines = [l for l in result.stdout.splitlines() if l.strip()]
            return len(lines)
        except Exception as e:
            logger.error(f"获取追踪文件数失败: {e}")
            return 0

    def get_summary(self, files: List[FileStatus]) -> Dict[str, Any]:
        """
        统计概要信息
        """
        total_staged_size = sum(f.size for f in files if f.staged)
        total_unstaged_size = sum(f.size for f in files if not f.staged)
        
        return {
            "staged_count": len([f for f in files if f.staged]),
            "staged_size": total_staged_size,
            "unstaged_count": len([f for f in files if not f.staged]),
            "unstaged_size": total_unstaged_size,
            "total_files": len(files)
        }

    def is_ignored(self, rel_path: str) -> bool:
        """
        判断指定路径是否被 Git 忽略
        """
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            # 非 Git 目录，使用手动检查
            return self._check_ignore_manual(rel_path)

        try:
            # 使用 git check-ignore 检查
            result = subprocess.run(
                ["git", "check-ignore", "-q", rel_path],
                cwd=self.repo_path,
                capture_output=True
            )
            # 返回码 0 表示被忽略，1 表示未被忽略
            if result.returncode == 0:
                return True
                
            # Double check with manual parser in case git fails or special cases
            return self._check_ignore_manual(rel_path)
            
        except Exception:
            return self._check_ignore_manual(rel_path)
        except Exception:
            return False

    def _check_ignore_manual(self, rel_path: str) -> bool:
        """
        手动检查是否被忽略 (Backup for non-git folders)
        简单实现，支持 * 通配符
        """
        import fnmatch
        
        ignore_file = os.path.join(self.repo_path, ".gitignore")
        if not os.path.exists(ignore_file):
            return False
            
        try:
            with open(ignore_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Normalize path to use forward slashes for gitignore matching
            rel_path_normalized = rel_path.replace('\\', '/')
            path_parts = rel_path_normalized.split('/')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # 简单的目录匹配 /directory/
                if line.endswith('/'):
                    # 如果规则是目录，检查路径中的任何部分是否匹配
                    pattern = line.rstrip('/')
                    if pattern in path_parts:
                        return True
                        
                # 简单的文件/通配符匹配 *.py, file.txt
                # Use normalized path for matching
                if fnmatch.fnmatch(rel_path_normalized, line) or fnmatch.fnmatch(os.path.basename(rel_path_normalized), line):
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Manual ignore check failed: {e}")
            return False

    def get_project_tree(self, max_depth: int = 3) -> str:
        """
        获取简略的项目目录树，供 AI 分析
        """
        tree_lines = []
        
        def _scan(path: str, depth: int):
            if depth > max_depth: return
            
            try:
                entries = sorted(os.listdir(path))
                for entry in entries:
                    if entry == ".git" or entry == "__pycache__": continue
                    
                    full_path = os.path.join(path, entry)
                    indent = "  " * (depth - 1)
                    if os.path.isdir(full_path):
                        tree_lines.append(f"{indent}📁 {entry}/")
                        _scan(full_path, depth + 1)
                    else:
                        tree_lines.append(f"{indent}📄 {entry}")
            except Exception:
                pass
                
        _scan(self.repo_path, 1)
        return "\n".join(tree_lines)
