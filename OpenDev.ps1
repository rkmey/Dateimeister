param(
    [string]$TargetDir
)

# Prüfen, ob ein Verzeichnis übergeben wurde
if (-not (Test-Path $TargetDir)) {
    Write-Error "Das angegebene Verzeichnis '$TargetDir' existiert nicht."
    exit 1
}

# Explorer im Zielverzeichnis öffnen
Start-Process explorer.exe $TargetDir

# Git Bash im Arbeitsverzeichnis öffnen
Start-Process "C:\Program Files\Git\git-bash.exe" --cd="$TargetDir"

# Notepad++ öffnen
Start-Process "C:\Program Files\Notepad++\notepad++.exe"

# PowerShell mit Arbeitsverzeichnis öffnen
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$TargetDir'"

