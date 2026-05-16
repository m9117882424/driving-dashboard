@echo off
chcp 65001 >nul
cd /d "%~dp0"
python sync_wialon_once.py --days 30
pause
