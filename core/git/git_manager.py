# === CONTEXT START ===
# The GitManager class provides a higher-level orchestration layer for handling
# version-control operations within the AI-driven code-generation workflow. It
# acts as a coordinator that builds on top of the low-level GitClient, offering
# structured workflows such as preparing branches, committing generated files,
# synchronizing with remote repositories, and performing automated push
# sequences.
#
# This class does not execute Git commands directly; instead, it delegates all
# operations to an injected GitClient instance. This design allows the manager
# to enforce consistent commit-message formatting, embed AI-generated context
# into commit messages, and guarantee a predictable sequence of Git actions when
# new code is created or updated. It simplifies integration by providing clean,
# descriptive methods rather than exposing raw Git commands across the system.
#
# GitManager’s responsibilities include switching branches before development,
# committing output files produced by the AI along with their associated
# context, pulling the latest remote changes to avoid divergence, and pushing
# updates when required. By centralizing these routines, the framework avoids
# duplication and maintains a clear boundary between repository mechanics and
# high-level automation logic.
# === CONTEXT END ===


from typing import Optional

class GitClient:
    def checkout(self, branch: str) -> None:
        pass

    def add(self, file_path: str) -> None:
        pass

    def commit(self, message: str) -> str:
        pass

    def pull(self, remote: str, branch: str) -> None:
        pass

    def push(self, remote: str, branch: str) -> None:
        pass

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
        :return: The commit hash returned by the GitClient.
        """
        self.git_client.add(file_path)
        commit_message = f"Add generated file {file_path}. Context: {context}"
        return self.git_client.commit(commit_message)

    def sync_with_remote(self, remote: str = "origin", branch: str = "main") -> None:
        """
        Pull the latest changes from the specified remote and branch.

        :param remote: The remote repository name.
        :param branch: The branch name to pull from.
        """
        self.git_client.pull(remote, branch)

    def auto_push(self, commit_message: str, context: str = "") -> None:
        """
        Commit with the provided message and push to the remote.

        :param commit_message: The commit message to use.
        :param context: Additional context for the commit message.
        """
        full_message = f"{commit_message}. Context: {context}" if context else commit_message
        self.git_client.commit(full_message)
        self.git_client.push("origin", "main")
