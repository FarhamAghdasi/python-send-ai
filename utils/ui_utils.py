import os
import platform
import argparse
import datetime
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from colorama import Fore, Style
import pyperclip
import markdown2
import shutil
import git
import json
from .file_utils import get_structure, get_file_contents, validate_path
from .config_utils import load_config, detect_project_type, PROJECT_DEFAULTS, PROJECT_COLORS
from .prompt_utils import save_prompt
import gettext

# Initialize i18n
lang = os.getenv("LANG", "en")
if lang == "fa":
    translation = gettext.translation("messages", localedir="locale", languages=["fa"])
    translation.install()
    _ = translation.gettext
else:
    _ = lambda x: x

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

def select_prompt():
    prompt_types = ["error_fixing", "explain_to_ai", "adding_new_feature", "auto_commiter"]
    session = PromptSession(_( "Select a prompt type (use arrow keys, Enter to select, 'q' to skip): "))
    bindings = KeyBindings()
    
    selected_index = [0]
    
    @bindings.add(Keys.Up)
    def _(event):
        selected_index[0] = (selected_index[0] - 1) % len(prompt_types)
    
    @bindings.add(Keys.Down)
    def _(event):
        selected_index[0] = (selected_index[0] + 1) % len(prompt_types)
    
    @bindings.add(Keys.Enter)
    def _(event):
        event.app.exit(result=prompt_types[selected_index[0]])
    
    @bindings.add('q')
    def _(event):
        event.app.exit(result=None)

    print(_( "Available prompts:"))
    for i, prompt in enumerate(prompt_types):
        print(f"{'→' if i == selected_index[0] else ' '} {prompt}")
    
    result = session.prompt(bindings=bindings)
    return result

def semi_interactive_mode(folder_path):
    session = PromptSession()
    bindings = KeyBindings()
    selected_files = []
    current_index = [0]
    structure = get_structure(folder_path)
    open_folders = set()

    @bindings.add(Keys.Up)
    def _(event):
        current_index[0] = (current_index[0] - 1) % len(structure)

    @bindings.add(Keys.Down)
    def _(event):
        current_index[0] = (current_index[0] + 1) % len(structure)

    @bindings.add(Keys.Enter)
    def _(event):
        item, is_dir = structure[current_index[0]]
        item_name = item.split()[-1]
        item_path = os.path.join(folder_path, item_name)
        if is_dir:
            if item_path in open_folders:
                open_folders.remove(item_path)
                # Remove subfolder contents when closing
                structure[:] = [(i, d) for i, d in structure if not i.startswith(f"    {item_name}/")]
            else:
                open_folders.add(item_path)
                # Add subfolder contents
                sub_structure = get_structure(item_path)
                structure[current_index[0]+1:current_index[0]+1] = [(f"    {sub_item}", sub_is_dir) for sub_item, sub_is_dir in sub_structure]
        else:
            if item_path in selected_files:
                selected_files.remove(item_path)
            else:
                selected_files.append(item_path)
    
    @bindings.add('q')
    def _(event):
        event.app.exit(result=selected_files)

    while True:
        print("\033[H\033[J", end="")  # Clear screen
        print(_( "Select files/folders (use arrow keys, Enter to toggle, 'q' to finish):"))
        for i, (item, is_dir) in enumerate(structure):
            item_name = item.split()[-1]
            item_path = os.path.join(folder_path, item_name)
            prefix = '→' if i == current_index[0] else ' '
            status = '[SELECTED]' if item_path in selected_files else '[OPEN]' if item_path in open_folders and is_dir else ''
            print(f"{prefix} {item} {status}")
        
        result = session.prompt(bindings=bindings)
        if result is not None:
            break
    
    return selected_files

