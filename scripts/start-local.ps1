param(
    [ValidateRange(1024, 65535)][int]$ApiPort = 8000,
    [ValidateRange(1024, 65535)][int]$WebPort = 5173,
    [string]$PythonExecutable
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = if ($PythonExecutable) { (Resolve-Path -LiteralPath $PythonExecutable).Path } else { Join-Path $backend '.venv/Scripts/python.exe' }
$vite = Join-Path $frontend 'node_modules/vite/bin/vite.js'
$node = Get-Command node.exe -ErrorAction SilentlyContinue
$stateRoot = Join-Path $env:TEMP 'jujosmi-trade-ui2-full-app'
$statePath = Join-Path $stateRoot 'processes.json'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Backend venv missing. Follow the root README dependency setup first.' }
if (-not (Test-Path -LiteralPath $vite -PathType Leaf)) { throw 'Frontend dependencies missing. Run npm ci in frontend first.' }
if (-not $node) { throw 'Node.js was not found. Install Node.js 20.19 or newer.' }

foreach ($port in @($ApiPort, $WebPort)) {
    $listener = $null
    try { $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port); $listener.Start(); $listener.Stop() }
    catch { if ($listener) { $listener.Stop() }; throw "Loopback port $port is already in use." }
}
if (Test-Path -LiteralPath $statePath) {
    $old = @(Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json)
    if (@($old | Where-Object { Get-Process -Id $_.pid -ErrorAction SilentlyContinue }).Count) { throw 'A recorded local demo process is active. Run scripts/stop-local.ps1 first.' }
    Remove-Item -LiteralPath $statePath -Force
}

New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null
$apiOut = Join-Path $stateRoot 'api.stdout.log'; $apiErr = Join-Path $stateRoot 'api.stderr.log'
$webOut = Join-Path $stateRoot 'web.stdout.log'; $webErr = Join-Path $stateRoot 'web.stderr.log'
$entries = @()
$previousOrigins = $env:TRADE_UI_ALLOWED_ORIGINS
$previousBase = $env:VITE_TRADE_API_BASE_URL
try {
    $env:TRADE_UI_ALLOWED_ORIGINS = "http://127.0.0.1:$WebPort,http://localhost:$WebPort"
    $apiProcess = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',[string]$ApiPort) -WorkingDirectory $backend -WindowStyle Hidden -PassThru -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr
    $entries += [pscustomobject]@{pid=$apiProcess.Id;path=$python;startTicks=$apiProcess.StartTime.ToUniversalTime().Ticks}
    $entries | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
    $env:VITE_TRADE_API_BASE_URL = "http://127.0.0.1:$ApiPort/api/v1"
    $viteProcess = Start-Process -FilePath $node.Source -ArgumentList @('"' + $vite + '"','--configLoader','runner','--host','127.0.0.1','--port',[string]$WebPort,'--strictPort') -WorkingDirectory $frontend -WindowStyle Hidden -PassThru -RedirectStandardOutput $webOut -RedirectStandardError $webErr
    $entries += [pscustomobject]@{pid=$viteProcess.Id;path=$node.Source;startTicks=$viteProcess.StartTime.ToUniversalTime().Ticks}
    $entries | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
} catch {
    & (Join-Path $PSScriptRoot 'stop-local.ps1')
    throw
} finally {
    if ($null -eq $previousOrigins) { Remove-Item Env:TRADE_UI_ALLOWED_ORIGINS -ErrorAction SilentlyContinue } else { $env:TRADE_UI_ALLOWED_ORIGINS = $previousOrigins }
    if ($null -eq $previousBase) { Remove-Item Env:VITE_TRADE_API_BASE_URL -ErrorAction SilentlyContinue } else { $env:VITE_TRADE_API_BASE_URL = $previousBase }
}

$ready = $false
for ($attempt=0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/health" -TimeoutSec 1
        $page = Invoke-WebRequest -Uri "http://127.0.0.1:$WebPort/" -TimeoutSec 1 -UseBasicParsing
        if ($health.status -eq 'ok' -and $page.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $ready) {
    & (Join-Path $PSScriptRoot 'stop-local.ps1')
    throw "Local services did not become ready. Review logs under $stateRoot."
}
Write-Output "Jujosmi Trade is ready at http://127.0.0.1:$WebPort/"
Write-Output "FastAPI health endpoint: http://127.0.0.1:$ApiPort/health"
Write-Output 'All demo market data is synthetic; SEC access remains configuration-dependent.'
