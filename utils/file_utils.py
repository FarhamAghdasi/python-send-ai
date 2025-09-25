import os
import chardet
import logging
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from colorama import Fore, Style
import gettext

# Initialize i18n
lang = os.getenv("LANG", "en")
if lang == "fa":
    translation = gettext.translation("messages", localedir="locale", languages=["fa"])
    translation.install()
    _ = translation.gettext
else:
    _ = lambda x: x

def validate_path(folder_path):
    """Validate that the folder path exists and is a directory."""
    if not os.path.exists(folder_path):
        raise ValueError(_(f"Path does not exist: {folder_path}"))
    if not os.path.isdir(folder_path):
        raise ValueError(_(f"Path is not a directory: {folder_path}"))
    return os.path.abspath(folder_path)

def is_binary_file(file_path):
    """Check if a file is binary."""
    try:
        with open(file_path, "rb") as f:
            content = f.read(1024)
            result = chardet.detect(content)
            return result["confidence"] < 0.9 or result["encoding"] is None
    except Exception:
        return True

def check_sensitive_content(content):
    """Check for sensitive content like API keys."""
    sensitive_patterns = [
        r"API_KEY\s*=\s*['\"][A-Za-z0-9_-]+['\"]",  # Simple API key pattern
        r"SECRET_KEY\s*=\s*['\"][A-Za-z0-9_-]+['\"]"
    ]
    for pattern in sensitive_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logging.warning(_(f"Potential sensitive content detected in file"))
            return True
    return False

def get_structure(folder_path, indent=0, filter_folder=None, exclude_folders=None, exclude_extensions=None):
    if exclude_folders is None:
        exclude_folders = ['.git']
    if exclude_extensions is None:
        exclude_extensions = ['.svg', '.jpg', '.png', '.bin']

    structure = []
    try:
        folder_path = validate_path(folder_path)
        items = sorted(os.listdir(folder_path))  # Sort for consistent display
    except Exception as e:
        logging.error(_(f"Could not list directory {folder_path}: {e}"))
        return [(f"[ERROR] Could not list directory {folder_path}: {e}", False)]

    for index, item in enumerate(items):
        if item in exclude_folders:
            continue

        item_path = os.path.join(folder_path, item)
        is_last = index == len(items) - 1

        if os.path.isdir(item_path):
            if filter_folder and filter_folder not in item:
                continue

            structure.append(('    ' * (indent // 4) + ('└── ' if is_last else '├── ') + f'[DIR] {item}', True))
            structure.extend(get_structure(item_path, indent + 4, filter_folder, exclude_folders, exclude_extensions))
        else:
            file_ext = os.path.splitext(item)[1].lower()
            if file_ext in exclude_extensions:
                continue

            structure.append(('    ' * (indent // 4) + ('└── ' if is_last else '├── ') + f'[FILE] {item}', False))

    return structure

def read_file(file_path, keyword=None, regex=None):
    """Read file content with encoding detection."""
    if is_binary_file(file_path):
        logging.info(_(f"Skipping binary file: {file_path}"))
        return None

    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"] if result["encoding"] else "utf-8"
            content = raw_data.decode(encoding, errors="replace")
        
        if check_sensitive_content(content):
            print(f"{Fore.YELLOW}⚠ Warning: Sensitive content detected in {file_path}. Masking...{Style.RESET_ALL}")
            content = "[MASKED SENSITIVE CONTENT]"

        if keyword and keyword.lower() not in content.lower():
            return None
        if regex and not re.search(regex, content, re.IGNORECASE):
            return None
        return f"\n{'-' * 40}\nFile: {file_path}\n{'-' * 40}\n{content}\n"
    except Exception as e:
        logging.error(_(f"Could not read {file_path}: {e}"))
        return f"\n[ERROR] Could not read {file_path}: {e}\n"

def get_file_contents(folder_path, selected_files, filter_folder=None, exclude_folders=None, exclude_extensions=None, keyword=None, regex=None, min_size=0, modified_after=None):
    if exclude_folders is None:
        exclude_folders = ['.git']
    if exclude_extensions is None:
        exclude_extensions = ['.svg', '.jpg', '.png', '.bin']

    contents = ""
    file_list = []
    try:
        folder_path = validate_path(folder_path)
        for file_path in selected_files:
            if not os.path.isfile(file_path):
                continue
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in exclude_extensions:
                continue
            if any(exclude_folder in os.path.normpath(file_path).split(os.sep) for exclude_folder in exclude_folders):
                continue
            if filter_folder and filter_folder not in file_path:
                continue
            if min_size > 0 and os.path.getsize(file_path) < min_size:
                continue
            if modified_after:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mtime < modified_after:
                    continue
            file_list.append(file_path)
    except Exception as e:
        logging.error(_(f"Could not process directory {folder_path}: {e}"))
        return f"[ERROR] Could not process directory {folder_path}: {e}\n"

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(tqdm(
            executor.map(lambda f: read_file(f, keyword, regex), file_list),
            total=len(file_list),
            desc=_( "Processing files"),
            unit="file"
        ))
    
    return "".join([r for r in results if r])