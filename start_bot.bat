@echo off
cd /d "%~dp0"
call venv\Scripts\activate

echo Checking requirements...
pip install -r requirements.txt -q --disable-pip-version-check
echo Requirements OK.

python bot.py
pause