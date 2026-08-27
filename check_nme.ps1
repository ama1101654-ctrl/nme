$ErrorActionPreference = 'SilentlyContinue'

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir 'nme_backend'
$frontendDir = Join-Path $rootDir 'nme_frontend'
$backendPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$backendHealthUrl = 'http://127.0.0.1:8000/health'
$backendMarketUrl = 'http://127.0.0.1:8000/market'
$backendDocsUrl = 'http://127.0.0.1:8000/docs'
$backendOpenApiUrl = 'http://127.0.0.1:8000/openapi.json'
$frontendUrl = 'http://127.0.0.1:5173/'
$expectedApiUrl = 'http://127.0.0.1:8000'
$expectedFrontendOrigin = 'http://127.0.0.1:5173'

$failureCount = 0

function Write-Check {
    param(
        [int]$Index,
        [string]$Name,
        [bool]$Passed,
        [string]$Message,
        [string]$Cause,
        [string]$Expected
    )

    if ($Passed) {
        $status = 'PASS'
    } else {
        $status = 'FAIL'
        $script:failureCount++
    }

    Write-Output ("[{0}] {1}" -f $Index, $Name)
    Write-Output ("{0} - {1}" -f $status, $Message)

    if (-not $Passed -and $Cause) {
        Write-Output 'Possible cause:'
        Write-Output $Cause
    }

    if ($Expected) {
        Write-Output 'Expected:'
        Write-Output $Expected
    }

    Write-Output ''
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
        $response = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 4
        return [pscustomobject]@{
            Ok = $true
            StatusCode = [int]$response.StatusCode
            Body = [string]$response.Content
            Headers = $response.Headers
            Error = ''
        }
    } catch {
        $status = 0
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        return [pscustomobject]@{
            Ok = $false
            StatusCode = $status
            Body = ''
            Headers = @{}
            Error = $_.Exception.Message
        }
    }
}

function Get-PortProcess {
    param([int]$Port)

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) {
        return $null
    }

    $proc = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $conn.OwningProcess)
    if (-not $proc) {
        return [pscustomobject]@{
            LocalAddress = $conn.LocalAddress
            LocalPort = $conn.LocalPort
            ProcessId = $conn.OwningProcess
            Name = 'unknown'
            CommandLine = ''
        }
    }

    return [pscustomobject]@{
        LocalAddress = $conn.LocalAddress
        LocalPort = $conn.LocalPort
        ProcessId = $proc.ProcessId
        Name = $proc.Name
        CommandLine = [string]$proc.CommandLine
    }
}

function Parse-EnvLine {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $line = Get-Content $Path | Where-Object {
        $_ -match '^\s*[^#].*=' -and $_.TrimStart().StartsWith("$Key=")
    } | Select-Object -First 1

    if (-not $line) {
        return $null
    }

    return ($line -split '=', 2)[1].Trim()
}

Write-Output '========================================'
Write-Output ' NME DEVELOPMENT ENVIRONMENT CHECK'
Write-Output '========================================'
Write-Output ''

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $pyVer = (& python --version 2>&1 | Out-String).Trim()
    Write-Check -Index 1 -Name 'Python' -Passed $true -Message $pyVer
} else {
    Write-Check -Index 1 -Name 'Python' -Passed $false -Message 'python command not found on PATH' -Cause 'Python is not installed or PATH is not configured.'
}

if (Test-Path $backendPython) {
    $venvVer = (& $backendPython --version 2>&1 | Out-String).Trim()
    Write-Check -Index 2 -Name 'Virtual Environment' -Passed $true -Message ("{0} found ({1})" -f $backendPython, $venvVer)
} else {
    Write-Check -Index 2 -Name 'Virtual Environment' -Passed $false -Message ("Missing {0}" -f $backendPython) -Cause 'nme_backend .venv is not created.'
}

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
    $nodeVer = (& node --version 2>&1 | Out-String).Trim()
    Write-Check -Index 3 -Name 'Node' -Passed $true -Message $nodeVer
} else {
    Write-Check -Index 3 -Name 'Node' -Passed $false -Message 'node command not found on PATH' -Cause 'Node.js is not installed or PATH is not configured.'
}

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($npmCmd) {
    $npmVer = (& npm --version 2>&1 | Out-String).Trim()
    Write-Check -Index 4 -Name 'npm' -Passed $true -Message $npmVer
} else {
    Write-Check -Index 4 -Name 'npm' -Passed $false -Message 'npm command not found on PATH' -Cause 'npm is not installed or PATH is not configured.'
}

