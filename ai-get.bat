@echo off
:: Install required Python packages
pip install -r requirements.txt

:: clear
cls

:: set title app
title Python Collect Data

:: Run the main.py script with optional GUI
python "main.py" %* --log-file "output/log.txt"

:: Pause the script to keep the window open after execution
pause