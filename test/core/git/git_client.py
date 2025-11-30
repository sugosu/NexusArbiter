# === CONTEXT START ===
# This module defines the GitClient class, which provides methods to interact
# with a Git repository. It includes functionalities to initialize a repository,
# add files, commit changes, push to a remote, pull from a remote, checkout
# branches, and get the current branch status. The refactoring removes the
# hardcoded 'master' branch default, allowing for a more flexible branch
# handling by defaulting to 'main' if no branch is specified.
# === CONTEXT END ===

import subprocess
from typing import Union
from core.logger import BasicLogger

class GitClient:
    def __init__(self, repo_path: str):
        """Initialize the GitClient with the path to the repository."""
        self.repo_path = repo_path
        self.logger = BasicLogger(self.__class__.__name__).get_logger()

    def _run_git_command(self, *args: str) -> str:
        self.logger.info(f'Running git command: {args}')
        try:
            result = subprocess.run(
                ['git'] + list(args),
                cwd=self.repo_path,
                text=True,
                capture_output=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as exc:
            stdout_msg = (exc.stdout or "").strip()
            stderr_msg = (exc.stderr or "").strip()

            if stdout_msg:
                self.logger.error(f"Git stdout (cmd: {args}): {stdout_msg}")
            if stderr_msg:
                self.logger.error(f"Git stderr (cmd: {args}): {stderr_msg}")

            # Re-raise so the caller still gets the failure
            raise

    def init_repo(self) -> None:
        """Initialize a new git repository."""
        self.logger.info('Initializing repository')
        self._run_git_command('init')

    def add(self, paths: Union[list[str], str]) -> str:
        """Add file contents to the index."""
        self.logger.info(f'Adding paths: {paths}')
        if isinstance(paths, str):
            paths = [paths]
        return self._run_git_command('add', *paths)

    def commit(self, message: str) -> str:
        """Record changes to the repository with a commit message."""
        self.logger.info(f'Committing with message: {message}')
        return self._run_git_command('commit', '-m', message)

    def push(self, remote: str = "origin", branch: str = None) -> str:
        """Update remote refs along with associated objects."""
        branch = branch or 'main'
        self.logger.info(f'Pushing to {remote}/{branch}')
        return self._run_git_command('push', remote, branch)

    def pull(self, remote: str = "origin", branch: str = None) -> str:
        """Fetch from and integrate with another repository or a local branch."""
        branch = branch or 'main'
        self.logger.info(f'Pulling from {remote}/{branch}')
        return self._run_git_command('pull', remote, branch)

    def checkout(self, branch: str, create_if_missing: bool = False) -> str:
        """Switch branches or restore working tree files."""
        self.logger.info(f'Checking out branch: {branch}, create if missing: {create_if_missing}')
        if create_if_missing:
            return self._run_git_command('checkout', '-b', branch)
        return self._run_git_command('checkout', branch)

    def status(self) -> str:
        """Show the working tree status."""
        self.logger.info('Getting status')
        return self._run_git_command('status')

    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        self.logger.info('Getting current branch')
        return self._run_git_command('rev-parse', '--abbrev-ref', 'HEAD')
