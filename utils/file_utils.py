import os
import re
import logging
from colorama import Fore, Style
import threading
from concurrent.futures import ThreadPoolExecutor
from .i18n_utils import _
from .common_utils import validate_path

def get_structure(folder_path, filter_folder=None, exclude_folders=None, exclude_extensions=None, indent=0):
    """Get the folder structure as a list of tuples (item, is_dir)."""
    try:
        folder_path = validate_path(folder_path)
        structure = []
        exclude_folders = exclude_folders or []
        exclude_extensions = exclude_extensions or []

        items = sorted(os.listdir(folder_path), key=lambda x: (not os.path.isdir(os.path.join(folder_path, x)), x))
        
        for item in items:
            item_path = os.path.join(folder_path, item)
            relative_path = os.path.relpath(item_path, folder_path)
            if filter_folder and filter_folder not in relative_path:
                continue
            if any(excluded in relative_path for excluded in exclude_folders):
                continue
            if os.path.isfile(item_path) and any(item.endswith(ext) for ext in exclude_extensions):
                continue
            
            prefix = "│   " * indent
            if os.path.isdir(item_path):
                structure.append((f"{prefix}├── [DIR] {relative_path}", True))
                sub_structure = get_structure(item_path, filter_folder, exclude_folders, exclude_extensions, indent + 1)
                structure.extend(sub_structure)
            else:
                structure.append((f"{prefix}├── [FILE] {relative_path}", False))
        
        return structure
    except Exception as e:
        logging.error(_(f"Could not process directory {folder_path}: {e}"))
        return []

def get_file_contents(folder_path, selected_files=None, filter_folder=None, exclude_folders=None, exclude_extensions=None, keyword=None, regex=None, min_size=0, modified_after=None):
    """Get contents of files in the folder, filtered by criteria."""
    try:
        folder_path = validate_path(folder_path)
        contents = []
        selected_files = selected_files or []
        exclude_folders = exclude_folders or []
        exclude_extensions = exclude_extensions or []

        sensitive_patterns = [
            r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # Credit card
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'(?i)password\s*=\s*["\'][^"\']+["\']'  # Password in config
        ]

        def process_file(file_path):
            try:
                relative_path = os.path.relpath(file_path, folder_path)
                if filter_folder and filter_folder not in relative_path:
                    return None
                if any(excluded in relative_path for excluded in exclude_folders):
                    return None
                if any(file_path.endswith(ext) for ext in exclude_extensions):
                    return None
                if min_size and os.path.getsize(file_path) < min_size:
                    return None
                if modified_after and os.path.getmtime(file_path) < modified_after.timestamp():
                    return None
                if selected_files and file_path not in selected_files:
                    return None

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    logging.info(_(f"Skipping binary file: {file_path}"))
                    return None

                if keyword and keyword.lower() not in content.lower():
                    return None
                if regex and not re.search(regex, content, re.MULTILINE):
                    return None

                for pattern in sensitive_patterns:
                    if re.search(pattern, content):
                        logging.warning(_( "Potential sensitive content detected in file"))
                        return None

                return f"----------------------------------------\nFile: {relative_path}\n----------------------------------------\n{content}\n"
            except Exception as e:
                logging.error(_(f"Could not read {file_path}: {e}"))
                return None

        with ThreadPoolExecutor() as executor:
            file_paths = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_paths.append(file_path)
            
            results = executor.map(process_file, file_paths)
            contents = [result for result in results if result]

        return "\n".join(contents)
    except Exception as e:
        logging.error(_(f"Could not process directory {folder_path}: {e}"))
        raise ValueError(_(f"Could not process directory {folder_path}: {e}"))