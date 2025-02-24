import os
import pyperclip

def get_structure(folder_path, indent=0, filter_folder=None):
    """Get the structure of the folder as a string, ignoring .git folder."""
    structure = ""
    for item in os.listdir(folder_path):
        if item == ".git":  # Ignore .git folder
            continue
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            if filter_folder and filter_folder in item:
                structure += ' ' * indent + f'[DIR] {item}\n'
                structure += get_structure(item_path, indent + 4, filter_folder)
            elif not filter_folder:
                structure += ' ' * indent + f'[DIR] {item}\n'
                structure += get_structure(item_path, indent + 4, filter_folder)
        else:
            structure += ' ' * indent + f'[FILE] {item}\n'
    return structure

def get_file_contents(folder_path, filter_folder=None):
    """Get the content of each file in the folder as a string, ignoring .git folder and .svg files."""
    contents = ""
    for root, dirs, files in os.walk(folder_path):
        if ".git" in root:  # Ignore .git folder
            continue
        if filter_folder and filter_folder not in root:
            continue
        for file in files:
            if file.endswith(".svg"):  # Ignore .svg files
                continue
            file_path = os.path.join(root, file)
            contents += f'\nContent of {file_path}:\n'
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contents += f.read() + '\n'
            except Exception as e:
                contents += f'Could not read file {file_path}: {e}\n'
    return contents

def main():
    folder_path = input("Enter the folder path: ")
    filter_folder = input("Enter folder name to filter (leave empty to show all): ")

    # Get the structure and file contents
    structure = get_structure(folder_path, filter_folder=filter_folder)
    contents = get_file_contents(folder_path, filter_folder=filter_folder)

    # Combine structure and contents
    output = "Folder Structure:\n" + structure + "\nFile Contents:\n" + contents

    # Copy to clipboard
    pyperclip.copy(output)
    print("\nOutput has been copied to your clipboard! You can now paste it anywhere.")

if __name__ == "__main__":
    main()
