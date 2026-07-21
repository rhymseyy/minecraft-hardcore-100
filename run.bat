bat@echo off
set SESSION=%1
set STATS=C:\Users\Brandon\AppData\Roaming\.minecraft\saves\HardcoreRun\stats\61522d8c-e347-4750-810a-a611d44fe950.json

python src\parse_stats.py --stats "%STATS%" --session %SESSION%
python src\dashboard.py

git add .
git commit -m "Session %SESSION% complete"
git push

echo Done. Session %SESSION% logged.
pause
