@echo off
REM Lance la version web locale de SkyWings Fuel Planner (une seule ligne, double-clic OK).
REM Usage : web.bat            -> http://127.0.0.1:8765
REM         web.bat --demo     -> données de démonstration (hors-ligne)
REM         web.bat --port 9000
cd /d "%~dp0"
python -m fuelplanner --web %*
pause
