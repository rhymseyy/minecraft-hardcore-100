@echo off
set STATS=C:\Users\Brandon\AppData\Roaming\.minecraft\saves\harcore100\stats\61522d8c-e347-4750-810a-a611d44fe950.json

if "%1"=="snap" goto snapshot

set SESSION=%1
echo.
echo [SESSION %SESSION%] Parsing stats...
python src\parse_stats.py --stats "%STATS%" --session %SESSION%
python src\dashboard.py
git add .
git commit -m "Session %SESSION% complete"
git push
echo.
echo Done. Session %SESSION% logged and pushed to GitHub.
pause
goto end

:snapshot
set SNAPNUM=%2
set SESSION=%3
echo.
echo [SNAP %SNAPNUM% / SESSION %SESSION%] Taking mid-session snapshot...
python src\snapshot.py --stats "%STATS%" --snapshot %SNAPNUM% --session %SESSION%
echo.
echo Snapshot done. Keep playing.
pause

:end