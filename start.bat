@echo off
REM MindIsle（心屿）一键启动（双击即可，等价于 start.ps1）
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
