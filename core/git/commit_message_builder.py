# === CONTEXT START ===
# The CommitMessageBuilder class is designed to create standardized commit
# messages for version control systems. It includes a static method 'build' that
# constructs a commit message using the file name, a short description, a detailed
# context, and the author's name. This utility can be used to ensure consistency
# in commit messages across a project.
# === CONTEXT END ===

class CommitMessageBuilder:
    """
    A utility class to build commit messages for version control.
    """

    @staticmethod
    def build(file_path: str, context: str, author: str = "AI_Agent") -> str:
        """
        Builds a formatted commit message.

        :param file_path: The path of the file being committed.
        :param context: A detailed, multi-line description of the changes.
        :param author: The author of the commit, default is 'AI_Agent'.
        :return: A formatted commit message string.
        """
        filename = file_path.split('/')[-1]
        short_description = f"Update {filename}"
        commit_message = f"{short_description}\n\n{context}\n\nAuthor: {author}"
        return commit_message
