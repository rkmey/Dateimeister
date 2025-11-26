param(
    [string]$TargetDir
)

# Prüfen, ob ein Verzeichnis übergeben wurde
if (-not (Test-Path $TargetDir)) {
    Write-Error "Das angegebene Verzeichnis '$TargetDir' existiert nicht."
    exit 1
}


Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$width = [int]($screen.Width * 0.9)
$height = [int]($screen.Height * 0.2)
$left = [int](($screen.Width - $width) / 2)
$top = $screen.Height - $height - 40

$code = @'
using System;
using System.Runtime.InteropServices;
public class WindowAPI {
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
}
'@

Add-Type -TypeDefinition $code

# PowerShell starten
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$TargetDir'"

# Warten bis Fenster da ist
Start-Sleep -Seconds 2

# Fenster positionieren
$windowHandle = [WindowAPI]::GetForegroundWindow()
if ($windowHandle -ne [IntPtr]::Zero) {
    [WindowAPI]::MoveWindow($windowHandle, $left, $top, $width, $height, $true)
    Write-Host "Fenster positioniert: $width × $height" -ForegroundColor Green
}