import os
import platform
import argparse
import json
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import chardet
from colorama import init, Fore, Style
from tqdm import tqdm
import markdown2
import pyperclip
import git
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import gettext
import shutil
import sys

# Import msvcrt only on Windows
if platform.system() == "Windows":
    import msvcrt
else:
    import tty
    import termios

# Initialize i18n
lang = os.getenv("LANG", "en")

try:
    if lang.startswith("fa"):
        translation = gettext.translation("messages", localedir="locale", languages=["fa"])
        translation.install()
        _ = translation.gettext
    else:
        _ = lambda x: x
except FileNotFoundError:
    # If no translation files exist, fallback to English
    _ = lambda x: x

# Prompt Templates
PROMPT_TEMPLATES = {
    "code_review": {
        "name": "Code Review & Improvement",
        "template": """Please carefully review this project and perform the following tasks:

1. **Analyze the complete structure** - Understand the architecture, patterns, and organization
2. **Identify issues** - Find bugs, code smells, security vulnerabilities, and performance bottlenecks
3. **Suggest improvements** - Provide specific recommendations for:
   - Code quality and readability
   - Performance optimizations
   - Security enhancements
   - Better design patterns
   - Missing error handling
4. **Prioritize changes** - Rank suggestions by impact and effort

Project Structure and Files:
---
"""
    },
    "documentation": {
        "name": "Documentation Generation",
        "template": """Please generate comprehensive documentation for this project:

1. **Overview** - Project purpose, key features, and architecture
2. **Setup Instructions** - Installation, configuration, and dependencies
3. **API Documentation** - All public functions, classes, and methods with parameters and return values
4. **Usage Examples** - Common use cases with code snippets
5. **Contributing Guidelines** - How to contribute, coding standards, and PR process
6. **Troubleshooting** - Common issues and solutions

Project Structure and Files:
---
"""
    },
    "commit_messages": {
        "name": "Generate Commit Messages",
        "template": """For each change you suggest or make, provide a commit message following the Conventional Commits standard:

Format: <type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, perf, test, chore
Example: "feat(auth): add JWT token validation"

Include:
- Clear, concise description (50 chars max for subject)
- Detailed body explaining what and why (if needed)
- Breaking changes notation if applicable

Project Structure and Files:
---
"""
    }
}

