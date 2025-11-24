# === CONTEXT START ===
# Added the import for generate_profile_file to ensure it self-registers in the
# ActionRegistry. Preserved existing imports and comments, including keeping
# git_commit_and_push commented out. Maintained consistent formatting and kept the
# # noqa: F401 comments.
# === CONTEXT END ===

# core/actions/__init__.py

# Import all action modules here so they self-register in the registry.
from . import generate_class_file  # noqa: F401
# from . import git_commit_and_push  # noqa: F401
from . import generate_test_file   # noqa: F401
from . import continue_action      # noqa: F401
from . import generate_profile_file  # noqa: F401
