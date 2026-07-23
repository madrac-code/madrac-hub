@echo off
echo [*] Activando venv central (madrac-hub)...
call "%~dp0..\..\venv\Scripts\activate.bat"
python asistente.py
pause
