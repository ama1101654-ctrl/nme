$ErrorActionPreference = 'Continue'

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir 'nme_backend'
$frontendDir = Join-Path $rootDir 'nme_frontend'
$backendPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$dbPath = Join-Path $backendDir 'nme.db'

$backendBase = 'http://127.0.0.1:8000'
$frontendBase = 'http://127.0.0.1:5173'
$healthUrl = "$backendBase/health"
$marketUrl = "$backendBase/market"
$docsUrl = "$backendBase/docs"
$openApiUrl = "$backendBase/openapi.json"

function Write-Banner {
    Write-Output '========================================'
    Write-Output ' NME QUALITY GATE / PRE-FLIGHT VERIFY'
    Write-Output '========================================'
    Write-Output ''
}

function Write-FailDetail {
    param(
        [string]$Item,
        [string]$Cause,
        [string]$Related,
        [string]$Action
    )

    Write-Output '[FAIL]'
    Write-Output ("Item: {0}" -f $Item)
    Write-Output ("Cause: {0}" -f $Cause)
    Write-Output ("Related file: {0}" -f $Related)
    Write-Output ("Recommended action: {0}" -f $Action)
    Write-Output ''
}

function Stop-WithFail {
    param(
        [string]$Item,
        [string]$Cause,
        [string]$Related,
        [string]$Action
    )

    Write-FailDetail -Item $Item -Cause $Cause -Related $Related -Action $Action
    Write-Output 'NME QUALITY GATE: FAIL'
    exit 1
}

function Invoke-Http {
    param(
        [string]$Url,
        [hashtable]$Headers
    )

    if (-not $Headers) {
        $Headers = @{}
    }

    try {
        $resp = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 5
        return [pscustomobject]@{ Ok = $true; StatusCode = [int]$resp.StatusCode; Body = [string]$resp.Content; Headers = $resp.Headers; Error = '' }
    } catch {
        $status = 0
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        return [pscustomobject]@{ Ok = $false; StatusCode = $status; Body = ''; Headers = @{}; Error = $_.Exception.Message }
    }
}

