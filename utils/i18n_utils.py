import os
import logging
import gettext

def setup_i18n():
    """Initialize internationalization (i18n) settings."""
    try:
        lang = os.getenv("LANG", "en")
        if lang == "fa":
            translation = gettext.translation("messages", localedir="locale", languages=["fa"])
            translation.install()
            return translation.gettext
        else:
            return lambda x: x
    except FileNotFoundError as e:
        logging.warning(f"Translation file not found: {e}. Falling back to English.")
        return lambda x: x

_ = setup_i18n()