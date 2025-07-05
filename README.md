# Python Project Structure and File Reader

This tool generates a folder structure and file contents for a given directory, with support for filtering and multiple output formats.

## Features
- Display folder structure with customizable filters.
- Read file contents with keyword and regex filtering.
- Output in plain text, JSON, or Markdown.
- Interactive mode with default settings from `config.json`.
- Colored console output and progress feedback.

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
Follow prompts to specify folder path, filters, and output format.

### CLI Mode
Example:
```bash
python main.py -C "/path/to/project" ".git,.venv" ".svg,.png" -F src -K import -R "^def\\s+\\w+" --format md
```

## Configuration
Edit `config.json` to set default values:
```json
{
  "exclude_folders": [".git"],
  "exclude_extensions": [".svg"],
  "filter_folder": null,
  "keyword": null,
  "regex": null,
  "output_format": "txt"
}
```

## Requirements
- Python 3.8+
- Dependencies listed in `requirements.txt`

## License
MIT License
By Farham Aghdasi