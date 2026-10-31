# Builds dist\Ownhost.exe (app + agent in a single file, no Python needed).
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\build.ps1
# Optional CurseForge key: "curseforge.key" file at the root or the CURSEFORGE_API_KEY variable.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $env:USERPROFILE ".venvs\ownhost"
$python = "$venv\Scripts\python.exe"
# Intermediate files go to TEMP so they don't fill up the synced folder.
$work = Join-Path $env:TEMP "ownhost-build"

if (-not (Test-Path $python)) {
    python -m venv $venv
}
& $python -m pip install --upgrade pip
& $python -m pip install -e "$root[app]" pyinstaller

# The files in dist\ are always replaced (no other folders are ever created).
# Windows doesn't allow overwriting an exe in use, but it does allow renaming it: the open one is moved
# aside as .old (it keeps working until it's closed) and the new one takes its place.
$dist = Join-Path $root "dist"
New-Item -ItemType Directory -Force $dist | Out-Null
Get-ChildItem $dist -Filter "*.old" -ErrorAction SilentlyContinue | ForEach-Object {
    try { Remove-Item $_.FullName -Force -ErrorAction Stop } catch { }  # any still open: next time
}
$exe = Join-Path $dist "Ownhost.exe"
if (Test-Path $exe) {
    try { [IO.File]::Open($exe, 'Open', 'ReadWrite', 'None').Close() }
    catch {
        $old = "$exe.$(Get-Date -Format yyyyMMddHHmmss).old"
        Rename-Item $exe $old
        Write-Host "Ownhost is open: the version in use has been moved aside as $(Split-Path $old -Leaf)." -ForegroundColor Yellow
        Write-Host "Close Ownhost and reopen dist\Ownhost.exe to use the new one." -ForegroundColor Yellow
    }
}

# Same build (date) for Windows and Linux: it's the tag of the published release, and the app
# compares its own build with it to know whether there's a newer one.
if (-not $env:OWNHOST_BUILD) { $env:OWNHOST_BUILD = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss") }
Write-Host "Build $env:OWNHOST_BUILD (tag to publish: v$env:OWNHOST_BUILD)"
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
    # The key doesn't stay in the source code.
    & $python (Join-Path $root "scripts\embed_key.py") --clean
}

Write-Host ""
Write-Host "Done: $(Join-Path $dist 'Ownhost.exe')" -ForegroundColor Green

# --- Linux version, built in an AlmaLinux 8 container with Docker ---
# (glibc 2.28: works on almost any distribution: Debian 10+, Ubuntu 20.04+, RHEL 8+, Fedora, Arch...)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is not installed: skipping the Linux version." -ForegroundColor Yellow
    & $python (Join-Path $root "scripts\check_privacy.py") (Join-Path $dist "Ownhost.exe")
    if ($LASTEXITCODE -ne 0) { Write-Host "Check the privacy warning before sharing." -ForegroundColor Red; exit 1 }
    exit 0
}
docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    $desktop = Join-Path (Split-Path (Split-Path (Split-Path (Get-Command docker).Source))) "Docker Desktop.exe"
    if (Test-Path $desktop) {
        Write-Host "Starting Docker Desktop..."
        Start-Process $desktop
        for ($i = 0; $i -lt 60 -and $LASTEXITCODE -ne 0; $i++) {
            Start-Sleep -Seconds 3
            docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
        }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker is not responding: skipping the Linux version." -ForegroundColor Yellow
        & $python (Join-Path $root "scripts\check_privacy.py") (Join-Path $dist "Ownhost.exe")
        if ($LASTEXITCODE -ne 0) { Write-Host "Check the privacy warning before sharing." -ForegroundColor Red; exit 1 }
        exit 0
    }
}
$linuxOut = "/src/" + ($dist.Substring($root.Length + 1) -replace '\\', '/') + "/linux"
docker run --rm -e OWNHOST_BUILD -v "${root}:/src" almalinux:8 `
    bash /src/scripts/build-linux.sh /src $linuxOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done: $(Join-Path $root ($linuxOut -replace '^/src/', '') )" -ForegroundColor Green

# No data about whoever builds (user, computer, IPs...) may end up inside what gets shared.
$linuxBin = Join-Path $root (($linuxOut -replace '^/src/', '') + "/Ownhost")
& $python (Join-Path $root "scripts\check_privacy.py") (Join-Path $dist "Ownhost.exe") $linuxBin
if ($LASTEXITCODE -ne 0) { Write-Host "Check the privacy warning before sharing." -ForegroundColor Red; exit 1 }
