# Instala Ownhost en este PC con Windows (agente + app).
# Uso: clic derecho > "Ejecutar con PowerShell", o:  powershell -ExecutionPolicy Bypass -File scripts\instalar-windows.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
# El entorno va fuera de la carpeta del proyecto (por si está en una carpeta sincronizada en la nube).
$venv = Join-Path $env:USERPROFILE ".venvs\ownhost"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Necesitas Python 3.11 o superior: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $venv)) {
    python -m venv $venv
}
& "$venv\Scripts\python.exe" -m pip install --upgrade pip
& "$venv\Scripts\python.exe" -m pip install -e "$root[app]"

# Acceso directo en el escritorio que abre la app sin ventana de consola.
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Ownhost.lnk"))
$link.TargetPath = "$venv\Scripts\pythonw.exe"
$link.Arguments = "-m ownhost.app"
$link.WorkingDirectory = $root
$link.Save()

Write-Host ""
Write-Host "Listo. Abre 'Ownhost' desde el escritorio." -ForegroundColor Green
Write-Host "Para que otros PCs de la red gestionen este equipo, permite el puerto 8765 (TCP) en el firewall:"
Write-Host "  New-NetFirewallRule -DisplayName 'Ownhost' -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow"