if ((Test-Path $backendDir) -and (Test-Path (Join-Path $backendDir 'app\main.py'))) {
    Write-Check -Index 5 -Name 'Backend Directory' -Passed $true -Message $backendDir
} else {
    Write-Check -Index 5 -Name 'Backend Directory' -Passed $false -Message 'nme_backend folder or app/main.py missing' -Cause 'Project folder structure is incomplete.'
}

if ((Test-Path $frontendDir) -and (Test-Path (Join-Path $frontendDir 'package.json'))) {
    Write-Check -Index 6 -Name 'Frontend Directory' -Passed $true -Message $frontendDir
} else {
    Write-Check -Index 6 -Name 'Frontend Directory' -Passed $false -Message 'nme_frontend folder or package.json missing' -Cause 'Project folder structure is incomplete.'
}

$backendPort = Get-PortProcess -Port 8000
if (-not $backendPort) {
    Write-Check -Index 7 -Name 'Backend Port 8000' -Passed $false -Message 'NOT RUNNING - Port 8000 is free' -Cause 'NME backend is not started.'
} else {
    $health = Invoke-Http -Url $backendHealthUrl
    $cmd = $backendPort.CommandLine
    $looksNme = ($cmd -match 'uvicorn') -and ($cmd -match 'app\.main:app')
    $healthOk = $health.Ok -and $health.StatusCode -eq 200 -and ($health.Body -match '"status"\s*:\s*"ok"')

    if ($healthOk) {
        Write-Check -Index 7 -Name 'Backend Port 8000' -Passed $true -Message ("RUNNING/REUSE - PID {0} ({1})" -f $backendPort.ProcessId, $backendPort.Name)
    } elseif ($looksNme) {
        Write-Check -Index 7 -Name 'Backend Port 8000' -Passed $false -Message ("SERVICE ERROR - PID {0} is backend-like but /health failed" -f $backendPort.ProcessId) -Cause 'Backend process started but application did not become healthy.'
    } else {
        Write-Check -Index 7 -Name 'Backend Port 8000' -Passed $false -Message ("CONFLICT - PID {0} ({1}) is using port 8000" -f $backendPort.ProcessId, $backendPort.Name) -Cause 'Another program is occupying port 8000.'
    }
}

$frontendPort = Get-PortProcess -Port 5173
if (-not $frontendPort) {
    Write-Check -Index 8 -Name 'Frontend Port 5173' -Passed $false -Message 'NOT RUNNING - Port 5173 is free' -Cause 'NME frontend is not started.'
} else {
    $front = Invoke-Http -Url $frontendUrl -Headers @{ Accept = 'text/html,application/xhtml+xml' }
    $cmd = $frontendPort.CommandLine
    $looksVite = ($cmd -match 'vite') -or ($cmd -match 'npm(\.cmd)?\s+run\s+dev')
    $frontOk = $front.Ok -and $front.StatusCode -eq 200 -and ($front.Body -match 'NME Frontend')

    if ($frontOk) {
        Write-Check -Index 8 -Name 'Frontend Port 5173' -Passed $true -Message ("RUNNING/REUSE - PID {0} ({1})" -f $frontendPort.ProcessId, $frontendPort.Name)
    } elseif ($looksVite) {
        Write-Check -Index 8 -Name 'Frontend Port 5173' -Passed $false -Message ("SERVICE ERROR - PID {0} is frontend-like but HTTP check failed" -f $frontendPort.ProcessId) -Cause 'Vite process exists but app is not serving the expected page.'
    } else {
        Write-Check -Index 8 -Name 'Frontend Port 5173' -Passed $false -Message ("CONFLICT - PID {0} ({1}) is using port 5173" -f $frontendPort.ProcessId, $frontendPort.Name) -Cause 'Another program is occupying port 5173.'
    }
}

$healthResp = Invoke-Http -Url $backendHealthUrl
Write-Check -Index 9 -Name 'Backend /health' -Passed ($healthResp.Ok -and $healthResp.StatusCode -eq 200) -Message ("HTTP {0}" -f ($(if ($healthResp.StatusCode) { $healthResp.StatusCode } else { 'ERROR' }))) -Cause 'NME backend is not running or unhealthy.'

$marketResp = Invoke-Http -Url $backendMarketUrl
Write-Check -Index 10 -Name 'Backend /market' -Passed ($marketResp.Ok -and $marketResp.StatusCode -eq 200) -Message ("HTTP {0}" -f ($(if ($marketResp.StatusCode) { $marketResp.StatusCode } else { 'ERROR' }))) -Cause 'NME backend is not reachable or market endpoint failed.'

