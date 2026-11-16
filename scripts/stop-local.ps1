$ErrorActionPreference = 'Continue'
$statePath = Join-Path $env:TEMP 'jujosmi-trade-ui2-full-app/processes.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Output 'No recorded Jujosmi Trade local process state was found.'; exit 0 }
$entries = @(Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json)
$stopped = 0
foreach ($entry in $entries) {
    $process = Get-Process -Id ([int]$entry.pid) -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    $samePath = $false; $sameStart = $false
    try { $samePath = [string]::Equals($process.Path,[string]$entry.path,[StringComparison]::OrdinalIgnoreCase) } catch { }
    try { $sameStart = $process.StartTime.ToUniversalTime().Ticks -eq [long]$entry.startTicks } catch { }
    if ($samePath -and $sameStart) { Stop-Process -Id $process.Id -Force; $stopped++ }
    else { Write-Warning "PID $($entry.pid) does not match the recorded executable and start time; leaving it running." }
}
Remove-Item -LiteralPath $statePath -Force
Write-Output "Stopped $stopped matching demo process(es). Logs remain under $env:TEMP\jujosmi-trade-ui2-full-app."
