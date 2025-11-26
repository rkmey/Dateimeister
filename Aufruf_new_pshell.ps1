param(
    [string]$TargetDir
)

# Prüfen, ob ein Verzeichnis übergeben wurde
if (-not (Test-Path $TargetDir)) {
    Write-Error "Das angegebene Verzeichnis '$TargetDir' existiert nicht."
    exit 1
}

# PowerShell mit Arbeitsverzeichnis öffnen
& $TargetDir\new_pshell.ps1 "$TargetDir"
