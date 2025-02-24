# Folder Structure & Content Analyzer

A Python utility script that generates a directory structure overview and file contents while automatically ignoring version control files and image assets. Includes clipboard integration for easy sharing.

## ✨ Features

- 🗂️ Recursive folder structure visualization
- 📄 Automatic file content extraction
- 🚫 Built-in ignores for:
  - `.git` folders (Git repositories)
  - `.svg` files (vector images)
- 📋 One-click clipboard copy functionality
- 🔍 Optional folder filtering
- 💻 Cross-platform compatibility

## ⚙️ Requirements

- Python 3.6+
- `pyperclip` package

Install dependencies:  
```bash
pip install pyperclip
```

## 🚀 Basic Usage

1. Run the script:
```bash
python folder_analyzer.py
```

2. Enter folder path when prompted:  
`Enter the folder path: /path/to/your/project`

3. Filter options (optional):  
`Enter folder name to filter (leave empty to show all): src`

4. Results automatically copied to clipboard 📋

## 📂 Output Format

### Structure Example:
```
[DIR] src
    [FILE] main.py
    [DIR] utils
        [FILE] helpers.py
```

### Content Example:
```
Content of /path/to/src/main.py:
import os

def main():
    print("Hello World!")
...

Content of /path/to/src/utils/helpers.py:
def helper_function():
    return "Helpful!"
...
```

## ⚠️ Important Notes

1. **File Size Warning**:
   - Avoid running on folders with large binaries/media files
   - No file size limits implemented

2. **Excluded by Default**:
   - Hidden files/folders (names starting with `.`)
   - Version control systems (`.git`, `.svn`, etc.)
   - SVG image files

3. **Encoding Handling**:
   - Only reads UTF-8 encoded files
   - Skips binary files automatically

4. **Security**:
   - Avoid running on untrusted directories
   - Clipboard contents remain until overwritten

## 📜 License

This script is provided under [MIT License](https://opensource.org/licenses/MIT).  

> **Note:** The clipboard functionality requires appropriate permissions on your operating system.
```

This README includes:
- Clear installation and usage instructions
- Visual examples of input/output
- Security considerations
- Platform requirements
- File handling limitations
- License information

Key improvements over basic documentation:
1. Emoji-enhanced section headers
2. Clear visual hierarchy
3. Warning callouts for critical information
4. Multiple examples of usage scenarios
5. Cross-platform considerations
6. Security best practices
