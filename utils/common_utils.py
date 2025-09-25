import os
from .i18n_utils import _

def validate_path(folder_path):
    """Validate the provided folder path."""
    if not os.path.exists(folder_path):
        raise ValueError(_(f"Path does not exist: {folder_path}"))
    if not os.path.isdir(folder_path):
        raise ValueError(_(f"Path is not a directory: {folder_path}"))
    return os.path.abspath(folder_path)