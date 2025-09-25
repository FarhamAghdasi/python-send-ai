# Python Project Structure and File Reader

This tool generates a folder structure and file contents for a given directory or GitHub repository, with support for advanced filtering, multiple output formats, GUI, CLI, and semi-interactive CLI modes, and multilingual interface.

## Features
- Display folder structure with customizable filters for folders, files, size, and modification date.
- Read file contents with keyword, regex, and sensitive content detection.
- Output in plain text, JSON, Markdown, or HTML formats.
- Interactive CLI mode, semi-interactive CLI mode (with arrow key selection), or GUI with default settings from `config.json`.
- Multilingual support (English, Persian) with `--lang`.
- Colored console output, progress feedback, and logging to file.
- Project type support for Python, Node.js, Java, Go, Laravel, Next.js, React.js, and generic projects.
- Remote repository support via GitHub URLs with `--remote`.
- Copy output to clipboard with `--copy`.
- Threaded file processing for performance.
- Save user settings as profiles in `profiles.json`.
- Add AI prompts for Error Fixing, Explain to AI, Adding New Feature, and Auto-Commiter.
- Modular code structure with utilities in `utils` folder.

## Project Structure
```
├── [FILE] .gitignore
├── [FILE] ai-get.bat
├── [FILE] config.json
├── [DIR] locale
│   └── [DIR] fa
│       └── [DIR] LC_MESSAGES
│           └── [FILE] messages.po
├── [FILE] main.py
├── [FILE] README.md
├── [FILE] requirements.txt
├── [DIR] tests
│   └── [FILE] test_main.py
└── [DIR] utils
    ├── [FILE] file_utils.py
    ├── [FILE] config_utils.py
    ├── [FILE] prompt_utils.py
    └── [FILE] ui_utils.py
```

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
Follow prompts to specify project type, folder/URL, filters, and output format.

### Semi-Interactive CLI Mode
Run with arrow key-based folder/file selection:
```bash
python main.py --semi
```
Navigate with arrow keys, press Enter to toggle selection, and 'q' to finish.

### CLI Mode
Example for a Laravel project:
```bash
python main.py -P laravel -C "/path/to/laravel-project" ".git,vendor" ".env,.blade.php" -F app -K route --format md
```

Example for a Next.js project:
```bash
python main.py -P nextjs --remote https://github.com/user/nextjs-repo --format html --copy
```

Example for a React.js project:
```bash
python main.py -P reactjs -C "/path/to/react-app" ".git,node_modules" ".d.ts" -F src -K component --min-size 500
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
    "laravel": {
      "exclude_folders": [".git", "vendor", "node_modules", "storage", "bootstrap/cache"],
      "exclude_extensions": [".svg", ".log", ".jpg", ".png", ".bin", ".env", ".blade.php"],
      "filter_folder": "app",
      "keyword": null,
      "regex": null,
      "output_format": "txt",
      "min_size": 0,
      "modified_after": null
    },
    "nextjs": {
      "exclude_folders": [".git", ".next", "node_modules", "out"],
      "exclude_extensions": [".svg", ".log", ".jpg", ".png", ".bin"],
      "filter_folder": "app",
      "keyword": null,
      "regex": null,
      "output_format": "txt",
      "min_size": 0,
      "modified_after": null
    },
    "reactjs": {
      "exclude_folders": [".git", "node_modules", "build", "dist"],
      "exclude_extensions": [".svg", ".log", ".jpg", ".png", ".bin", ".d.ts"],
      "filter_folder": "src",
      "keyword": null,
      "regex": null,
      "output_format": "txt",
      "min_size": 0,
      "modified_after": null
    }
  }
}
```

### Profiles
Save settings as a profile after processing:
```bash
Would you like to save these settings as a profile? (y/n): y
Enter profile name: my_laravel_profile
```
Profiles are saved in `profiles.json`.

### Prompts
Add AI prompts at the start of interactive mode:
```bash
Would you like to add a prompt? (y/n): y
Select a prompt type (use arrow keys, Enter to select, 'q' to skip):
→ error_fixing
  explain_to_ai
  adding_new_feature
  auto_commiter
```
Prompts are saved in the `prompts` folder as text files.

## Sample Output (HTML)
```html
<h1>Project Structure</h1>
<pre><code>├── [DIR] app
│   ├── [FILE] Http/Controllers
│   └── [FILE] Models
</code></pre>
<h1>File Contents</h1>
<pre><code>----------------------------------------
File: /path/to/laravel/app/Models/User.php
----------------------------------------
<?php
namespace App\Models;
// ...
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