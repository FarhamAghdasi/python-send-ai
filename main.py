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

def get_structure(folder_path, indent=0, filter_folder=None, exclude_folders=None, exclude_extensions=None):
    if exclude_folders is None:
        exclude_folders = ['.git']
    if exclude_extensions is None:
        exclude_extensions = ['.svg']

    structure = ""
    try:
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
    total_files = sum(len(files) for root, _, files in os.walk(folder_path)
                      if not (filter_folder and filter_folder not in root)
                      and not any(part in exclude_folders for part in os.path.normpath(root).split(os.sep)))

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
    config = load_config("generic")  # Load generic config to show available project types
    available_projects = list(PROJECT_DEFAULTS.keys())
    print(f"Available project types: {', '.join(available_projects)}")
    project_type = input(f"Enter project type (default: generic): ").strip().lower() or "generic"
    if project_type not in available_projects:
        print(f"{Fore.YELLOW}⚠ Warning: Unknown project type '{project_type}', using 'generic'{Style.RESET_ALL}")
        project_type = "generic"

    config = load_config(project_type)
    folder_path = input(f"Enter the folder path (default: {os.getcwd()}): ").strip() or os.getcwd()
    filter_folder = input(f"Enter folder name to filter (default: {config['filter_folder']}): ").strip() or config['filter_folder']
    exclude_folders = input(f"Enter folders to exclude (comma-separated, default: {','.join(config['exclude_folders'])}): ").strip()
    exclude_folders = [f.strip() for f in exclude_folders.split(',')] if exclude_folders else config['exclude_folders']
    exclude_extensions = input(f"Enter file extensions to exclude (comma-separated, default: {','.join(config['exclude_extensions'])}): ").strip()
    exclude_extensions = [e.strip().lower() for e in exclude_extensions.split(',')] if exclude_extensions else config['exclude_extensions']
    keyword = input(f"Enter keyword to filter file contents (default: {config['keyword']}): ").strip() or config['keyword']
    regex = input(f"Enter regex pattern to filter file contents (default: {config['regex']}): ").strip() or config['regex']
    output_format = input(f"Enter output format (txt, json, md, default: {config['output_format']}): ").strip().lower() or config['output_format']
    if output_format not in ["txt", "json", "md"]:
        output_format = config['output_format']
    return folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, project_type

def main():
    init()  # Initialize colorama
    parser = argparse.ArgumentParser(
        description="Project structure and file reader",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-C", "--custom", nargs=3, 
        metavar=("FOLDER", "EXCLUDE Curso de diseño gráfico y edición de video online para principiantes", "EXCLUDE_EXTENSIONS"),
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
        help=f"Project type: {', '.join(PROJECT_DEFAULTS.keys())}\nExample: --project-type nodejs"
    )

    args = parser.parse_args()

    if args.custom:
        project_type = args.project_type if args.project_type else "generic"
        config = load_config(project_type)
        folder_path = args.custom[0]
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

    try:
        saved_path = save_and_open(output, folder_path, output_format)
        print(f"\n{Fore.GREEN}✅ Output saved to: {saved_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error saving file: {e}{Style.RESET_ALL}")
        print("Here's the output:\n")
        print(output)

if __name__ == "__main__":
    main()