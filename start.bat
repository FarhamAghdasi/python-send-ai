@echo off
:: Install required Python packages
pip install -r requirements.txt

:: Run the main.py script
python main.py

:: Pause the script to keep the window open after execution
pause
