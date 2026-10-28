@echo off
setlocal

cd /d "%~dp0"

echo Erstelle Dateimeister.zip ...

powershell -NoProfile -Command ^
  "$src = (Get-Location).Path; " ^
  "$dst = Join-Path (Split-Path $src -Parent) 'Dateimeister.zip'; " ^
  "$files = Get-ChildItem -LiteralPath $src -Recurse -File | Where-Object { " ^
  "  $_.FullName -notlike ($src + '\build\*') -and " ^
  "  $_.FullName -notlike ($src + '\dist\*') -and " ^
  "  $_.FullName -notlike ($src + '\__pycache__\*') -and " ^
  "  $_.FullName -notlike ($src + '\.git\*') -and " ^
  "  $_.FullName -notlike ($src + '\.vs\*') -and " ^
  "  $_.FullName -notlike ($src + '\.venv\*') " ^
  "}; " ^
  "Compress-Archive -Path $files.FullName -DestinationPath $dst -Force"

if errorlevel 1 (
    echo.
    echo FEHLER beim Erstellen der ZIP-Datei.
    pause
    exit /b 1
)

echo.
echo Fertig:
echo %~dp0..\Dateimeister.zip
pause
