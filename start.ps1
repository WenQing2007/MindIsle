# ===========================================================================
# MindIsle one-click launcher (Windows PowerShell)
#   - Creates .env from .env.example if missing
#   - Installs Python / Node deps when missing
#   - Starts backend (uvicorn :8000) and frontend (Vite :5173) in background
#   - Opens the student home page when ready
#
# Usage (project root):   .\start.ps1
# If policy blocks it:    Set-ExecutionPolicy -Scope Process Bypass
# ===========================================================================

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
Set-Location $Root

# ---- 1. prepare .env ----
if (-not (Test-Path (Join-Path $Root '.env'))) {
    Copy-Item (Join-Path $Root '.env.example') (Join-Path $Root '.env')
    Write-Host '[start] .env created from .env.example (edit LLM_API_KEY if needed)' -ForegroundColor Yellow
}

# ---- 2. node on PATH? (Vite needs it) ----
$nodeOpts = @()
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    foreach ($p in @("$env:ProgramFiles\nodejs", "$env:LOCALAPPDATA\Programs\nodejs")) {
        if (Test-Path (Join-Path $p 'node.exe')) { $nodeOpts += $p }
    }
    if ($nodeOpts.Count -gt 0) {
        $env:Path = ($nodeOpts -join ';') + ';' + $env:Path
        Write-Host '[start] node found via probed path' -ForegroundColor DarkCyan
    } else {
        Write-Host '[start] Node.js not found; frontend may fail. Install Node 18+' -ForegroundColor Red
    }
}

# ---- 3. backend deps ----
Write-Host '[start] checking backend deps...' -ForegroundColor Cyan
python -c "import fastapi, uvicorn, fpdf" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host '[start] installing python deps...' -ForegroundColor Yellow
    pip install -r (Join-Path $Root 'requirements.txt')
} else {
    Write-Host '[start] backend deps ready' -ForegroundColor Green
}

# ---- 4. frontend deps ----
$frontend = Join-Path $Root 'Mindlsle_fronted\frontend'
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host '[start] installing frontend deps (first run, may be slow)...' -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
} else {
    Write-Host '[start] frontend deps ready' -ForegroundColor Green
}

# ---- 5. start backend (background) ----
Write-Host '[start] starting backend :8000 ...' -ForegroundColor Cyan
$logDir = Join-Path $Root 'output'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$backendLog = Join-Path $logDir 'backend.log'
$frontLog = Join-Path $logDir 'frontend.log'
Start-Process -FilePath 'python' -ArgumentList '-m','uvicorn','backend.app:app','--host','0.0.0.0','--port','8000' `
    -WorkingDirectory $Root -RedirectStandardOutput $backendLog -RedirectStandardError $backendLog -WindowStyle Hidden
Write-Host "[start] backend log: $backendLog" -ForegroundColor DarkGray

# ---- 6. start frontend (background) ----
Write-Host '[start] starting frontend :5173 ...' -ForegroundColor Cyan
Push-Location $frontend
Start-Process -FilePath 'npm' -ArgumentList 'run','dev' `
    -WorkingDirectory $frontend -RedirectStandardOutput $frontLog -RedirectStandardError $frontLog -WindowStyle Hidden
Pop-Location
Write-Host "[start] frontend log: $frontLog" -ForegroundColor DarkGray

# ---- 7. wait for readiness then open browser ----
Write-Host '[start] waiting for services...' -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/health' -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
}
if ($ready) {
    Write-Host '[start] backend ready; opening browser...' -ForegroundColor Green
    Start-Process 'http://localhost:5173/student/home'
    Write-Host '============================================' -ForegroundColor Cyan
    Write-Host '  Student  http://localhost:5173/student/home' -ForegroundColor White
    Write-Host '  Teacher  http://localhost:5173/teacher/login' -ForegroundColor White
    Write-Host '  Admin    http://localhost:5173/admin/login' -ForegroundColor White
    Write-Host '  default passwords: 123456' -ForegroundColor DarkGray
    Write-Host '============================================' -ForegroundColor Cyan
} else {
    Write-Host "[start] backend not ready; check $backendLog" -ForegroundColor Red
}

Write-Host '[start] done' -ForegroundColor Green