# Default settings for different project types
PROJECT_DEFAULTS = {
    "python": {
        "exclude_folders": [".git", ".venv", "__pycache__", "venv", "env", ".pytest_cache", ".mypy_cache", "dist", "build", "*.egg-info"],
        "exclude_extensions": [".svg", ".pyc", ".jpg", ".png", ".bin", ".pyo", ".pyd", ".so", ".dll"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "nodejs": {
        "exclude_folders": [".git", "node_modules", "dist", "build", ".next", "coverage"],
        "exclude_extensions": [".svg", ".log", ".jpg", ".png", ".bin", ".map"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "java": {
        "exclude_folders": [".git", "target", ".idea", "build", "out"],
        "exclude_extensions": [".svg", ".class", ".jpg", ".png", ".bin", ".jar"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "go": {
        "exclude_folders": [".git", "vendor", "bin"],
        "exclude_extensions": [".svg", ".jpg", ".png", ".bin"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "csharp": {
        "exclude_folders": [".git", "bin", "obj", "packages", ".vs"],
        "exclude_extensions": [".svg", ".dll", ".exe", ".pdb", ".jpg", ".png"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "php": {
        "exclude_folders": [".git", "vendor", "cache"],
        "exclude_extensions": [".svg", ".jpg", ".png", ".bin"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "generic": {
        "exclude_folders": [".git"],
        "exclude_extensions": [".svg", ".jpg", ".png", ".bin"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    }
}

PROJECT_COLORS = {
    "python": Fore.MAGENTA,
    "nodejs": Fore.YELLOW,
    "java": Fore.GREEN,
    "go": Fore.BLUE,
    "csharp": Fore.CYAN,
    "php": Fore.LIGHTMAGENTA_EX,
    "generic": Fore.WHITE
}

def setup_logging(log_file):
    """Setup logging configuration."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def validate_path(folder_path):
    """Validate that the folder path exists and is a directory."""
    if not os.path.exists(folder_path):
        raise ValueError(_(f"Path does not exist: {folder_path}"))
    if not os.path.isdir(folder_path):
        raise ValueError(_(f"Path is not a directory: {folder_path}"))
    return os.path.abspath(folder_path)

def get_folder_size(folder_path):
    """Calculate total size of folder in bytes."""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
    except Exception:
        pass
    return total

def format_size(bytes_size):
    """Format bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"

def get_size_color(bytes_size):
    """Get color based on file/folder size."""
    mb = bytes_size / (1024 * 1024)
    if mb > 10:
        return Fore.RED
    elif mb > 5:
        return Fore.YELLOW
    else:
        return Fore.GREEN

def detect_project_type_advanced(folder_path):
    """Advanced project type detection based on files and structure."""
    try:
        folder_path = validate_path(folder_path)
        
        # Count files by extension
        file_counts = {}
        total_files = 0
        
        for root, dirs, files in os.walk(folder_path):
            # Skip common exclude folders
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '.venv', 'vendor']]
            
            for file in files:
                total_files += 1
                ext = os.path.splitext(file)[1].lower()
                file_counts[ext] = file_counts.get(ext, 0) + 1
        
        if total_files == 0:
            return "generic", 0
        
        # Check for specific project files first
        items = os.listdir(folder_path)
        
        # Python indicators
        python_files = [f for f in ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "poetry.lock"] if f in items]
        python_percentage = (file_counts.get('.py', 0) / total_files) * 100
        
        # Node.js indicators
        nodejs_files = [f for f in ["package.json", "npm-shrinkwrap.json", "yarn.lock", "package-lock.json"] if f in items]
        js_percentage = ((file_counts.get('.js', 0) + file_counts.get('.ts', 0) + file_counts.get('.jsx', 0) + file_counts.get('.tsx', 0)) / total_files) * 100
        
        # Java indicators
        java_files = [f for f in ["pom.xml", "build.gradle", "build.gradle.kts"] if f in items]
        java_percentage = (file_counts.get('.java', 0) / total_files) * 100
        
        # Go indicators
        go_files = [f for f in ["go.mod", "go.sum"] if f in items]
        go_percentage = (file_counts.get('.go', 0) / total_files) * 100
        
        # C# indicators
        csharp_files = [f for f in items if f.endswith('.csproj') or f.endswith('.sln')]
        csharp_percentage = (file_counts.get('.cs', 0) / total_files) * 100
        
        # PHP indicators
        php_files = [f for f in ["composer.json", "composer.lock"] if f in items]
        php_percentage = (file_counts.get('.php', 0) / total_files) * 100
        
        # Determine project type with confidence
        scores = {
            "python": (len(python_files) * 30 + python_percentage),
            "nodejs": (len(nodejs_files) * 30 + js_percentage),
            "java": (len(java_files) * 30 + java_percentage),
            "go": (len(go_files) * 30 + go_percentage),
            "csharp": (len(csharp_files) * 30 + csharp_percentage),
            "php": (len(php_files) * 30 + php_percentage)
        }
        
        if max(scores.values()) > 0:
            detected_type = max(scores, key=scores.get)
            confidence = min(scores[detected_type], 100)
            return detected_type, confidence
        
    except Exception as e:
        logging.error(_(f"Error detecting project type: {e}"))
    
    return "generic", 0

def minify_content(content, file_ext):
    """Minify file content to reduce size."""
    if not content:
        return content
    
    # Remove comments for various languages
    if file_ext in ['.py']:
        # Remove Python comments but keep docstrings
        lines = content.split('\n')
        minified_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if '"""' in stripped or "'''" in stripped:
                in_docstring = not in_docstring
                minified_lines.append(line)
            elif not in_docstring and stripped.startswith('#'):
                continue
            elif stripped:
                minified_lines.append(line)
        content = '\n'.join(minified_lines)
    
    elif file_ext in ['.js', '.ts', '.jsx', '.tsx', '.java', '.cs', '.go', '.php']:
        # Remove single line comments
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    elif file_ext in ['.html', '.xml']:
        # Remove HTML/XML comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    elif file_ext in ['.css', '.scss']:
        # Remove CSS comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove excessive whitespace
    content = re.sub(r'\n\s*\n', '\n\n', content)
    
    return content

def clone_remote_repo(remote_url, temp_dir="temp_repo"):
    """Clone a remote git repository to a temporary directory."""
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    try:
        logging.info(_(f"Cloning repository: {remote_url}"))
        git.Repo.clone_from(remote_url, temp_dir)
        return temp_dir
    except Exception as e:
        logging.error(_(f"Failed to clone repository: {e}"))
        raise

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
        r"API_KEY\s*=\s*['\"][A-Za-z0-9_-]+['\"]",
        r"SECRET_KEY\s*=\s*['\"][A-Za-z0-9_-]+['\"]",
        r"password\s*=\s*['\"][^'\"]+['\"]",
        r"token\s*=\s*['\"][A-Za-z0-9_-]+['\"]"
    ]
    for pattern in sensitive_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logging.warning(_(f"Potential sensitive content detected in file"))
            return True
    return False

def get_structure(folder_path, indent=0, filter_folder=None, exclude_folders=None, exclude_extensions=None):
    """Get folder structure with size information."""
    if exclude_folders is None:
        exclude_folders = ['.git']
    if exclude_extensions is None:
        exclude_extensions = ['.svg', '.jpg', '.png', '.bin']

    structure = ""
    try:
        folder_path = validate_path(folder_path)
        items = os.listdir(folder_path)
    except Exception as e:
        logging.error(_(f"Could not list directory {folder_path}: {e}"))
        return f"[ERROR] Could not list directory {folder_path}: {e}\n"

    for index, item in enumerate(items):
        if item in exclude_folders:
            continue

        item_path = os.path.join(folder_path, item)
        is_last = index == len(items) - 1

        if os.path.isdir(item_path):
            if filter_folder and filter_folder not in item:
                continue

            size = get_folder_size(item_path)
            structure += '    ' * (indent // 4)
            structure += '└── ' if is_last else '├── '
            structure += f'[DIR] {item} ({format_size(size)})\n'

            structure += get_structure(item_path, indent + 4, filter_folder, exclude_folders, exclude_extensions)
        else:
            file_ext = os.path.splitext(item)[1].lower()
            if file_ext in exclude_extensions:
                continue

            size = os.path.getsize(item_path)
            structure += '    ' * (indent // 4)
            structure += ('└── ' if is_last else '├── ') + f'[FILE] {item} ({format_size(size)})\n'

    return structure

def read_file(file_path, keyword=None, regex=None, minify=False):
    """Read file content with encoding detection and optional minification."""
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

        # Apply minification if enabled
        if minify and content != "[MASKED SENSITIVE CONTENT]":
            file_ext = os.path.splitext(file_path)[1].lower()
            content = minify_content(content, file_ext)

        if keyword and keyword.lower() not in content.lower():
            return None
        if regex and not re.search(regex, content, re.IGNORECASE):
            return None
        
        return f"\n{'-' * 40}\nFile: {file_path}\n{'-' * 40}\n{content}\n"
    except Exception as e:
        logging.error(_(f"Could not read {file_path}: {e}"))
        return f"\n[ERROR] Could not read {file_path}: {e}\n"

def get_file_contents(folder_path, filter_folder=None, exclude_folders=None, exclude_extensions=None, 
                     keyword=None, regex=None, min_size=0, modified_after=None, minify=False, 
                     selected_files=None):
    """Get file contents with optional file selection."""
    if exclude_folders is None:
        exclude_folders = ['.git']
    if exclude_extensions is None:
        exclude_extensions = ['.svg', '.jpg', '.png', '.bin']

    contents = ""
    file_list = []
    
    try:
        folder_path = validate_path(folder_path)
        for root, dirs, files in os.walk(folder_path):
            path_parts = os.path.normpath(root).split(os.sep)
            if any(part in exclude_folders for part in path_parts):
                continue
            if filter_folder and filter_folder not in root:
                continue
            
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in exclude_extensions:
                    continue
                
                file_path = os.path.join(root, file)
                
                # Check if file is in selected files (if selection is active)
                if selected_files is not None:
                    rel_path = os.path.relpath(file_path, folder_path)
                    if rel_path not in selected_files:
                        continue
                
                if min_size > 0 and os.path.getsize(file_path) < min_size:
                    continue
                
                if modified_after:
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < modified_after:
                        continue
                
                file_list.append(file_path)
    except Exception as e:
        logging.error(_(f"Could not process directory {folder_path}: {e}"))
        return f"[ERROR] Could not process directory {folder_path}: {e}\n"

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(tqdm(
            executor.map(lambda f: read_file(f, keyword, regex, minify), file_list),
            total=len(file_list),
            desc=_("Processing files"),
            unit="file"
        ))
    
    return "".join([r for r in results if r])

def format_output(structure, contents, output_format="txt", prompt_template=None):
    """Format output with optional prompt template."""
    final_output = ""
    
    # Add prompt template if selected
    if prompt_template:
        final_output += prompt_template + "\n\n"
    
    if output_format == "json":
        output_dict = {
            "prompt": prompt_template if prompt_template else "",
            "folder_structure": structure,
            "file_contents": contents
        }
        return json.dumps(output_dict, indent=2, ensure_ascii=False)
    elif output_format == "md":
        output = f"# {_('Project Structure')}\n\n```tree\n{structure}\n```\n\n# {_('File Contents')}\n\n```text\n{contents}\n```"
        return final_output + output
    elif output_format == "html":
        md_content = f"# {_('Project Structure')}\n\n```tree\n{structure}\n```\n\n# {_('File Contents')}\n\n```text\n{contents}\n```"
        return final_output + markdown2.markdown(md_content)
    else:  # txt
        output = f"{_('Folder Structure')}:\n{structure}\n\n{_('File Contents')}:{contents}"
        return final_output + output

def save_and_open(output, folder_path, output_format="txt", split_if_large=True, copy_to_clipboard=False):
    """Save output to file and optionally open it."""
    try:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        os.makedirs(output_dir, exist_ok=True)

        extension = {"txt": "txt", "json": "json", "md": "md", "html": "html"}[output_format]
        max_size = 12000

        if copy_to_clipboard:
            pyperclip.copy(output)
            logging.info(_("Output copied to clipboard"))

        if split_if_large and len(output) > max_size:
            print(f"{Fore.YELLOW}⚠ {_('Output exceeds {max_size:,} characters.').format(max_size=max_size)}{Style.RESET_ALL}")
            user_choice = input(f"{_('Split into multiple files? (y/n):')} ").strip().lower()
            if user_choice == "y":
                parts = [output[i:i+max_size] for i in range(0, len(output), max_size)]
                saved_paths = []
                for idx, part in enumerate(parts, start=1):
                    filename = f"project_structure_part{idx}.{extension}"
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(part)
                    saved_paths.append(filepath)
                logging.info(_(f"Output saved in {len(saved_paths)} files"))
                return saved_paths

        filename = f"project_structure_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output)

        try:
            if platform.system() == 'Windows':
                os.startfile(filepath)
            elif platform.system() == 'Darwin':
                os.system(f'open "{filepath}"')
            else:
                os.system(f'xdg-open "{filepath}"')
        except Exception as e:
            logging.warning(_(f"Could not open file {filepath}: {e}"))

        return filepath
    except Exception as e:
        logging.error(_(f"Error saving output: {e}"))
        raise ValueError(_(f"Error saving output: {e}"))

def load_config(project_type="generic"):
    """Load configuration from config.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    default_config = {"projects": PROJECT_DEFAULTS}
    config = default_config.copy()

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
        except Exception as e:
            logging.warning(_(f"Could not load config.json: {e}"))

    return config["projects"].get(project_type, PROJECT_DEFAULTS["generic"])

def getch():
    """Get a single character from standard input - works on Windows, Linux, and macOS."""
    if platform.system() == 'Windows':
        # Windows handling
        char = msvcrt.getch()
        # Check for special keys (arrows, function keys, etc.)
        if char in (b'\x00', b'\xe0'):  # Special key prefix
            char = msvcrt.getch()  # Get the actual key code
            # Map Windows arrow key codes
            key_map = {
                b'H': 'UP',      # Up arrow
                b'P': 'DOWN',    # Down arrow
                b'K': 'LEFT',    # Left arrow
                b'M': 'RIGHT',   # Right arrow
            }
            return key_map.get(char, char.decode('utf-8', errors='ignore'))
        else:
            try:
                return char.decode('utf-8', errors='ignore')
            except:
                return ''
    else:
        # Linux/macOS handling
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            
            # Check for escape sequences (arrow keys)
            if ch == '\x1b':  # ESC
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    # Map Unix arrow key codes
                    key_map = {
                        'A': 'UP',
                        'B': 'DOWN',
                        'C': 'RIGHT',
                        'D': 'LEFT'
                    }
                    return key_map.get(ch3, ch3)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def select_from_list(items, title="Select an option", multi_select=False):
    """Interactive list selection with arrow keys - works on all platforms."""
    if not items:
        return None
        
    current = 0
    selected = set() if multi_select else None
    
    # Import colorama for cross-platform colors
    from colorama import init, Fore, Style
    init()
    
    while True:
        # Clear screen
        os.system('cls' if platform.system() == 'Windows' else 'clear')
        
        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
        if multi_select:
            print(f"{Fore.YELLOW}Use ↑↓ to navigate, SPACE to select, ENTER to confirm, Q to quit{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Use ↑↓ to navigate, ENTER to select, Q to quit{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
        
        # Display items
        for idx, item in enumerate(items):
            prefix = "> " if idx == current else "  "
            
            if multi_select:
                checkbox = "[X]" if idx in selected else "[ ]"
                marker = f"{checkbox} "
            else:
                marker = ""
            
            if idx == current:
                print(f"{Fore.GREEN}{prefix}{marker}{item}{Style.RESET_ALL}")
            elif multi_select and idx in selected:
                print(f"{Fore.CYAN}{prefix}{marker}{item}{Style.RESET_ALL}")
            else:
                print(f"{prefix}{marker}{item}")
        
        # Get user input
        key = getch()
        
        # Handle key presses
        if key == 'UP':
            current = (current - 1) % len(items)
        elif key == 'DOWN':
            current = (current + 1) % len(items)
        elif key == 'LEFT' and multi_select:
            # Optional: can be used for other navigation
            pass
        elif key == 'RIGHT' and multi_select:
            # Optional: can be used for other navigation
            pass
        elif key in ['\r', '\n']:  # Enter
            if multi_select:
                return [items[i] for i in sorted(selected)] if selected else []
            else:
                return items[current]
        elif key == ' ' and multi_select:  # Space for multi-select
            if current in selected:
                selected.remove(current)
            else:
                selected.add(current)
        elif key.lower() == 'q':
            return None
        elif key == '\x1b':  # ESC key
            return None

def interactive_file_browser(folder_path, exclude_folders=None, exclude_extensions=None):
    """Interactive file browser with selection capability - Fixed for all platforms."""
    from colorama import Fore, Style
    
    if exclude_folders is None:
        exclude_folders = ['.git']
    if exclude_extensions is None:
        exclude_extensions = ['.svg', '.jpg', '.png', '.bin']
    
    # Validate path
    if not os.path.exists(folder_path):
        print(f"{Fore.RED}Error: Path does not exist: {folder_path}{Style.RESET_ALL}")
        return None
    if not os.path.isdir(folder_path):
        print(f"{Fore.RED}Error: Path is not a directory: {folder_path}{Style.RESET_ALL}")
        return None
    
    folder_path = os.path.abspath(folder_path)
    
    # Build file tree
    file_tree = {}
    all_files = []
    
    for root, dirs, files in os.walk(folder_path):
        # Filter directories
        dirs[:] = [d for d in dirs if d not in exclude_folders]
        
        rel_root = os.path.relpath(root, folder_path)
        if rel_root == '.':
            rel_root = '/'
        
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in exclude_extensions:
                continue
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, folder_path)
            try:
                size = os.path.getsize(file_path)
            except:
                size = 0
            
            all_files.append({
                'path': rel_path,
                'full_path': file_path,
                'name': file,
                'size': size,
                'dir': rel_root
            })
    
    # Group by directory
    for file_info in all_files:
        dir_name = file_info['dir']
        if dir_name not in file_tree:
            file_tree[dir_name] = []
        file_tree[dir_name].append(file_info)
    
    if not file_tree:
        print(f"{Fore.YELLOW}No files found in the specified directory.{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return []
    
    selected_files = set()
    current_dir = 0
    current_file = 0
    view_mode = 'dirs'  # 'dirs' or 'files'
    
    dirs = sorted(file_tree.keys())
    
    def format_size(bytes_size):
        """Format bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}TB"
    
    def get_size_color(bytes_size):
        """Get color based on file/folder size."""
        mb = bytes_size / (1024 * 1024)
        if mb > 10:
            return Fore.RED
        elif mb > 5:
            return Fore.YELLOW
        else:
            return Fore.GREEN
    
    while True:
        # Clear screen
        os.system('cls' if platform.system() == 'Windows' else 'clear')
        
        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Interactive File Browser - {folder_path}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Selected: {len(selected_files)} files{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Commands: ↑↓=Navigate | →=Enter Dir | ←=Back | SPACE=Select | A=Select All | "
              f"N=Deselect All | ENTER=Done | Q=Quit{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
        
        if view_mode == 'dirs':
            print(f"{Fore.GREEN}Directories:{Style.RESET_ALL}\n")
            for idx, dir_name in enumerate(dirs):
                file_count = len(file_tree[dir_name])
                total_size = sum(f['size'] for f in file_tree[dir_name])
                size_str = format_size(total_size)
                size_color = get_size_color(total_size)
                
                prefix = "> " if idx == current_dir else "  "
                selected_count = sum(1 for f in file_tree[dir_name] if f['path'] in selected_files)
                status = f"[{selected_count}/{file_count}]" if selected_count > 0 else ""
                
                if idx == current_dir:
                    print(f"{Fore.GREEN}{prefix}📁 {dir_name} {status} ({file_count} files, {size_color}{size_str}{Style.RESET_ALL})")
                else:
                    print(f"{prefix}📁 {dir_name} {status} ({file_count} files, {size_color}{size_str}{Style.RESET_ALL})")
        
        else:  # view_mode == 'files'
            current_dir_name = dirs[current_dir]
            files_in_dir = file_tree[current_dir_name]
            
            print(f"{Fore.GREEN}Files in: {current_dir_name}{Style.RESET_ALL}\n")
            for idx, file_info in enumerate(files_in_dir):
                size_str = format_size(file_info['size'])
                size_color = get_size_color(file_info['size'])
                
                prefix = "> " if idx == current_file else "  "
                checkbox = "[X]" if file_info['path'] in selected_files else "[ ]"
                
                if idx == current_file:
                    print(f"{Fore.GREEN}{prefix}{checkbox} 📄 {file_info['name']} ({size_color}{size_str}{Style.RESET_ALL})")
                elif file_info['path'] in selected_files:
                    print(f"{Fore.CYAN}{prefix}{checkbox} 📄 {file_info['name']} ({size_color}{size_str}{Style.RESET_ALL})")
                else:
                    print(f"{prefix}{checkbox} 📄 {file_info['name']} ({size_color}{size_str}{Style.RESET_ALL})")
        
        # Get user input
        key = getch()
        
        # Handle key presses
        if key == 'UP':
            if view_mode == 'dirs':
                current_dir = (current_dir - 1) % len(dirs)
            else:
                current_file = (current_file - 1) % len(file_tree[dirs[current_dir]])
        elif key == 'DOWN':
            if view_mode == 'dirs':
                current_dir = (current_dir + 1) % len(dirs)
            else:
                current_file = (current_file + 1) % len(file_tree[dirs[current_dir]])
        elif key == 'RIGHT':
            if view_mode == 'dirs':
                view_mode = 'files'
                current_file = 0
        elif key == 'LEFT':
            if view_mode == 'files':
                view_mode = 'dirs'
        elif key in ['\r', '\n']:  # Enter
            return list(selected_files)
        elif key == ' ':  # Space
            if view_mode == 'files':
                current_dir_name = dirs[current_dir]
                file_info = file_tree[current_dir_name][current_file]
                if file_info['path'] in selected_files:
                    selected_files.remove(file_info['path'])
                else:
                    selected_files.add(file_info['path'])
        elif key.lower() == 'a':  # Select all in current directory
            if view_mode == 'files':
                current_dir_name = dirs[current_dir]
                for file_info in file_tree[current_dir_name]:
                    selected_files.add(file_info['path'])
        elif key.lower() == 'n':  # Deselect all in current directory
            if view_mode == 'files':
                current_dir_name = dirs[current_dir]
                for file_info in file_tree[current_dir_name]:
                    selected_files.discard(file_info['path'])
        elif key.lower() == 'q' or key == '\x1b':  # Q or ESC
            return None


def select_prompts():
    """Select prompt templates interactively."""
    prompts = list(PROMPT_TEMPLATES.keys())
    prompt_names = [f"{PROMPT_TEMPLATES[k]['name']}" for k in prompts]
    
    print(f"\n{Fore.CYAN}Select Prompt Templates (you can select multiple):{Style.RESET_ALL}\n")
    for idx, name in enumerate(prompt_names):
        print(f"  {idx + 1}. {name}")
    print(f"  0. No prompt template")
    
    selected_indices = input(f"\n{Fore.YELLOW}Enter numbers separated by commas (e.g., 1,3): {Style.RESET_ALL}").strip()
    
    if not selected_indices or selected_indices == "0":
        return []
    
    try:
        indices = [int(x.strip()) - 1 for x in selected_indices.split(',') if x.strip()]
        selected = []
        for idx in indices:
            if 0 <= idx < len(prompts):
                selected.append(prompts[idx])
        return selected
    except:
        return []

def interactive_mode():
    """Enhanced interactive mode with menu selection."""
    
    # Step 1: Choose mode
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Welcome to Enhanced Project Structure Reader{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    
    modes = [
        "Standard Mode (with prompts and filters)",
        "Interactive File Browser (select specific files)"
    ]
    
    mode_choice = select_from_list(modes, "Select Mode:")
    if mode_choice is None:
        return None
    
    use_file_browser = (mode_choice == modes[1])
    
    # Step 2: Project type selection
    project_types = list(PROJECT_DEFAULTS.keys())
    suggested_type, confidence = detect_project_type_advanced(os.getcwd())
    
    type_options = []
    for pt in project_types:
        color = PROJECT_COLORS.get(pt, Fore.WHITE)
        if pt == suggested_type:
            type_options.append(f"{color}{pt} (Detected: {confidence:.0f}% confidence){Style.RESET_ALL}")
        else:
            type_options.append(f"{color}{pt}{Style.RESET_ALL}")
    
    project_type_display = select_from_list(type_options, "Select Project Type:")
    if project_type_display is None:
        return None
    
    project_type = project_types[type_options.index(project_type_display)]
    config = load_config(project_type)
    
    # Step 3: Folder path
    print(f"\n{Fore.CYAN}Enter folder path or GitHub URL{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Default: {os.getcwd()}{Style.RESET_ALL}")
    folder_input = input(f"{Fore.GREEN}> {Style.RESET_ALL}").strip()
    
    if not folder_input:
        folder_path = os.getcwd()
    elif folder_input.startswith("http"):
        try:
            folder_path = clone_remote_repo(folder_input)
        except Exception as e:
            print(f"{Fore.RED}Error cloning repository: {e}{Style.RESET_ALL}")
            return None
    else:
        try:
            folder_path = validate_path(folder_input)
        except ValueError as e:
            print(f"{Fore.RED}{e}{Style.RESET_ALL}")
            return None
    
    # Step 4: File browser mode or standard mode
    selected_files = None
    if use_file_browser:
        selected_files = interactive_file_browser(folder_path, config['exclude_folders'], config['exclude_extensions'])
        if selected_files is None:
            print(f"{Fore.RED}File selection cancelled.{Style.RESET_ALL}")
            return None
        print(f"\n{Fore.GREEN}Selected {len(selected_files)} files.{Style.RESET_ALL}")
        
        filter_folder = None
        keyword = None
        regex = None
        min_size = 0
        modified_after = None
    else:
        # Standard mode - additional filters
        filters = [
            "Filter by folder name",
            "Filter by keyword",
            "Filter by regex",
            "Filter by minimum size",
            "Filter by modification date",
            "No additional filters"
        ]
        
        filter_choice = select_from_list(filters, "Select Filter Options:", multi_select=True)
        
        filter_folder = None
        keyword = None
        regex = None
        min_size = 0
        modified_after = None
        
        if filter_choice and "Filter by folder name" in filter_choice:
            filter_folder = input(f"\n{Fore.YELLOW}Enter folder name to filter: {Style.RESET_ALL}").strip() or None
        
        if filter_choice and "Filter by keyword" in filter_choice:
            keyword = input(f"\n{Fore.YELLOW}Enter keyword to filter: {Style.RESET_ALL}").strip() or None
        
        if filter_choice and "Filter by regex" in filter_choice:
            regex = input(f"\n{Fore.YELLOW}Enter regex pattern: {Style.RESET_ALL}").strip() or None
        
        if filter_choice and "Filter by minimum size" in filter_choice:
            size_input = input(f"\n{Fore.YELLOW}Enter minimum file size in bytes: {Style.RESET_ALL}").strip()
            min_size = int(size_input) if size_input.isdigit() else 0
        
        if filter_choice and "Filter by modification date" in filter_choice:
            date_input = input(f"\n{Fore.YELLOW}Enter date (YYYY-MM-DD): {Style.RESET_ALL}").strip()
            try:
                modified_after = datetime.datetime.strptime(date_input, "%Y-%m-%d")
            except:
                modified_after = None
    
    # Step 5: Prompt template selection
    selected_prompt_keys = select_prompts()
    
    # Build combined prompt
    combined_prompt = ""
    if selected_prompt_keys:
        for key in selected_prompt_keys:
            combined_prompt += PROMPT_TEMPLATES[key]['template'] + "\n\n"
    
    # Step 6: Output format
    formats = ["txt", "json", "md", "html"]
    format_options = [f.upper() for f in formats]
    format_choice = select_from_list(format_options, "Select Output Format:")
    if format_choice is None:
        return None
    output_format = formats[format_options.index(format_choice)]
    
    # Step 7: Minify option
    minify_options = ["Yes - Minify content (reduce size)", "No - Keep original content"]
    minify_choice = select_from_list(minify_options, "Enable Minification?")
    minify = (minify_choice == minify_options[0])
    
    # Step 8: Copy to clipboard
    clipboard_options = ["Yes - Copy to clipboard", "No"]
    clipboard_choice = select_from_list(clipboard_options, "Copy to Clipboard?")
    copy_to_clipboard = (clipboard_choice == clipboard_options[0])
    
    return {
        'folder_path': folder_path,
        'project_type': project_type,
        'filter_folder': filter_folder,
        'exclude_folders': config['exclude_folders'],
        'exclude_extensions': config['exclude_extensions'],
        'keyword': keyword,
        'regex': regex,
        'output_format': output_format,
        'min_size': min_size,
        'modified_after': modified_after,
        'minify': minify,
        'copy_to_clipboard': copy_to_clipboard,
        'prompt_template': combined_prompt if combined_prompt else None,
        'selected_files': selected_files
    }

def main():
    init()  # Initialize colorama
    parser = argparse.ArgumentParser(
        description=_("Enhanced project structure and file reader with interactive browser"),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-C", "--custom", nargs=3,
        metavar=("FOLDER", "EXCLUDE_FOLDERS", "EXCLUDE_EXTENSIONS"),
        help=_("Custom mode. Format: folder_path 'folder1,folder2' '.log,.md'")
    )
    parser.add_argument(
        "-F", "--filter",
        help=_("Only include folders containing this name"),
        default=None
    )
    parser.add_argument(
        "-K", "--keyword",
        help=_("Filter files containing this keyword"),
        default=None
    )
    parser.add_argument(
        "-R", "--regex",
        help=_("Filter files matching this regex pattern"),
        default=None
    )
    parser.add_argument(
        "--format",
        choices=["txt", "json", "md", "html"],
        default=None,
        help=_("Output format")
    )
    parser.add_argument(
        "-P", "--project-type",
        choices=list(PROJECT_DEFAULTS.keys()),
        default=None,
        help=_("Project type")
    )
    parser.add_argument(
        "--remote",
        help=_("GitHub repository URL to clone"),
        default=None
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help=_("Copy output to clipboard")
    )
    parser.add_argument(
        "--log-file",
        default="output/log.txt",
        help=_("Path to log file")
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=0,
        help=_("Minimum file size in bytes")
    )
    parser.add_argument(
        "--modified-after",
        help=_("Only include files modified after this date (YYYY-MM-DD)"),
        default=None
    )
    parser.add_argument(
        "--minify",
        action="store_true",
        help=_("Minify file contents to reduce size")
    )
    parser.add_argument(
        "--prompt",
        choices=list(PROMPT_TEMPLATES.keys()),
        nargs='+',
        help=_("Add prompt template(s) to output")
    )

    args = parser.parse_args()

    setup_logging(args.log_file)

    try:
        # CLI mode
        if args.custom or args.remote:
            folder_path = None
            if args.remote:
                folder_path = clone_remote_repo(args.remote)
            elif args.custom:
                folder_path = validate_path(args.custom[0])
            
            project_type = args.project_type if args.project_type else detect_project_type_advanced(folder_path)[0]
            config = load_config(project_type)
            
            if args.custom:
                exclude_folders = [f.strip() for f in args.custom[1].split(',')]
                exclude_extensions = [e.strip().lower() for e in args.custom[2].split(',')]
            else:
                exclude_folders = config['exclude_folders']
                exclude_extensions = config['exclude_extensions']
            
            filter_folder = args.filter
            keyword = args.keyword
            regex = args.regex
            output_format = args.format if args.format else config['output_format']
            min_size = args.min_size
            modified_after = datetime.datetime.strptime(args.modified_after, "%Y-%m-%d") if args.modified_after else None
            minify = args.minify
            
            # Build prompt template
            prompt_template = ""
            if args.prompt:
                for prompt_key in args.prompt:
                    if prompt_key in PROMPT_TEMPLATES:
                        prompt_template += PROMPT_TEMPLATES[prompt_key]['template'] + "\n\n"
            
            structure = get_structure(
                folder_path,
                filter_folder=filter_folder,
                exclude_folders=exclude_folders,
                exclude_extensions=exclude_extensions
            )

            contents = get_file_contents(
                folder_path,
                filter_folder=filter_folder,
                exclude_folders=exclude_folders,
                exclude_extensions=exclude_extensions,
                keyword=keyword,
                regex=regex,
                min_size=min_size,
                modified_after=modified_after,
                minify=minify
            )

            output = format_output(structure, contents, output_format, prompt_template)
            saved_path = save_and_open(output, folder_path, output_format, copy_to_clipboard=args.copy)
            print(f"\n{Fore.GREEN}✅ {_('Output saved to')}: {Fore.BLUE}{saved_path}{Style.RESET_ALL}")

            if args.remote:
                shutil.rmtree(folder_path)
        
        # Interactive mode
        else:
            result = interactive_mode()
            if result is None:
                print(f"\n{Fore.YELLOW}Operation cancelled.{Style.RESET_ALL}")
                return
            
            print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Processing project...{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
            
            structure = get_structure(
                result['folder_path'],
                filter_folder=result['filter_folder'],
                exclude_folders=result['exclude_folders'],
                exclude_extensions=result['exclude_extensions']
            )

            contents = get_file_contents(
                result['folder_path'],
                filter_folder=result['filter_folder'],
                exclude_folders=result['exclude_folders'],
                exclude_extensions=result['exclude_extensions'],
                keyword=result['keyword'],
                regex=result['regex'],
                min_size=result['min_size'],
                modified_after=result['modified_after'],
                minify=result['minify'],
                selected_files=result.get('selected_files')
            )

            output = format_output(structure, contents, result['output_format'], result['prompt_template'])
            
            saved_path = save_and_open(
                output,
                result['folder_path'],
                result['output_format'],
                copy_to_clipboard=result['copy_to_clipboard']
            )
            
            print(f"\n{Fore.GREEN}✅ {_('Output saved to')}: {Fore.BLUE}{saved_path}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Total size: {format_size(len(output.encode('utf-8')))}{Style.RESET_ALL}")
            
    except ValueError as e:
        print(f"\n{Fore.RED}❌ {_('Error')}: {e}{Style.RESET_ALL}")
        exit(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠ Operation cancelled by user.{Style.RESET_ALL}")
        exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}❌ {_('Unexpected error')}: {e}{Style.RESET_ALL}")
        logging.exception("Unexpected error occurred")
        exit(1)

if __name__ == "__main__":
    main()