$docsResp = Invoke-Http -Url $backendDocsUrl
Write-Check -Index 11 -Name 'Backend /docs' -Passed ($docsResp.Ok -and $docsResp.StatusCode -eq 200) -Message ("HTTP {0}" -f ($(if ($docsResp.StatusCode) { $docsResp.StatusCode } else { 'ERROR' }))) -Cause 'Swagger docs endpoint is not reachable.'

$openApiResp = Invoke-Http -Url $backendOpenApiUrl
Write-Check -Index 12 -Name 'Backend /openapi.json' -Passed ($openApiResp.Ok -and $openApiResp.StatusCode -eq 200) -Message ("HTTP {0}" -f ($(if ($openApiResp.StatusCode) { $openApiResp.StatusCode } else { 'ERROR' }))) -Cause 'OpenAPI endpoint is not reachable.'

$frontendResp = Invoke-Http -Url $frontendUrl -Headers @{ Accept = 'text/html,application/xhtml+xml' }
$frontendHttpOk = $frontendResp.Ok -and $frontendResp.StatusCode -eq 200
Write-Check -Index 13 -Name 'Frontend HTTP Response' -Passed $frontendHttpOk -Message ("HTTP {0}" -f ($(if ($frontendResp.StatusCode) { $frontendResp.StatusCode } else { 'ERROR' }))) -Cause 'Frontend dev server is not reachable on 127.0.0.1:5173.'

$appJsPath = Join-Path $frontendDir 'src\App.jsx'
$frontendEnvPath = Join-Path $frontendDir '.env'
$frontendEnvLocalPath = Join-Path $frontendDir '.env.local'
$apiUrlPassed = $false
$apiUrlMessage = ''
$apiUrlCause = ''

$appJsText = if (Test-Path $appJsPath) { Get-Content $appJsPath -Raw } else { '' }
$defaultApiFound = $appJsText -match "const API = import\.meta\.env\.VITE_API_URL \|\| 'http://127\.0\.0\.1:8000'"
$envApi = Parse-EnvLine -Path $frontendEnvPath -Key 'VITE_API_URL'
$envLocalApi = Parse-EnvLine -Path $frontendEnvLocalPath -Key 'VITE_API_URL'
$effectiveApi = if ($envLocalApi) { $envLocalApi } elseif ($envApi) { $envApi } else { $expectedApiUrl }

if ($effectiveApi -eq $expectedApiUrl -and $defaultApiFound) {
    $apiUrlPassed = $true
    $apiUrlMessage = "PASS policy confirmed: effective API URL is $effectiveApi"
} elseif ($effectiveApi -eq $expectedApiUrl) {
    $apiUrlPassed = $true
    $apiUrlMessage = "Effective API URL is $effectiveApi (from env)"
} else {
    $apiUrlPassed = $false
    $apiUrlMessage = "Frontend API URL mismatch: $effectiveApi"
    $apiUrlCause = 'Frontend environment value does not match STEP 52 standard backend URL.'
}

Write-Check -Index 14 -Name 'VITE_API_URL Policy' -Passed $apiUrlPassed -Message $apiUrlMessage -Cause $apiUrlCause -Expected $expectedApiUrl

$backendEnvPath = Join-Path $backendDir '.env'
$devCorsRaw = Parse-EnvLine -Path $backendEnvPath -Key 'DEV_CORS_ALLOW_ORIGINS'
$corsPassed = $false
$corsMessage = ''
$corsCause = ''

if (-not $devCorsRaw) {
    $corsPassed = $false
    $corsMessage = 'DEV_CORS_ALLOW_ORIGINS is missing in nme_backend/.env'
    $corsCause = 'Backend development CORS policy is undefined.'
} else {
    $origins = $devCorsRaw.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $hasExpected = $origins -contains $expectedFrontendOrigin
    $hasWildcard = $origins -contains '*'
    if ($hasExpected -and -not $hasWildcard) {
        $allowedResp = Invoke-Http -Url $backendMarketUrl -Headers @{ Origin = $expectedFrontendOrigin }
        $evilResp = Invoke-Http -Url $backendMarketUrl -Headers @{ Origin = 'http://evil.example.com' }
        $allowedHeader = ''
        $evilHeader = ''
        if ($allowedResp.Headers) {
            $allowedHeader = [string]$allowedResp.Headers['Access-Control-Allow-Origin']
        }
        if ($evilResp.Headers) {
            $evilHeader = [string]$evilResp.Headers['Access-Control-Allow-Origin']
        }

        if (($allowedResp.StatusCode -eq 200) -and ($allowedHeader -eq $expectedFrontendOrigin) -and (-not $evilHeader)) {
            $corsPassed = $true
            $corsMessage = 'Config and runtime CORS checks passed'
        } else {
            $corsPassed = $false
            $corsMessage = 'CORS runtime response mismatch'
            $corsCause = 'Backend may be down or CORS header behavior differs from policy.'
        }
    } else {
        $corsPassed = $false
        $corsMessage = "CORS allowlist issue: hasExpected=$hasExpected, wildcard=$hasWildcard"
        $corsCause = 'Expected frontend origin missing or wildcard is present.'
    }
}

