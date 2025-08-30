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

# Initialize i18n
lang = os.getenv("LANG", "en")
if lang == "fa":
    translation = gettext.translation("messages", localedir="locale", languages=["fa"])
    translation.install()
    _ = translation.gettext
else:
    _ = lambda x: x

# Default settings for different project types
PROJECT_DEFAULTS = {
    "python": {
        "exclude_folders": [".git", ".venv", "__pycache__"],
        "exclude_extensions": [".svg", ".pyc", ".jpg", ".png", ".bin"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "nodejs": {
        "exclude_folders": [".git", "node_modules", "dist", "build"],
        "exclude_extensions": [".svg", ".log", ".jpg", ".png", ".bin"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "java": {
        "exclude_folders": [".git", "target", ".idea"],
        "exclude_extensions": [".svg", ".class", ".jpg", ".png", ".bin"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "go": {
        "exclude_folders": [".git", "vendor"],
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
    "generic": Fore.CYAN
}

def setup_logging(log_file):
    """Setup logging configuration."""
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

def detect_project_type(folder_path):
    """Detect project type based on directory contents."""
    try:
        folder_path = validate_path(folder_path)
        items = os.listdir(folder_path)
        if any(f in items for f in ["package.json", "npm-shrinkwrap.json"]):
            return "nodejs"
        if any(f in items for f in ["pyproject.toml", "requirements.txt", "setup.py"]):
            return "python"
        if any(f in items for f in ["pom.xml", "build.gradle"]):
            return "java"
        if "go.mod" in items:
            return "go"
    except Exception as e:
        logging.error(_(f"Error detecting project type: {e}"))
    return "generic"

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

            structure += '    ' * (indent // 4)
            structure += '└── ' if is_last else '├── '
            structure += f'[DIR] {item}\n'

            structure += get_structure(item_path, indent + 4, filter_folder, exclude_folders, exclude_extensions)
        else:
            file_ext = os.path.splitext(item)[1].lower()
            if file_ext in exclude_extensions:
                continue

            structure += '    ' * (indent // 4)
            structure += ('└── ' if is_last else '├── ') + f'[FILE] {item}\n'

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

def get_file_contents(folder_path, filter_folder=None, exclude_folders=None, exclude_extensions=None, keyword=None, regex=None, min_size=0, modified_after=None):
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
            executor.map(lambda f: read_file(f, keyword, regex), file_list),
            total=len(file_list),
            desc=_( "Processing files"),
            unit="file"
        ))
    
    return "".join([r for r in results if r])

def format_output(structure, contents, output_format="txt"):
    if output_format == "json":
        output_dict = {"folder_structure": structure, "file_contents": contents}
        return json.dumps(output_dict, indent=2, ensure_ascii=False)
    elif output_format == "md":
        return f"# {_( 'Project Structure')}\n\n```tree\n{structure}\n```\n\n# {_( 'File Contents')}\n\n```text\n{contents}\n```"
    elif output_format == "html":
        md_content = f"# {_( 'Project Structure')}\n\n```tree\n{structure}\n```\n\n# {_( 'File Contents')}\n\n```text\n{contents}\n```"
        return markdown2.markdown(md_content)
    else:  # txt
        return f"{_( 'Folder Structure')}:\n{structure}\n\n{_( 'File Contents')}:{contents}"

def save_and_open(output, folder_path, output_format="txt", split_if_large=True, copy_to_clipboard=False):
    try:
        output_dir = os.path.join(folder_path, 'output')
        os.makedirs(output_dir, exist_ok=True)

        extension = {"txt": "txt", "json": "json", "md": "md", "html": "html"}[output_format]
        max_size = 12000

        if copy_to_clipboard:
            pyperclip.copy(output)
            logging.info(_( "Output copied to clipboard"))

        if split_if_large and len(output) > max_size:
            user_choice = input(f"{Fore.YELLOW}⚠ {_( 'Output exceeds {max_size:,} characters. Split into multiple files? (y/n):')} {Style.RESET_ALL}").strip().lower()
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

        filename = f"project_structure_{len(os.listdir(output_dir)) + 1}.{extension}"
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
    config_path = os.path.join(os.getcwd(), "config.json")
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

def interactive_mode():
    input_stack = []
    prompts = [
        (
            lambda: _(f"Available project types: {', '.join(PROJECT_COLORS.get(p, Fore.CYAN) + p + Style.RESET_ALL for p in PROJECT_DEFAULTS.keys())}"),
            lambda suggested: _(f"Enter project type (default: {Fore.CYAN}{suggested}{Style.RESET_ALL}): "),
            lambda x: x.strip().lower() or None
        ),
        (
            lambda: _(f"Enter the folder path or GitHub URL (default: {Fore.BLUE}{os.getcwd()}{Style.RESET_ALL}): "),
            None,
            lambda x: x.strip() or os.getcwd()
        ),
        (
            lambda: _(f"Enter folder name to filter (default: {{}}): "),
            None,
            lambda x: x.strip() or None
        ),
        (
            lambda: _(f"Enter folders to exclude (comma-separated, default: {{}}): "),
            None,
            lambda x: [f.strip() for f in x.split(',')] if x.strip() else None
        ),
        (
            lambda: _(f"Enter file extensions to exclude (comma-separated, default: {{}}): "),
            None,
            lambda x: [e.strip().lower() for e in x.split(',')] if x.strip() else None
        ),
        (
            lambda: _(f"Enter keyword to filter file contents (default: {{}}): "),
            None,
            lambda x: x.strip() or None
        ),
        (
            lambda: _(f"Enter regex pattern to filter file contents (default: {{}}): "),
            None,
            lambda x: x.strip() or None
        ),
        (
            lambda: _(f"Enter output format ({Fore.CYAN}txt, json, md, html{Style.RESET_ALL}, default: {{}}): "),
            None,
            lambda x: x.strip().lower() or None
        ),
        (
            lambda: _(f"Enter minimum file size in bytes (default: {{}}): "),
            None,
            lambda x: int(x.strip()) if x.strip().isdigit() else None
        ),
        (
            lambda: _(f"Enter modified after date (YYYY-MM-DD, default: {{}}): "),
            None,
            lambda x: datetime.datetime.strptime(x.strip(), "%Y-%m-%d") if x.strip() else None
        )
    ]

    results = [None] * len(prompts)
    i = 0
    suggested_type = "generic"
    config = load_config(suggested_type)

    while i < len(prompts):
        if i == 0:
            prompt_text = prompts[i][0]()
            prompt_text += f"\n{_( 'Suggested project type')}: {Fore.CYAN}{suggested_type}{Style.RESET_ALL}\n"
            prompt_text += prompts[i][1](suggested_type)
        elif i == 1:
            prompt_text = prompts[i][0]()
            if prompts[i][1]:
                prompt_text += prompts[i][1](suggested_type)
        else:
            config = load_config(results[0] or suggested_type) if i > 0 else config
            default_value = {
                0: suggested_type,
                1: os.getcwd(),
                2: config['filter_folder'],
                3: ','.join(config['exclude_folders']),
                4: ','.join(config['exclude_extensions']),
                5: config['keyword'],
                6: config['regex'],
                7: config['output_format'],
                8: config['min_size'],
                9: config['modified_after']
            }[i]
            prompt_text = prompts[i][0]().format(default_value if default_value else _( "None"))
            if prompts[i][1]:
                prompt_text += prompts[i][1](suggested_type)

        user_input = input(prompt_text).strip()

        if user_input.lower() == "back" and i > 0:
            i -= 1
            results[i] = None
            if i == 1:
                suggested_type = detect_project_type(os.getcwd())
            if i == 0:
                suggested_type = "generic"
            continue

        if user_input.lower().startswith("back"):
            try:
                parts = user_input.split()
                if len(parts) == 2 and parts[1].isdigit():
                    step = int(parts[1])
                    if 0 <= step < len(results):
                        i = step
                        continue
                elif i > 0:
                    i -= 1
                    continue
            except:
                pass
            print(f"{Fore.YELLOW}⚠ {_( 'Usage: \'back\' or \'back <step_number>\' to return to a specific step.')}{Style.RESET_ALL}")
            continue

        if i == 1:
            try:
                if user_input.startswith("http"):
                    folder_path = clone_remote_repo(user_input)
                    processed_input = folder_path
                else:
                    processed_input = validate_path(user_input or os.getcwd())
                suggested_type = detect_project_type(processed_input)
            except ValueError as e:
                print(f"{Fore.RED}❌ {_( 'Error')}: {e}{Style.RESET_ALL}")
                continue
        else:
            processed_input = prompts[i][2](user_input)

        if i == 0 and processed_input not in PROJECT_DEFAULTS:
            warning_msg = _("Warning: Unknown project type \"{processed_input}\", using \"{output_format}\"").format(
                processed_input=processed_input,
                output_format=config['output_format']
            )
            print(f"{Fore.YELLOW}⚠ {warning_msg}{Style.RESET_ALL}")
            processed_input = suggested_type
        elif i == 7 and processed_input not in ["txt", "json", "md", "html", None]:
            warning_msg = _("Warning: Unknown output format \"{processed_input}\", using \"{output_format}\"").format(
                processed_input=processed_input,
                output_format=config['output_format']
            )
            print(f"{Fore.YELLOW}⚠ {warning_msg}{Style.RESET_ALL}")
            processed_input = config['output_format']

        results[i] = processed_input
        input_stack.append(user_input)
        i += 1

    project_type, folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, min_size, modified_after = results
    exclude_folders = exclude_folders or config['exclude_folders']
    exclude_extensions = exclude_extensions or config['exclude_extensions']
    output_format = output_format or config['output_format']
    min_size = min_size or config['min_size']
    modified_after = modified_after or config['modified_after']

    return folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, project_type, min_size, modified_after

def gui_mode():
    """Run GUI for input collection."""
    root = tk.Tk()
    root.title(_( "Project Structure Reader"))

    fields = [
        _( "Project Type"), _( "Folder Path or GitHub URL"), _( "Filter Folder"), _( "Exclude Folders (comma-separated)"),
        _( "Exclude Extensions (comma-separated)"), _( "Keyword"), _( "Regex"), _( "Output Format"),
        _( "Min File Size (bytes)"), _( "Modified After (YYYY-MM-DD)")
    ]
    entries = {}

    for i, field in enumerate(fields):
        tk.Label(root, text=field).grid(row=i, column=0, padx=5, pady=5)
        entry = ttk.Entry(root, width=50)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entries[field] = entry

    def submit():
        results = [entries[field].get() for field in fields]
        try:
            project_type = results[0] or "generic"
            folder_path = results[1] or os.getcwd()
            if folder_path.startswith("http"):
                folder_path = clone_remote_repo(folder_path)
            else:
                folder_path = validate_path(folder_path)
            filter_folder = results[2] or None
            exclude_folders = [f.strip() for f in results[3].split(',')] if results[3] else None
            exclude_extensions = [e.strip().lower() for e in results[4].split(',')] if results[4] else None
            keyword = results[5] or None
            regex = results[6] or None
            output_format = results[7] or "txt"
            min_size = int(results[8]) if results[8].isdigit() else 0
            modified_after = datetime.datetime.strptime(results[9], "%Y-%m-%d") if results[9] else None

            config = load_config(project_type)
            exclude_folders = exclude_folders or config['exclude_folders']
            exclude_extensions = exclude_extensions or config['exclude_extensions']
            output_format = output_format if output_format in ["txt", "json", "md", "html"] else config['output_format']
            
            structure = get_structure(folder_path, filter_folder=filter_folder, exclude_folders=exclude_folders, exclude_extensions=exclude_extensions)
            contents = get_file_contents(folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, min_size, modified_after)
            output = format_output(structure, contents, output_format)
            saved_path = save_and_open(output, folder_path, output_format, copy_to_clipboard=entries[_("Copy to Clipboard")].get() == "1")
            messagebox.showinfo(_( "Success"), _(f"Output saved to: {saved_path}"))
        except Exception as e:
            messagebox.showerror(_( "Error"), _(f"Error: {e}"))
        root.destroy()

    tk.Checkbutton(root, text=_( "Copy to Clipboard"), variable=tk.BooleanVar()).grid(row=len(fields), column=0, columnspan=2)
    tk.Button(root, text=_( "Generate"), command=submit).grid(row=len(fields)+1, column=0, columnspan=2, pady=10)

    root.mainloop()

def main():
    init()  # Initialize colorama
    parser = argparse.ArgumentParser(
        description=_( "Project structure and file reader"),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-C", "--custom", nargs=3,
        metavar=("FOLDER", "EXCLUDE_FOLDERS", "EXCLUDE_EXTENSIONS"),
        help=_( "Custom mode. Format: folder_path 'folder1,folder2' '.log,.md'\nExample: -C /path/to/project '.git,.venv' '.svg,.png'")
    )
    parser.add_argument(
        "-F", "--filter",
        help=_( "Only include folders containing this name\nExample: --filter src"),
        default=None
    )
    parser.add_argument(
        "-K", "--keyword",
        help=_( "Filter files containing this keyword\nExample: --keyword import"),
        default=None
    )
    parser.add_argument(
        "-R", "--regex",
        help=_( "Filter files matching this regex pattern\nExample: --regex '^def\\s+\\w+'"),
        default=None
    )
    parser.add_argument(
        "--format",
        choices=["txt", "json", "md", "html"],
        default=None,
        help=_( "Output format: txt (plain text), json (JSON), md (Markdown), html (HTML)\nExample: --format md")
    )
    parser.add_argument(
        "-P", "--project-type",
        choices=list(PROJECT_DEFAULTS.keys()),
        default=None,
        help=_(f"Project type: {', '.join(PROJECT_DEFAULTS.keys())}\nExample: --project-type nodejs\nIf not provided, auto-detected based on folder contents.")
    )
    parser.add_argument(
        "--remote",
        help=_( "GitHub repository URL to clone\nExample: --remote https://github.com/user/repo"),
        default=None
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help=_( "Run in GUI mode")
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help=_( "Copy output to clipboard")
    )
    parser.add_argument(
        "--log-file",
        default="output/log.txt",
        help=_( "Path to log file")
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=0,
        help=_( "Minimum file size in bytes\nExample: --min-size 1000")
    )
    parser.add_argument(
        "--modified-after",
        help=_( "Only include files modified after this date (YYYY-MM-DD)\nExample: --modified-after 2023-01-01"),
        default=None
    )
    parser.add_argument(
        "--lang",
        choices=["en", "fa"],
        default="en",
        help=_( "Language for interface (en, fa)\nExample: --lang fa")
    )

    args = parser.parse_args()

    setup_logging(args.log_file)

    try:
        if args.gui:
            gui_mode()
            return

        folder_path = None
        if args.remote:
            folder_path = clone_remote_repo(args.remote)
        elif args.custom:
            folder_path = validate_path(args.custom[0])
            project_type = args.project_type if args.project_type else detect_project_type(folder_path)
            config = load_config(project_type)
            exclude_folders = [f.strip() for f in args.custom[1].split(',')]
            exclude_extensions = [e.strip().lower() for e in args.custom[2].split(',')]
            filter_folder = args.filter
            keyword = args.keyword
            regex = args.regex
            output_format = args.format if args.format is not None else config['output_format']
            min_size = args.min_size
            modified_after = datetime.datetime.strptime(args.modified_after, "%Y-%m-%d") if args.modified_after else None
        else:
            folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, project_type, min_size, modified_after = interactive_mode()
            config = load_config(project_type)

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
            modified_after=modified_after
        )

        output = format_output(structure, contents, output_format)

        saved_path = save_and_open(output, folder_path, output_format, copy_to_clipboard=args.copy)
        print(f"\n{Fore.GREEN}✅ {_( 'Output saved to')}: {Fore.BLUE}{saved_path}{Style.RESET_ALL}")

        if args.remote:
            shutil.rmtree(folder_path)  # Cleanup temp repo
    except ValueError as e:
        print(f"\n{Fore.RED}❌ {_( 'Error')}: {e}{Style.RESET_ALL}")
        exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}❌ {_( 'Unexpected error')}: {e}{Style.RESET_ALL}")
        print(_( "Here's the partial output:\n"))
        print(output if 'output' in locals() else _( "No output generated."))
        exit(1)

if __name__ == "__main__":
    main()