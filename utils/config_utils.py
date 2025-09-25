import os
import json
import logging
from colorama import Fore, Style
from .i18n_utils import _
from .common_utils import validate_path

PROJECT_DEFAULTS = {
    "python": {
        "exclude_folders": [".git", ".venv", "__pycache__"],
        "exclude_extensions": [".svg", ".pyc", ".jpg", ".png", ".bin"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "nodejs": {
        "exclude_folders": [".git", "node_modules", "dist", "build"],
        "exclude_extensions": [".svg", ".log", ".jpg", ".png", ".bin"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "java": {
        "exclude_folders": [".git", "target", ".idea"],
        "exclude_extensions": [".svg", ".class", ".jpg", ".png", ".bin"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "go": {
        "exclude_folders": [".git", "vendor"],
        "exclude_extensions": [".svg", ".jpg", ".png", ".bin"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "laravel": {
        "exclude_folders": [".git", "vendor", "storage", "public/build"],
        "exclude_extensions": [".svg", ".jpg", ".png", ".bin", ".lock"],
        "filter_folder": "app",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "nextjs": {
        "exclude_folders": [".git", "node_modules", ".next", "public"],
        "exclude_extensions": [".svg", ".jpg", ".png", ".bin"],
        "filter_folder": "pages",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "reactjs": {
        "exclude_folders": [".git", "node_modules", "dist", "build"],
        "exclude_extensions": [".svg", ".jpg", ".png", ".bin"],
        "filter_folder": "src",
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    },
    "generic": {
        "exclude_folders": [".git"],
        "exclude_extensions": [".svg", ".jpg", ".png", ".bin"],
        "filter_folder": None,
        "keyword": None,
        "regex": None,
        "output_format": "txt",
        "min_size": 0,
        "modified_after": None
    }
}

PROJECT_COLORS = {
    "python": Fore.MAGENTA,
    "nodejs": Fore.YELLOW,
    "java": Fore.GREEN,
    "go": Fore.BLUE,
    "laravel": Fore.RED,
    "nextjs": Fore.CYAN,
    "reactjs": Fore.LIGHTBLUE_EX,
    "generic": Fore.WHITE
}

def detect_project_type(folder_path):
    """Detect project type based on directory contents."""
    try:
        folder_path = validate_path(folder_path)
        items = os.listdir(folder_path)
        if "composer.json" in items:
            return "laravel"
        if any(f in items for f in ["next.config.js", "next.config.mjs"]):
            return "nextjs"
        if "package.json" in items and any("react" in open(os.path.join(folder_path, "package.json")).read().lower() for _ in [1]):
            return "reactjs"
        if any(f in items for f in ["package.json", "npm-shrinkwrap.json"]):
            return "nodejs"
        if any(f in items for f in ["pyproject.toml", "requirements.txt", "setup.py"]):
            return "python"
        if any(f in items for f in ["pom.xml", "build.gradle"]):
            return "java"
        if "go.mod" in items:
            return "go"
    except Exception as e:
        logging.error(_(f"Error detecting project type: {e}"))
    return "generic"

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
            logging.warning(_(f"Could not load config.json: {e}"))

    return config["projects"].get(project_type, PROJECT_DEFAULTS["generic"])

def save_profile(profile_name, project_type, filter_folder, exclude_folders, exclude_extensions, keyword, regex, output_format, min_size, modified_after):
    profiles_path = os.path.join(os.getcwd(), "profiles.json")
    profiles = {}
    
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, 'r', encoding='utf-8') as f:
                profiles = json.load(f)
        except Exception as e:
            logging.warning(_(f"Could not load profiles.json: {e}"))

    profiles[profile_name] = {
        "project_type": project_type,
        "filter_folder": filter_folder,
        "exclude_folders": exclude_folders,
        "exclude_extensions": exclude_extensions,
        "keyword": keyword,
        "regex": regex,
        "output_format": output_format,
        "min_size": min_size,
        "modified_after": modified_after.isoformat() if modified_after else None
    }

    try:
        with open(profiles_path, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        logging.info(_(f"Profile '{profile_name}' saved successfully"))
    except Exception as e:
        logging.error(_(f"Could not save profile: {e}"))
        raise ValueError(_(f"Could not save profile: {e}"))

def load_profile(profile_name):
    profiles_path = os.path.join(os.getcwd(), "profiles.json")
    if os.path.exists(profiles_path):
        try:
            with open(profiles_path, 'r', encoding='utf-8') as f:
                profiles = json.load(f)
                return profiles.get(profile_name)
        except Exception as e:
            logging.warning(_(f"Could not load profiles.json: {e}"))
    return None