import os
import argparse
import logging
import datetime
from colorama import init, Fore, Style
import shutil
from utils.file_utils import get_structure, get_file_contents, validate_path
from utils.config_utils import load_config, save_profile, detect_project_type, PROJECT_DEFAULTS, PROJECT_COLORS
from utils.prompt_utils import save_prompt, PROMPT_TEMPLATES
from utils.ui_utils import interactive_mode, gui_mode, semi_interactive_mode, format_output, save_and_open, clone_remote_repo, select_prompt
import gettext

# Initialize i18n
lang = os.getenv("LANG", "en")
if lang == "fa":
    translation = gettext.translation("messages", localedir="locale", languages=["fa"])
    translation.install()
    _ = translation.gettext
else:
    _ = lambda x: x

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
        help=_(f"Project type: {', '.join(PROJECT_DEFAULTS.keys())}\nExample: --project-type laravel\nIf not provided, auto-detected based on folder contents.")
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
        "--semi",
        action="store_true",
        help=_( "Run in semi-interactive CLI mode with folder/file selection")
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
        # Prompt selection
        prompt_type = None
        if not args.gui and not args.semi and not args.custom and not args.remote:
            print(f"\n{Fore.CYAN}{_( 'Starting interactive mode')}{Style.RESET_ALL}")
            use_prompt = input(_( "Would you like to add a prompt? (y/n): ")).strip().lower()
            if use_prompt == "y":
                prompt_type = select_prompt()

        # Determine folder path
        folder_path = None
        selected_files = []
        if args.remote:
            folder_path = clone_remote_repo(args.remote)
        elif args.semi:
            folder_path = input(_(f"Enter the folder path or GitHub URL (default: {Fore.BLUE}{os.getcwd()}{Style.RESET_ALL}): ")).strip() or os.getcwd()
            if folder_path.startswith("http"):
                folder_path = clone_remote_repo(folder_path)
            else:
                folder_path = validate_path(folder_path)
            selected_files = semi_interactive_mode(folder_path)
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
        elif args.gui:
            gui_mode()
            return
        else:
            folder_path, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, project_type, min_size, modified_after = interactive_mode()
            config = load_config(project_type)

        # Default config for non-custom modes
        if not args.custom:
            project_type = args.project_type if args.project_type else detect_project_type(folder_path)
            config = load_config(project_type)
            exclude_folders = config['exclude_folders']
            exclude_extensions = config['exclude_extensions']
            filter_folder = args.filter if args.filter is not None else config['filter_folder']
            keyword = args.keyword if args.keyword is not None else config['keyword']
            regex = args.regex if args.regex is not None else config['regex']
            output_format = args.format if args.format is not None else config['output_format']
            min_size = args.min_size if args.min_size is not None else config['min_size']
            modified_after = datetime.datetime.strptime(args.modified_after, "%Y-%m-%d") if args.modified_after else config['modified_after']

        # Process structure and contents
        structure = "\n".join([item for item, _ in get_structure(folder_path, filter_folder=filter_folder, exclude_folders=exclude_folders, exclude_extensions=exclude_extensions)])
        contents = get_file_contents(folder_path, selected_files if args.semi else [], filter_folder, exclude_folders, exclude_extensions, keyword, regex, min_size, modified_after)

        # Apply prompt if selected
        if prompt_type:
            contents = save_prompt(prompt_type, contents)

        # Format and save output
        output = format_output(structure, contents, output_format)
        saved_path = save_and_open(output, folder_path, output_format, copy_to_clipboard=args.copy)

        # Save profile
        save_profile_choice = input(_( "Would you like to save these settings as a profile? (y/n): ")).strip().lower()
        if save_profile_choice == "y":
            profile_name = input(_( "Enter profile name: ")).strip()
            save_profile(profile_name, project_type, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, min_size, modified_after)

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