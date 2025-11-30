from dataclasses import dataclass

@dataclass
class RepoConfig:
    """
    Configuration for a repository.

    Attributes:
        repo_path (str): The file path to the repository.
        default_branch (str): The default branch of the repository. Defaults to 'master'.
        remote_name (str): The name of the remote. Defaults to 'origin'.
        author_name (str): The name of the author. Defaults to 'AI Agent'.
        author_email (str): The email of the author. Defaults to 'ai@example.com'.
    """
    repo_path: str
    default_branch: str = "master"
    remote_name: str = "origin"
    author_name: str = "AI Agent"
    author_email: str = "ai@example.com"
