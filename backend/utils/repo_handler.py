import os
import shutil
import tempfile
from pathlib import Path
from typing import Set, Tuple, Dict, List
from git import Repo, GitCommandError


class RepoHandler:
    IGNORE_DIRS = {
        '.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env',
        '.tox', '.mypy_cache', '.pytest_cache', 'build', 'dist',
        '.eggs', '*.egg-info', '.idea', '.vscode', 'target',
        'vendor', 'third_party', '.gradle', 'out', 'bin', 'obj',
    }

    MAX_FILE_SIZE = 1024 * 1024
    MAX_FILES = 500

    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def clone_repository(self, repo_url: str, branch: str = 'main') -> Tuple[str, Dict]:
        repo_dir = tempfile.mkdtemp(dir=self.base_dir)
        try:
            repo = Repo.clone_from(
                repo_url, repo_dir,
                branch=branch,
                depth=1,
                single_branch=True,
                no_checkout=False
            )
        except GitCommandError:
            try:
                repo = Repo.clone_from(
                    repo_url, repo_dir,
                    branch='master',
                    depth=1,
                    single_branch=True,
                    no_checkout=False
                )
                branch = 'master'
            except GitCommandError as e:
                shutil.rmtree(repo_dir, ignore_errors=True)
                raise RuntimeError(f"Failed to clone repository: {str(e)}")

        commit = repo.head.commit
        repo_info = {
            'url': repo_url,
            'branch': branch,
            'commit_hash': str(commit.hexsha)[:8],
            'commit_message': commit.message.strip()[:200],
            'author': str(commit.author),
            'name': repo_url.rstrip('/').split('/')[-1].replace('.git', ''),
        }

        return repo_dir, repo_info

    def discover_source_files(self, repo_path: str, supported_extensions: Set[str]) -> List[str]:
        source_files = []
        repo_root = Path(repo_path)

        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith('.')]

            for fname in sorted(files):
                if len(source_files) >= self.MAX_FILES:
                    break

                ext = Path(fname).suffix.lower()
                if ext not in supported_extensions:
                    continue

                full_path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(full_path)
                    if size > self.MAX_FILE_SIZE or size < 10:
                        continue
                    source_files.append(full_path)
                except OSError:
                    continue

        return source_files
