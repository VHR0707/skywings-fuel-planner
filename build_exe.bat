@echo off
REM ============================================================
REM  Build de l'executable SkyWingsFuelPlanner.exe
REM  Prerequis : Python 3.10+ avec pip, puis :  pip install pyinstaller
REM  Sortie    : dist\SkyWingsFuelPlanner.exe  (onefile, logo + donnees demo embarques)
REM ============================================================
cd /d "%~dp0"

python -m PyInstaller --onefile --clean --noconfirm ^
    --name SkyWingsFuelPlanner ^
    --add-data "%~dp0assets;assets" ^
    --add-data "%~dp0data;data" ^
    --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" ^
    "%~dp0main.py"

if errorlevel 1 (
    echo ECHEC DU BUILD
    pause
    exit /b 1
)

echo.
echo Exe genere : dist\SkyWingsFuelPlanner.exe
echo   - double-clic          : ouvre l'IHM graphique
REM    - SkyWingsFuelPlanner.exe --cli --list : mode ligne de commande
echo   - SkyWingsFuelPlanner.exe --cli --fleet "C172" --nm 150
pause
