# === CONTEXT START ===
# The GitClient class provides a lightweight wrapper around the Git command-line
# interface and exposes a clean Python API for core repository operations. It
# executes all git commands inside the configured repository path using
# subprocess.run, ensuring consistent behavior and strict error handling.
#
# This class supports all essential version-control actions required by the
# AI-driven code-generation workflow: initializing a repository, adding files,
# committing changes, switching branches, pulling updates, and pushing changes
# to a remote. All operations return the command output so higher-level
# components like GitManager can orchestrate Git actions without dealing with
# low-level shell details.
#
# All Git invocations flow through the private _run_git_command method, which
# handles argument assembly, working-directory selection, and command execution.
# This design keeps the API simple, predictable, and fully transparent. The
# implementation avoids external dependencies like GitPython to maintain
# portability and full visibility into git usage.
# === CONTEXT END ===


import subprocess
from typing import Union

class GitClient:
    def __init__(self, repo_path: str):
        """Initialize the GitClient with the path to the repository."""
        self.repo_path = repo_path

    def _run_git_command(self, *args: str) -> str:
        """Run a git command with the given arguments and return the output."""
        result = subprocess.run(
            ['git'] + list(args),
            cwd=self.repo_path,
            text=True,
            capture_output=True,
            check=True
        )
        return result.stdout.strip()

    def init_repo(self) -> None:
        """Initialize a new git repository."""
        self._run_git_command('init')

    def add(self, paths: Union[list[str], str]) -> str:
        """Add file contents to the index."""
        if isinstance(paths, str):
            paths = [paths]
        return self._run_git_command('add', *paths)

    def commit(self, message: str) -> str:
        """Record changes to the repository with a commit message."""
        return self._run_git_command('commit', '-m', message)

    def push(self, remote: str = "origin", branch: str = "main") -> str:
        """Update remote refs along with associated objects."""
        return self._run_git_command('push', remote, branch)

    def pull(self, remote: str = "origin", branch: str = "main") -> str:
        """Fetch from and integrate with another repository or a local branch."""
        return self._run_git_command('pull', remote, branch)

    def checkout(self, branch: str, create_if_missing: bool = False) -> str:
        """Switch branches or restore working tree files."""
        if create_if_missing:
            return self._run_git_command('checkout', '-b', branch)
        return self._run_git_command('checkout', branch)

    def status(self) -> str:
        """Show the working tree status."""
        return self._run_git_command('status')

    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        return self._run_git_command('rev-parse', '--abbrev-ref', 'HEAD')
