import os
import platform
import argparse
import json
import re
from colorama import init, Fore, Style
from tqdm import tqdm
import markdown2

# Default settings for different project types
PROJECT_DEFAULTS = {
    "python": {
        "exclude_folders": [".git", ".venv", "__pycache__"],
        "exclude_extensions": [".svg", ".pyc"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt"
    },
    "nodejs": {
        "exclude_folders": [".git", "node_modules", "dist", "build"],
        "exclude_extensions": [".svg", ".log"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt"
    },
    "java": {
        "exclude_folders": [".git", "target", ".idea"],
        "exclude_extensions": [".svg", ".class"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt"
    },
    "generic": {
        "exclude_folders": [".git"],
        "exclude_extensions": [".svg"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt"
    }
}

PROJECT_COLORS = {
    "python": Fore.MAGENTA,
    "nodejs": Fore.YELLOW,
    "java": Fore.GREEN,
    "generic": Fore.CYAN
}


def validate_path(folder_path):
    """Validate that the folder path exists and is a directory."""
    if not os.path.exists(folder_path):
        raise ValueError(f"Path does not exist: {folder_path}")
    if not os.path.isdir(folder_path):
        raise ValueError(f"Path is not a directory: {folder_path}")
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
    except Exception:
        pass
    return "generic"

def get_structure(folder_path, indent=0, filter_folder=None, exclude_folders=None, exclude_extensions=None):
    if exclude_folders is None:
        exclude_folders = ['.git']
    if exclude_extensions is None:
        exclude_extensions = ['.svg']

    structure = ""
    try:
        folder_path = validate_path(folder_path)
        items = os.listdir(folder_path)
    except Exception as e:
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

def get_file_contents(folder_path, filter_folder=None, exclude_folders=None, exclude_extensions=None, keyword=None, regex=None):
    if exclude_folders is None:
        exclude_folders = ['.git']
    if exclude_extensions is None:
        exclude_extensions = ['.svg']

    contents = ""
    try:
        folder_path = validate_path(folder_path)
        total_files = sum(len(files) for root, _, files in os.walk(folder_path)
                          if not (filter_folder and filter_folder not in root)
                          and not any(part in exclude_folders for part in os.path.normpath(root).split(os.sep)))
    except Exception as e:
        return f"[ERROR] Could not process directory {folder_path}: {e}\n"

    with tqdm(total=total_files, desc="Processing files", unit="file") as pbar:
        for root, dirs, files in os.walk(folder_path):
            path_parts = os.path.normpath(root).split(os.sep)
            if any(part in exclude_folders for part in path_parts):
                continue

            if filter_folder and filter_folder not in root:
                continue

            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in exclude_extensions:
                    pbar.update(1)
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if keyword and keyword.lower() not in content.lower():
                            pbar.update(1)
                            continue
                        if regex and not re.search(regex, content, re.IGNORECASE):
                            pbar.update(1)
                            continue
                        contents += f"\n{'-' * 40}\nFile: {file_path}\n{'-' * 40}\n{content}\n"
                except Exception as e:
                    contents += f"\n[ERROR] Could not read {file_path}: {e}\n"
                pbar.update(1)

    return contents

def format_output(structure, contents, output_format="txt"):
    if output_format == "json":
        output_dict = {"folder_structure": structure, "file_contents": contents}
        return json.dumps(output_dict, indent=2, ensure_ascii=False)
    elif output_format == "md":
        return f"# Project Structure\n\n```tree\n{structure}\n```\n\n# File Contents\n\n```text\n{contents}\n```"
    else:  # txt
        return f"Folder Structure:\n{structure}\n\nFile Contents:{contents}"

def save_and_open(output, folder_path, output_format="txt"):
    try:
        output_dir = os.path.join(folder_path, 'output')
        os.makedirs(output_dir, exist_ok=True)

        extension = {"txt": "txt", "json": "json", "md": "md"}[output_format]
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
            print(f"{Fore.YELLOW}⚠ Warning: Could not open file {filepath}: {e}{Style.RESET_ALL}")

        return filepath
    except Exception as e:
        raise ValueError(f"Error saving output: {e}")

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
            print(f"{Fore.YELLOW}⚠ Warning: Could not load config.json: {e}{Style.RESET_ALL}")

    return config["projects"].get(project_type, PROJECT_DEFAULTS["generic"])

def interactive_mode():
    input_stack = []  # Stack to store inputs for back navigation
    prompts = [
        (
        lambda: "Available project types: " + ', '.join(
            PROJECT_COLORS.get(p, Fore.CYAN) + p + Style.RESET_ALL
            for p in PROJECT_DEFAULTS.keys()
        ),

            lambda suggested: f"Enter project type (default: {Fore.CYAN}{suggested}{Style.RESET_ALL}): ",
            lambda x: x.strip().lower() or None
        ),
        (
            lambda: f"Enter the folder path (default: {Fore.BLUE}{os.getcwd()}{Style.RESET_ALL}): ",
            None,
            lambda x: x.strip() or os.getcwd()
        ),
        (
            lambda: f"Enter folder name to filter (default: {{}}): ",
            None,
            lambda x: x.strip() or None
        ),
        (
            lambda: f"Enter folders to exclude (comma-separated, default: {{}}): ",
            None,
            lambda x: [f.strip() for f in x.split(',')] if x.strip() else None
        ),
        (
            lambda: f"Enter file extensions to exclude (comma-separated, default: {{}}): ",
            None,
            lambda x: [e.strip().lower() for e in x.split(',')] if x.strip() else None
        ),
        (
            lambda: f"Enter keyword to filter file contents (default: {{}}): ",
            None,
            lambda x: x.strip() or None
        ),
        (
            lambda: f"Enter regex pattern to filter file contents (default: {{}}): ",
            None,
            lambda x: x.strip() or None
        ),
        (
            lambda: f"Enter output format ({Fore.CYAN}txt{Style.RESET_ALL}, {Fore.CYAN}json{Style.RESET_ALL}, {Fore.CYAN}md{Style.RESET_ALL}, default: {{}}): ",
            None,
            lambda x: x.strip().lower() or None
        )
    ]

    results = [None] * len(prompts)
    i = 0
    suggested_type = "generic"
    config = load_config(suggested_type)

    while i < len(prompts):
        if i == 0:  # Project type prompt
            prompt_text = prompts[i][0]()
            prompt_text += f"\nSuggested project type: {Fore.CYAN}{suggested_type}{Style.RESET_ALL}\n"
            prompt_text += prompts[i][1](suggested_type)
        elif i == 1:  # Folder path prompt
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
                7: config['output_format']
            }[i]
            prompt_text = prompts[i][0]().format(default_value if default_value else "None")
            if prompts[i][1]:
                prompt_text += prompts[i][1](suggested_type)

        user_input = input(prompt_text).strip()

        if user_input.lower() == "back" and i > 0:
            i -= 1
            results[i] = None
            if i == 1:  # Recompute suggested project type when going back to folder path
                suggested_type = detect_project_type(os.getcwd())
            if i == 0:  # Reset suggested type when going back to project type
                suggested_type = "generic"
            continue

        if i == 1:  # Validate folder path
            try:
                processed_input = validate_path(user_input or os.getcwd())
                suggested_type = detect_project_type(processed_input)
            except ValueError as e:
                print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
                continue
        else:
            processed_input = prompts[i][2](user_input)

        if i == 0 and processed_input not in PROJECT_DEFAULTS:
            print(f"{Fore.YELLOW}⚠ Warning: Unknown project type '{processed_input}', using '{suggested_type}'{Style.RESET_ALL}")
            processed_input = suggested_type
        elif i == 7 and processed_input not in ["txt", "json", "md", None]:
            print(f"{Fore.YELLOW}⚠ Warning: Unknown output format '{processed_input}', using '{config['output_format']}'{Style.RESET_ALL}")
            processed_input = config['output_format']

        results[i] = processed_input
        input_stack.append(user_input)
        i += 1

    project_type, folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format = results
    exclude_folders = exclude_folders or config['exclude_folders']
    exclude_extensions = exclude_extensions or config['exclude_extensions']
    output_format = output_format or config['output_format']

    return folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, project_type

def main():
    init()  # Initialize colorama
    parser = argparse.ArgumentParser(
        description="Project structure and file reader",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-C", "--custom", nargs=3, 
        metavar=("FOLDER", "EXCLUDE_FOLDERS", "EXCLUDE_EXTENSIONS"),
        help="Custom mode. Format: folder_path 'folder1,folder2' '.log,.md'\nExample: -C /path/to/project '.git,.venv' '.svg,.png'"
    )
    parser.add_argument(
        "-F", "--filter", 
        help="Only include folders containing this name\nExample: --filter src",
        default=None
    )
    parser.add_argument(
        "-K", "--keyword", 
        help="Filter files containing this keyword\nExample: --keyword import",
        default=None
    )
    parser.add_argument(
        "-R", "--regex", 
        help="Filter files matching this regex pattern\nExample: --regex '^def\\s+\\w+'",
        default=None
    )
    parser.add_argument(
        "--format", 
        choices=["txt", "json", "md"], 
        default=None,
        help="Output format: txt (plain text), json (JSON), or md (Markdown)\nExample: --format md"
    )
    parser.add_argument(
        "-P", "--project-type",
        choices=list(PROJECT_DEFAULTS.keys()),
        default=None,
        help=f"Project type: {', '.join(PROJECT_DEFAULTS.keys())}\nExample: --project-type nodejs\nIf not provided, auto-detected based on folder contents."
    )

    args = parser.parse_args()

    try:
        if args.custom:
            folder_path = validate_path(args.custom[0])
            project_type = args.project_type if args.project_type else detect_project_type(folder_path)
            config = load_config(project_type)
            exclude_folders = [f.strip() for f in args.custom[1].split(',')]
            exclude_extensions = [e.strip().lower() for e in args.custom[2].split(',')]
            filter_folder = args.filter
            keyword = args.keyword
            regex = args.regex
            output_format = args.format if args.format is not None else config['output_format']
        else:
            folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, project_type = interactive_mode()
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
            regex=regex
        )

        output = format_output(structure, contents, output_format)

        saved_path = save_and_open(output, folder_path, output_format)
        print(f"\n{Fore.GREEN}✅ Output saved to: {Fore.BLUE}{saved_path}{Style.RESET_ALL}")
    except ValueError as e:
        print(f"\n{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
        exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
        print("Here's the partial output:\n")
        print(output if 'output' in locals() else "No output generated.")
        exit(1)

if __name__ == "__main__":
    main()