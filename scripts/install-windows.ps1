# Installs Ownhost on this Windows PC (agent + app) to run from source.
# Usage: right-click > "Run with PowerShell", or:  powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
# The environment lives outside the project folder (in case it is in a cloud-synced folder).
$venv = Join-Path $env:USERPROFILE ".venvs\ownhost"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "You need Python 3.11 or later: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $venv)) {
    python -m venv $venv
}
& "$venv\Scripts\python.exe" -m pip install --upgrade pip
& "$venv\Scripts\python.exe" -m pip install -e "$root[app]"

# Desktop shortcut that opens the app without a console window.
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Ownhost.lnk"))
$link.TargetPath = "$venv\Scripts\pythonw.exe"
$link.Arguments = "-m ownhost.app"
$link.WorkingDirectory = $root
$link.Save()

Write-Host ""
Write-Host "Done. Open 'Ownhost' from the desktop." -ForegroundColor Green
Write-Host "To let other PCs on the network manage this computer, allow port 8765 (TCP) in the firewall:"
Write-Host "  New-NetFirewallRule -DisplayName 'Ownhost' -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow"
