# Python Project Structure and File Reader

This tool generates a folder structure and file contents for a given directory or GitHub repository, with support for advanced filtering, multiple output formats, GUI, and multilingual interface.

## Features
- Display folder structure with customizable filters for folders, files, size, and modification date.
- Read file contents with keyword, regex, and sensitive content detection.
- Output in plain text, JSON, Markdown, or HTML formats.
- Interactive mode or GUI with default settings from `config.json`.
- Multilingual support (English, Persian) with `--lang`.
- Colored console output, progress feedback, and logging to file.
- Project type support for Python, Node.js, Java, Go, and generic projects.
- Remote repository support via GitHub URLs with `--remote`.
- Copy output to clipboard with `--copy`.
- Threaded file processing for performance.

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
Follow prompts to specify project type, folder/URL, filters, and output format. Example:
```
Available project types: python, nodejs, java, go, generic
Enter project type (default: generic): nodejs
Enter the folder path or GitHub URL (default: /current/path): https://github.com/user/repo
Enter folder name to filter (default: src): src
Enter folders to exclude (comma-separated, default: .git,node_modules,dist,build): .git
Enter file extensions to exclude (comma-separated, default: .svg,.log): .svg
Enter keyword to filter file contents (default: None): import
Enter regex pattern to filter file contents (default: None): ^import\s+
Enter output format (txt, json, md, html, default: txt): html
Enter minimum file size in bytes (default: 0): 1000
Enter modified after date (YYYY-MM-DD, default: None): 2023-01-01
```

### CLI Mode
Example for a Node.js project:
```bash
python main.py -P nodejs -C "/path/to/project" ".git" ".svg,.log" -F src -K import -R "^import\s+" --format html --min-size 1000 --modified-after 2023-01-01
```

Example for a GitHub repository:
```bash
python main.py --remote https://github.com/user/repo --format html --copy
```

### GUI Mode
Run with GUI:
```bash
python main.py --gui
```

### Configuration
Edit `config.json` to customize settings for different project types:
```json
{
  "projects": {
    "python": {
      "exclude_folders": [".git", ".venv", "__pycache__"],
      "exclude_extensions": [".svg", ".pyc", ".jpg", ".png", ".bin"],
      "filter_folder": null,
      "keyword": null,
      "regex": null,
      "output_format": "txt",
      "min_size": 0,
      "modified_after": null
    }
  }
}
```

## Sample Output (HTML)
```html
<h1>Project Structure</h1>
<pre><code>├── [DIR] src
│   ├── [FILE] index.js
│   └── [FILE] utils.js
</code></pre>
<h1>File Contents</h1>
<pre><code>----------------------------------------
File: /path/to/project/src/index.js
----------------------------------------
import express from 'express';
...
</code></pre>
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