import os
import logging
import gettext
from colorama import Fore, Style

# Initialize i18n
lang = os.getenv("LANG", "en")
if lang == "fa":
    translation = gettext.translation("messages", localedir="locale", languages=["fa"])
    translation.install()
    _ = translation.gettext
else:
    _ = lambda x: x

PROMPT_TEMPLATES = {
    "error_fixing": """
Analyze the following code and identify any errors or bugs. Provide detailed explanations and suggest fixes.

Code:
{content}

Please provide:
1. Identified errors or potential issues
2. Suggested fixes with code snippets
3. Explanation of why these fixes are necessary
""",
    "explain_to_ai": """
Explain the following code in simple terms, as if teaching it to an AI with basic programming knowledge. Break down the code into parts and describe what each part does.

Code:
{content}
""",
    "adding_new_feature": """
Based on the following code, suggest how to implement a new feature. Provide a detailed plan, including code snippets and explanations of how the new feature integrates with the existing code.

Code:
{content}

Proposed Feature: [Describe the feature here]
""",
    "auto_commiter": """
Analyze the following code changes and suggest an appropriate Git commit message. The message should be concise, descriptive, and follow conventional commit guidelines (e.g., feat, fix, docs, etc.).

Code:
{content}

Suggested Commit Message:
"""
}

def save_prompt(prompt_type, content):
    os.makedirs("prompts", exist_ok=True)
    prompt_file = os.path.join("prompts", f"{prompt_type}.txt")
    try:
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(PROMPT_TEMPLATES[prompt_type].format(content=content))
        logging.info(_(f"Prompt '{prompt_type}' saved to {prompt_file}"))
        return prompt_file
    except Exception as e:
        logging.error(_(f"Could not save prompt: {e}"))
        raise ValueError(_(f"Could not save prompt: {e}"))