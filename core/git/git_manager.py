# core/git/git_manager.py

# === CONTEXT START ===
# The GitManager class provides a higher-level orchestration layer for handling
# version-control operations within the AI-driven code-generation workflow.
# === CONTEXT END ===

from typing import Optional
from core.git.git_client import GitClient  # adjust path if different


class GitManager:
    def __init__(self, git_client: GitClient) -> None:
        self.git_client = git_client

    def prepare_branch(self, branch: str) -> None:
        """
        Checkout the specified branch using the GitClient.
        """
        self.git_client.checkout(branch)

    def commit_generated_file(self, file_path: str, context: str) -> str:
        """
        Add the specified file and commit it with a message including the context.

        :param file_path: Path to the file to be committed.
        :param context: Context to include in the commit message.
        :return: The commit hash or output returned by the GitClient.
        """
        self.git_client.add(file_path)
        commit_message = f"Add/update generated file {file_path}. Context: {context[:120]}"
        return self.git_client.commit(commit_message)

    def sync_with_remote(self, remote: str = "origin", branch: str = "master") -> None:
        """
        Pull the latest changes from the specified remote and branch.
        """
        self.git_client.pull(remote, branch)

    def auto_push(self, commit_message: str, context: str = "") -> None:
        """
        Commit with the provided message and push to the remote.
        """
        full_message = (
            f"{commit_message}. Context: {context[:120]}" if context else commit_message
        )
        self.git_client.commit(full_message)
        self.git_client.push("origin", "master")
