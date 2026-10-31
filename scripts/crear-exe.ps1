# Genera dist\Ownhost.exe (app + agente en un solo archivo, sin necesidad de Python).
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\crear-exe.ps1
# Clave de CurseForge opcional: archivo "curseforge.key" en la raíz o variable CURSEFORGE_API_KEY.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $env:USERPROFILE ".venvs\ownhost"
$python = "$venv\Scripts\python.exe"
# Los archivos intermedios van a TEMP para no llenar la carpeta sincronizada.
$work = Join-Path $env:TEMP "ownhost-build"

if (-not (Test-Path $python)) {
    python -m venv $venv
}
& $python -m pip install --upgrade pip
& $python -m pip install -e "$root[app]" pyinstaller

# Siempre se reemplazan los archivos de dist\ (nunca se crean otras carpetas).
# Windows no deja sobrescribir un exe en uso, pero sí renombrarlo: el que está abierto se aparta
# como .old (sigue funcionando hasta que se cierre) y el nuevo ocupa su sitio.
$dist = Join-Path $root "dist"
New-Item -ItemType Directory -Force $dist | Out-Null
Get-ChildItem $dist -Filter "*.old" -ErrorAction SilentlyContinue | ForEach-Object {
    try { Remove-Item $_.FullName -Force -ErrorAction Stop } catch { }  # los que sigan abiertos, la próxima vez
}
$exe = Join-Path $dist "Ownhost.exe"
if (Test-Path $exe) {
    try { [IO.File]::Open($exe, 'Open', 'ReadWrite', 'None').Close() }
    catch {
        $old = "$exe.$(Get-Date -Format yyyyMMddHHmmss).old"
        Rename-Item $exe $old
        Write-Host "Ownhost está abierto: la versión en uso se ha apartado como $(Split-Path $old -Leaf)." -ForegroundColor Yellow
        Write-Host "Cierra Ownhost y vuelve a abrir dist\Ownhost.exe para usar la nueva." -ForegroundColor Yellow
    }
}

# Misma compilación (fecha) para Windows y Linux: es la etiqueta de la versión publicada, y la app
# compara la suya con ella para saber si hay una más nueva.
if (-not $env:OWNHOST_BUILD) { $env:OWNHOST_BUILD = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss") }
Write-Host "Compilación $env:OWNHOST_BUILD (etiqueta para publicar: v$env:OWNHOST_BUILD)"
& $python (Join-Path $root "scripts\embed_key.py")
try {
    $hidden = @("--hidden-import", "ownhost._build")
    if (Test-Path (Join-Path $root "ownhost\_embedded.py")) { $hidden += @("--hidden-import", "ownhost._embedded") }
    & $python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name Ownhost `
        --icon (Join-Path $root "ownhost\app\assets\icon.ico") `
        --add-data "$(Join-Path $root 'ownhost\app\assets');ownhost/app/assets" `
        --add-data "$(Join-Path $root 'ownhost\agent\web');ownhost/agent/web" `
        --paths $root `
        --collect-submodules uvicorn `
        --collect-submodules websockets `
        --collect-submodules ownhost.locale `
        @hidden `
        --distpath $dist `
        --workpath $work `
        --specpath $work `
        (Join-Path $root "ownhost\app\__main__.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    # La clave no se queda en el código fuente.
    & $python (Join-Path $root "scripts\embed_key.py") --clean
}

Write-Host ""
Write-Host "Listo: $(Join-Path $dist 'Ownhost.exe')" -ForegroundColor Green

# --- Versión para Linux, compilada en un contenedor AlmaLinux 8 con Docker ---
# (glibc 2.28: funciona en casi cualquier distribución: Debian 10+, Ubuntu 20.04+, RHEL 8+, Fedora, Arch...)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker no está instalado: se omite la versión para Linux." -ForegroundColor Yellow
    & $python (Join-Path $root "scripts\comprobar_privacidad.py") (Join-Path $dist "Ownhost.exe")
    if ($LASTEXITCODE -ne 0) { Write-Host "Revisa el aviso de privacidad antes de compartir." -ForegroundColor Red; exit 1 }
    exit 0
}
docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    $desktop = Join-Path (Split-Path (Split-Path (Split-Path (Get-Command docker).Source))) "Docker Desktop.exe"
    if (Test-Path $desktop) {
        Write-Host "Arrancando Docker Desktop..."
        Start-Process $desktop
        for ($i = 0; $i -lt 60 -and $LASTEXITCODE -ne 0; $i++) {
            Start-Sleep -Seconds 3
            docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
        }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker no responde: se omite la versión para Linux." -ForegroundColor Yellow
        & $python (Join-Path $root "scripts\comprobar_privacidad.py") (Join-Path $dist "Ownhost.exe")
        if ($LASTEXITCODE -ne 0) { Write-Host "Revisa el aviso de privacidad antes de compartir." -ForegroundColor Red; exit 1 }
        exit 0
    }
}
$linuxOut = "/src/" + ($dist.Substring($root.Length + 1) -replace '\\', '/') + "/linux"
docker run --rm -e OWNHOST_BUILD -v "${root}:/src" almalinux:8 `
    bash /src/scripts/crear-binario-linux.sh /src $linuxOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Listo: $(Join-Path $root ($linuxOut -replace '^/src/', '') )" -ForegroundColor Green

# Ningún dato de quien compila (usuario, equipo, IPs...) debe acabar dentro de lo que se comparte.
$linuxBin = Join-Path $root (($linuxOut -replace '^/src/', '') + "/Ownhost")
& $python (Join-Path $root "scripts\comprobar_privacidad.py") (Join-Path $dist "Ownhost.exe") $linuxBin
if ($LASTEXITCODE -ne 0) { Write-Host "Revisa el aviso de privacidad antes de compartir." -ForegroundColor Red; exit 1 }