Write-Check -Index 15 -Name 'CORS Policy' -Passed $corsPassed -Message $corsMessage -Cause $corsCause -Expected 'Allow http://127.0.0.1:5173 and deny http://evil.example.com without wildcard(*)'

$dbPath = Join-Path $backendDir 'nme.db'
if (Test-Path $dbPath) {
    Write-Check -Index 16 -Name 'Database File' -Passed $true -Message ("Found {0}" -f $dbPath)
} else {
    Write-Check -Index 16 -Name 'Database File' -Passed $false -Message 'nme_backend/nme.db not found' -Cause 'Real development DB file is missing.'
}

$dbProtectPassed = $false
$dbProtectMessage = ''
$dbProtectCause = ''
$dbCountJson = ''
if ((Test-Path $dbPath) -and (Test-Path $backendPython)) {
    $pyCode = @"
import json, sqlite3
conn = sqlite3.connect(r'$dbPath')
cur = conn.cursor()
tables = ['users','products','deals','orders','auth_sessions']
data = {}
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    data[t] = cur.fetchone()[0]
conn.close()
print(json.dumps(data, ensure_ascii=True))
"@
    $dbCountJson = (& $backendPython -c $pyCode 2>$null | Out-String).Trim()
    if ($dbCountJson) {
        $dbProtectPassed = $true
        $dbProtectMessage = "Read-only count check OK: $dbCountJson"
    } else {
        $dbProtectPassed = $false
        $dbProtectMessage = 'Could not read table counts from nme.db'
        $dbProtectCause = 'venv python/sqlite execution failed.'
    }
} else {
    $dbProtectPassed = $false
    $dbProtectMessage = 'Skipped read-only DB count check'
    $dbProtectCause = 'nme.db or backend venv python is missing.'
}

Write-Check -Index 17 -Name 'Database Protection/Read-only Check' -Passed $dbProtectPassed -Message $dbProtectMessage -Cause $dbProtectCause

$pytestIniPath = Join-Path $backendDir 'pytest.ini'
if (Test-Path $pytestIniPath) {
    $pytestText = Get-Content $pytestIniPath -Raw
    $hasTestPaths = $pytestText -match 'testpaths\s*=\s*tests'
    if ($hasTestPaths) {
        Write-Check -Index 18 -Name 'pytest Configuration' -Passed $true -Message 'pytest.ini testpaths=tests confirmed'
    } else {
        Write-Check -Index 18 -Name 'pytest Configuration' -Passed $false -Message 'pytest.ini exists but testpaths=tests not found' -Cause 'Test discovery baseline may be broken.'
    }
} else {
    Write-Check -Index 18 -Name 'pytest Configuration' -Passed $false -Message 'nme_backend/pytest.ini missing' -Cause 'Pytest baseline config is missing.'
}

$browserFiles = @(
    (Join-Path $backendDir 'tests\browser\conftest.py'),
    (Join-Path $backendDir 'tests\browser\test_browser_smoke.py'),
    (Join-Path $backendDir 'tests\browser\test_browser_trade_flow.py')
)
$missingBrowser = $browserFiles | Where-Object { -not (Test-Path $_) }
if ($missingBrowser.Count -eq 0) {
    Write-Check -Index 19 -Name 'Browser Test Files' -Passed $true -Message 'Browser smoke/trade-flow files are present'
} else {
    Write-Check -Index 19 -Name 'Browser Test Files' -Passed $false -Message ("Missing files: {0}" -f ($missingBrowser -join ', ')) -Cause 'Browser regression baseline is incomplete.'
}

if ($failureCount -eq 0) {
    Write-Check -Index 20 -Name 'Final Environment Status' -Passed $true -Message 'READY'
    Write-Output '========================================'
    Write-Output ' RESULT: READY'
    Write-Output '========================================'
    exit 0
}

Write-Check -Index 20 -Name 'Final Environment Status' -Passed $false -Message ("NOT READY - {0} check(s) failed" -f $failureCount) -Cause 'Review failed sections above and resolve startup/environment issues first.'
Write-Output '========================================'
Write-Output ' RESULT: NOT READY'
Write-Output '========================================'
exit 1
