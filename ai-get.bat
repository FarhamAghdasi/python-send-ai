@echo off
:: Install required Python packages
pip install -r requirements.txt

:: clear
cls

:: set title app
title Python Collect Data

:: Run the main.py script
python "D:\$RTL-THEMES Apps\python-ai-data\main.py"

:: Pause the script to keep the window open after execution
pause
