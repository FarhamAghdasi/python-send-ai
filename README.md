# Python Project Structure and File Reader

This tool generates a folder structure and file contents for a given directory, with support for filtering, multiple output formats, and project-specific configurations.

## Features
- Display folder structure with customizable filters for folders and files.
- Read file contents with keyword and regex filtering.
- Output in plain text, JSON, or Markdown formats.
- Interactive mode with default settings from `config.json`.
- Colored console output and progress feedback.
- Project type support for Python, Node.js, Java, and generic projects with tailored defaults.

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd python-ai-data
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Windows) Run using the batch file:
   ```bash
   ai-get.bat
   ```
   (Linux/macOS) Run directly:
   ```bash
   python main.py
   ```

## Usage
### Interactive Mode
Run without arguments to enter interactive mode:
```bash
python main.py
```
Follow prompts to specify project type, folder path, filters, and output format. Example:
```
Available project types: python, nodejs, java, generic
Enter project type (default: generic): nodejs
Enter the folder path (default: /current/path): .
Enter folder name to filter (default: src): src
Enter folders to exclude (comma-separated, default: .git,node_modules,dist,build): .git
Enter file extensions to exclude (comma-separated, default: .svg,.log): .svg
Enter keyword to filter file contents (default: None): import
Enter regex pattern to filter file contents (default: None): ^import\s+
Enter output format (txt, json, md, default: txt): md
```

### CLI Mode
Example for a Node.js project:
```bash
python main.py -P nodejs -C "/path/to/project" ".git" ".svg,.log" -F src -K import -R "^import\s+" --format md
```

### Configuration
Edit `config.json` to customize settings for different project types:
```json
{
  "projects": {
    "python": {
      "exclude_folders": [".git", ".venv", "__pycache__"],
      "exclude_extensions": [".svg", ".pyc"],
      "filter_folder": null,
      "keyword": null,
      "regex": null,
      "output_format": "txt"
    },
    "nodejs": {
      "exclude_folders": [".git", "node_modules", "dist", "build"],
      "exclude_extensions": [".svg", ".log"],
      "filter_folder": "src",
      "keyword": null,
      "regex": null,
      "output_format": "txt"
    },
    "java": {
      "exclude_folders": [".git", "target", ".idea"],
      "exclude_extensions": [".svg", ".class"],
      "filter_folder": "src",
      "keyword": null,
      "regex": null,
      "output_format": "txt"
    },
    "generic": {
      "exclude_folders": [".git"],
      "exclude_extensions": [".svg"],
      "filter_folder": null,
      "keyword": null,
      "regex": null,
      "output_format": "txt"
    }
  }
}
```

## Sample Output (Markdown)
```markdown
# Project Structure

```tree
├── [DIR] src
│   ├── [FILE] index.js
│   └── [FILE] utils.js
```

# File Contents

```text
----------------------------------------
File: /path/to/project/src/index.js
----------------------------------------
import express from 'express';
...
```
```

## Requirements
- Python 3.8+
- Dependencies listed in `requirements.txt`

## Testing
Run tests with:
```bash
pytest --cov=./ --cov-report=xml
```

## License
MIT License
By Farham Aghdasi