def interactive_mode(suggested_type="generic"):
    input_stack = []
    prompts = [
        (
            lambda: _(f"Available project types: {', '.join(PROJECT_COLORS.get(p, Fore.CYAN) + p + Style.RESET_ALL for p in PROJECT_DEFAULTS.keys())}"),
            lambda suggested: _(f"Enter project type (default: {Fore.CYAN}{suggested}{Style.RESET_ALL}): "),
            lambda x, suggested: x.strip().lower() or suggested
        ),
        (
            lambda: _(f"Enter the folder path or GitHub URL (default: {Fore.BLUE}{os.getcwd()}{Style.RESET_ALL}): "),
            None,
            lambda x, _: x.strip() or os.getcwd()
        ),
        (
            lambda: _(f"Enter folder name to filter (default: {{}}): "),
            None,
            lambda x, _: x.strip() or None
        ),
        (
            lambda: _(f"Enter folders to exclude (comma-separated, default: {{}}): "),
            None,
            lambda x, _: [f.strip() for f in x.split(',')] if x.strip() else None
        ),
        (
            lambda: _(f"Enter file extensions to exclude (comma-separated, default: {{}}): "),
            None,
            lambda x, _: [e.strip().lower() for e in x.split(',')] if x.strip() else None
        ),
        (
            lambda: _(f"Enter keyword to filter file contents (default: {{}}): "),
            None,
            lambda x, _: x.strip() or None
        ),
        (
            lambda: _(f"Enter regex pattern to filter file contents (default: {{}}): "),
            None,
            lambda x, _: x.strip() or None
        ),
        (
            lambda: _(f"Enter output format ({Fore.CYAN}txt, json, md, html{Style.RESET_ALL}, default: {{}}): "),
            None,
            lambda x, _: x.strip().lower() or None
        ),
        (
            lambda: _(f"Enter minimum file size in bytes (default: {{}}): "),
            None,
            lambda x, _: int(x.strip()) if x.strip().isdigit() else None
        ),
        (
            lambda: _(f"Enter modified after date (YYYY-MM-DD, default: {{}}): "),
            None,
            lambda x, _: datetime.datetime.strptime(x.strip(), "%Y-%m-%d") if x.strip() else None
        )
    ]

    results = [None] * len(prompts)
    i = 0
    current_suggested_type = suggested_type
    config = load_config(current_suggested_type)

    while i < len(prompts):
        if i == 0:
            prompt_text = prompts[i][0]()
            prompt_text += f"\n{_( 'Suggested project type')}: {Fore.CYAN}{current_suggested_type}{Style.RESET_ALL}\n"
            prompt_text += prompts[i][1](current_suggested_type)
        elif i == 1:
            prompt_text = prompts[i][0]()
            if prompts[i][1]:
                prompt_text += prompts[i][1](current_suggested_type)
        else:
            config = load_config(results[0] or current_suggested_type) if i > 0 else config
            default_value = {
                0: current_suggested_type,
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
                prompt_text += prompts[i][1](current_suggested_type)

        user_input = input(prompt_text).strip()

        if user_input.lower() == "back" and i > 0:
            i -= 1
            results[i] = None
            if i == 1:
                current_suggested_type = detect_project_type(os.getcwd())
            if i == 0:
                current_suggested_type = "generic"
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
                current_suggested_type = detect_project_type(processed_input)
            except ValueError as e:
                print(f"{Fore.RED}❌ {_( 'Error')}: {e}{Style.RESET_ALL}")
                continue
        else:
            processed_input = prompts[i][2](user_input, current_suggested_type)

        if i == 0 and processed_input not in PROJECT_DEFAULTS:
            warning_msg = _("Warning: Unknown project type \"{processed_input}\", using \"{output_format}\"").format(
                processed_input=processed_input,
                output_format=config['output_format']
            )
            print(f"{Fore.YELLOW}⚠ {warning_msg}{Style.RESET_ALL}")
            processed_input = current_suggested_type
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
            
            structure = "\n".join([item for item, _ in get_structure(folder_path, filter_folder=filter_folder, exclude_folders=exclude_folders, exclude_extensions=exclude_extensions)])
            contents = get_file_contents(folder_path, [], filter_folder, exclude_folders, exclude_extensions, keyword, regex, min_size, modified_after)
            output = format_output(structure, contents, output_format)
            saved_path = save_and_open(output, folder_path, output_format, copy_to_clipboard=entries[_("Copy to Clipboard")].get() == "1")
            messagebox.showinfo(_( "Success"), _(f"Output saved to: {saved_path}"))
        except Exception as e:
            messagebox.showerror(_( "Error"), _(f"Error: {e}"))
        root.destroy()

    tk.Checkbutton(root, text=_( "Copy to Clipboard"), variable=tk.BooleanVar()).grid(row=len(fields), column=0, columnspan=2)
    tk.Button(root, text=_( "Generate"), command=submit).grid(row=len(fields)+1, column=0, columnspan=2, pady=10)

    root.mainloop()