function Get-DbCounts {
    param(
        [string]$PythonPath,
        [string]$DbFile
    )

    if (-not (Test-Path $PythonPath)) {
        return $null
    }
    if (-not (Test-Path $DbFile)) {
        return $null
    }

    $pyCode = @"
import json, sqlite3
conn = sqlite3.connect(r'''$DbFile''')
cur = conn.cursor()
result = {}
for t in ['users','products','deals','orders','auth_sessions']:
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    result[t] = cur.fetchone()[0]
conn.close()
print(json.dumps(result, ensure_ascii=True))
"@
    $json = (& $PythonPath -c $pyCode 2>$null | Out-String).Trim()
    if (-not $json) {
        return $null
    }

    try {
        return $json | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Parse-PytestSummary {
    param([string[]]$Lines)

    $text = ($Lines -join "`n")
    $summary = [ordered]@{ passed = 0; failed = 0; skipped = 0; warnings = 0 }

    $passedMatches = [regex]::Matches($text, '(\d+)\s+passed')
    if ($passedMatches.Count -gt 0) {
        $summary.passed = [int]$passedMatches[$passedMatches.Count - 1].Groups[1].Value
    }

    $failedMatches = [regex]::Matches($text, '(\d+)\s+failed')
    if ($failedMatches.Count -gt 0) {
        $summary.failed = [int]$failedMatches[$failedMatches.Count - 1].Groups[1].Value
    }

    $skippedMatches = [regex]::Matches($text, '(\d+)\s+skipped')
    if ($skippedMatches.Count -gt 0) {
        $summary.skipped = [int]$skippedMatches[$skippedMatches.Count - 1].Groups[1].Value
    }

    $warningMatches = [regex]::Matches($text, '(\d+)\s+warnings?')
    if ($warningMatches.Count -gt 0) {
        $summary.warnings = [int]$warningMatches[$warningMatches.Count - 1].Groups[1].Value
    }

    return [pscustomobject]$summary
}

function Require-Http200 {
    param(
        [string]$Item,
        [string]$Url,
        [string]$Related
    )

    $resp = Invoke-Http -Url $Url
    if (-not ($resp.Ok -and $resp.StatusCode -eq 200)) {
        $statusText = if ($resp.StatusCode) { [string]$resp.StatusCode } else { 'ERROR' }
        Stop-WithFail -Item $Item -Cause ("HTTP check failed: {0} -> {1} {2}" -f $Url, $statusText, $resp.Error) -Related $Related -Action 'Run start_nme.bat and check_nme.bat first.'
    }
    Write-Output ("PASS - {0}: HTTP 200" -f $Item)
}

function Run-Bat {
    param([string]$ScriptName)

    $scriptPath = Join-Path $rootDir $ScriptName
    $quoted = '"' + $scriptPath + '"'
    & cmd.exe /c $quoted | Out-Host
    $code = $LASTEXITCODE
    return [int]$code
}

Write-Banner

Write-Output '[STEP 1] Environment CHECK (check_nme.bat)'
$checkExit = Run-Bat -ScriptName 'check_nme.bat'
if ($checkExit -ne 0) {
    Write-Output 'INFO - check_nme.bat failed. Running start_nme.bat once for reuse/start policy.'
    $startExit = Run-Bat -ScriptName 'start_nme.bat'
    if ($startExit -ne 0) {
        Stop-WithFail -Item 'START' -Cause 'start_nme.bat failed' -Related 'start_nme.bat' -Action 'Resolve port conflict or runtime dependency issue, then retry.'
    }

    Write-Output 'INFO - Re-running check_nme.bat'
    $checkExit2 = Run-Bat -ScriptName 'check_nme.bat'
    if ($checkExit2 -ne 0) {
        Stop-WithFail -Item 'Environment CHECK' -Cause 'check_nme.bat is still NOT READY after startup attempt' -Related 'check_nme.bat, check_nme.ps1' -Action 'Fix failed check items first, then run verify_nme.bat again.'
    }
}
Write-Output 'PASS - Environment CHECK'
Write-Output ''

Write-Output '[STEP 2] Backend/Frontend + API checks'
Require-Http200 -Item '/health' -Url $healthUrl -Related 'nme_backend/app/main.py'
Require-Http200 -Item '/market' -Url $marketUrl -Related 'nme_backend/app/main.py'
Require-Http200 -Item '/docs' -Url $docsUrl -Related 'nme_backend/app/main.py'
Require-Http200 -Item '/openapi.json' -Url $openApiUrl -Related 'nme_backend/app/main.py'
$frontResp = Invoke-Http -Url "$frontendBase/" -Headers @{ Accept = 'text/html,application/xhtml+xml' }
if (-not ($frontResp.Ok -and $frontResp.StatusCode -eq 200)) {
    $frontStatus = if ($frontResp.StatusCode) { [string]$frontResp.StatusCode } else { 'ERROR' }
    Stop-WithFail -Item 'Frontend' -Cause ("HTTP check failed: {0}/ -> {1} {2}" -f $frontendBase, $frontStatus, $frontResp.Error) -Related 'nme_frontend' -Action 'Run start_nme.bat and check_nme.bat first.'
}
Write-Output 'PASS - Frontend: HTTP 200'
Write-Output ''

Write-Output '[STEP 3] CORS checks'
$allowed = Invoke-Http -Url $marketUrl -Headers @{ Origin = $frontendBase }
$denied = Invoke-Http -Url $marketUrl -Headers @{ Origin = 'http://evil.example.com' }
$allowedHeader = ''
$deniedHeader = ''
if ($allowed.Headers) { $allowedHeader = [string]$allowed.Headers['Access-Control-Allow-Origin'] }
if ($denied.Headers) { $deniedHeader = [string]$denied.Headers['Access-Control-Allow-Origin'] }

if (($allowed.StatusCode -ne 200) -or ($allowedHeader -ne $frontendBase)) {
    Stop-WithFail -Item 'CORS Allowed Origin' -Cause ("allowed origin check failed: status={0}, header={1}" -f $allowed.StatusCode, $allowedHeader) -Related 'nme_backend/.env, nme_backend/app/main.py' -Action 'Ensure DEV_CORS_ALLOW_ORIGINS includes http://127.0.0.1:5173.'
}
if ($deniedHeader) {
    Stop-WithFail -Item 'CORS Denied Origin' -Cause ("evil origin was allowed: header={0}" -f $deniedHeader) -Related 'nme_backend/.env, nme_backend/app/main.py' -Action 'Remove wildcard(*) or external origins from CORS configuration.'
}
Write-Output 'PASS - CORS checks'
Write-Output ''

Write-Output '[STEP 4] DB pre-count (read-only)'
$dbBefore = Get-DbCounts -PythonPath $backendPython -DbFile $dbPath
if (-not $dbBefore) {
    Stop-WithFail -Item 'DB Pre-count' -Cause 'Could not read nme.db counts before verification' -Related 'nme_backend/nme.db' -Action 'Check backend venv python and nme.db path.'
}
Write-Output ("PASS - DB Before: users={0}, products={1}, deals={2}, orders={3}, auth_sessions={4}" -f $dbBefore.users, $dbBefore.products, $dbBefore.deals, $dbBefore.orders, $dbBefore.auth_sessions)
Write-Output ''

Write-Output '[STEP 5] Full pytest'
Push-Location $backendDir
try {
    $pytestOut = & $backendPython -m pytest -q 2>&1
    $pytestExit = $LASTEXITCODE
} finally {
    Pop-Location
}
$pytestOut | ForEach-Object { Write-Output $_ }
$pytestSummary = Parse-PytestSummary -Lines $pytestOut
Write-Output ("pytest summary: passed={0}, failed={1}, skipped={2}, warnings={3}" -f $pytestSummary.passed, $pytestSummary.failed, $pytestSummary.skipped, $pytestSummary.warnings)
if ($pytestExit -ne 0 -or $pytestSummary.failed -gt 0) {
    Stop-WithFail -Item 'pytest -q' -Cause ("pytest failed: exit={0}, failed={1}" -f $pytestExit, $pytestSummary.failed) -Related 'nme_backend/tests' -Action 'Fix failing tests and rerun verify_nme.bat.'
}
Write-Output 'PASS - full pytest'
Write-Output ''

Write-Output '[STEP 6] Browser pytest'
Push-Location $backendDir
try {
    $browserOut = & $backendPython -m pytest -q tests/browser -m browser 2>&1
    $browserExit = $LASTEXITCODE
} finally {
    Pop-Location
}
$browserOut | ForEach-Object { Write-Output $_ }
$browserSummary = Parse-PytestSummary -Lines $browserOut
Write-Output ("browser summary: passed={0}, failed={1}, skipped={2}, warnings={3}" -f $browserSummary.passed, $browserSummary.failed, $browserSummary.skipped, $browserSummary.warnings)
if ($browserExit -ne 0 -or $browserSummary.failed -gt 0) {
    Stop-WithFail -Item 'browser pytest' -Cause ("browser tests failed: exit={0}, failed={1}" -f $browserExit, $browserSummary.failed) -Related 'nme_backend/tests/browser' -Action 'Fix browser regressions and rerun verify_nme.bat.'
}
Write-Output 'PASS - browser pytest'
Write-Output ''

Write-Output '[STEP 7] Frontend build'
Push-Location $frontendDir
try {
    $buildOut = cmd /c "npm run build" 2>&1
    $buildExit = $LASTEXITCODE
} finally {
    Pop-Location
}
$buildOut | ForEach-Object { Write-Output $_ }
if ($buildExit -ne 0) {
    Stop-WithFail -Item 'npm run build' -Cause ("frontend build failed: exit={0}" -f $buildExit) -Related 'nme_frontend/package.json' -Action 'Fix build errors and rerun verify_nme.bat.'
}
Write-Output 'PASS - frontend build'
Write-Output ''

Write-Output '[STEP 8] DB post-count (read-only)'
$dbAfter = Get-DbCounts -PythonPath $backendPython -DbFile $dbPath
if (-not $dbAfter) {
    Stop-WithFail -Item 'DB Post-count' -Cause 'Could not read nme.db counts after verification' -Related 'nme_backend/nme.db' -Action 'Check nme.db path and access rights.'
}
Write-Output ("PASS - DB After: users={0}, products={1}, deals={2}, orders={3}, auth_sessions={4}" -f $dbAfter.users, $dbAfter.products, $dbAfter.deals, $dbAfter.orders, $dbAfter.auth_sessions)

if (($dbBefore.users -ne $dbAfter.users) -or ($dbBefore.products -ne $dbAfter.products) -or ($dbBefore.deals -ne $dbAfter.deals) -or ($dbBefore.orders -ne $dbAfter.orders)) {
    Stop-WithFail -Item 'DB Protection' -Cause 'Core table counts changed(users/products/deals/orders)' -Related 'nme_backend/nme.db' -Action 'Stop using real DB for test mutation and verify test isolation.'
}

Write-Output ''
Write-Output 'PASS - DB protection confirmed (users/products/deals/orders unchanged)'
Write-Output ''
Write-Output 'NME QUALITY GATE: PASS'
exit 0
