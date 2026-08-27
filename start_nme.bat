@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%nme_backend"
set "FRONTEND_DIR=%ROOT_DIR%nme_frontend"
set "VENV_PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "BACKEND_HEALTH_URL=http://127.0.0.1:8000/health"
set "FRONTEND_ROOT_URL=http://127.0.0.1:5173/"

if not exist "%BACKEND_DIR%\app\main.py" (
    echo [ERROR] Backend folder not found: %BACKEND_DIR%
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Backend virtual environment not found: %VENV_PYTHON%
    echo Please create .venv in nme_backend first.
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERROR] Frontend folder not found: %FRONTEND_DIR%
    exit /b 1
)

call :DetectBackendStatus
if /I "%BACKEND_STATUS%" EQU "BACKEND_CONFLICT" (
    echo [ERROR] Port 8000 is already used by another process that is not the NME backend.
    echo Please stop the conflicting process or choose a different port.
    exit /b 1
)

if /I "%BACKEND_STATUS%" NEQ "BACKEND_RUNNING" (
    echo [INFO] Starting NME Backend on http://127.0.0.1:8000
    start "NME Backend" powershell -NoLogo -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%BACKEND_DIR%'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-proxy-headers"
)

call :WaitForBackendReady

call :DetectFrontendStatus
if /I "%FRONTEND_STATUS%" EQU "FRONTEND_CONFLICT" (
    echo [ERROR] Port 5173 is already used by another process that is not the NME frontend.
    echo Please stop the conflicting process or choose a different port.
    exit /b 1
)

if /I "%FRONTEND_STATUS%" NEQ "FRONTEND_RUNNING" (
    echo [INFO] Starting NME Frontend on http://127.0.0.1:5173
    start "NME Frontend" powershell -NoLogo -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%FRONTEND_DIR%'; $env:VITE_API_URL='http://127.0.0.1:8000'; npm run dev -- --host 127.0.0.1 --port 5173"
)

call :WaitForFrontendReady

echo.
echo NME 시작 완료
echo Backend: http://127.0.0.1:8000
echo Swagger: http://127.0.0.1:8000/docs
echo Frontend: http://127.0.0.1:5173

echo.
echo Standard backend command: .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-proxy-headers
echo Standard frontend command: npm run dev -- --host 127.0.0.1 --port 5173
echo If a port conflict occurs, stop the conflicting process instead of starting a duplicate.
exit /b 0

:DetectBackendStatus
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $url = '%BACKEND_HEALTH_URL%'; try { $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2; if ($resp.StatusCode -eq 200) { 'BACKEND_RUNNING' } else { 'BACKEND_CONFLICT' } } catch { $listen = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if ($listen) { 'BACKEND_CONFLICT' } else { 'BACKEND_NOT_RUNNING' } } }"`) do set "BACKEND_STATUS=%%I"
exit /b 0

:DetectFrontendStatus
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $url = '%FRONTEND_ROOT_URL%'; try { $resp = Invoke-WebRequest -Uri $url -Headers @{Accept='text/html,application/xhtml+xml'} -UseBasicParsing -TimeoutSec 2; if ($resp.StatusCode -eq 200 -and $resp.Content -match 'NME Frontend') { 'FRONTEND_RUNNING' } else { 'FRONTEND_CONFLICT' } } catch { $listen = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue; if ($listen) { 'FRONTEND_CONFLICT' } else { 'FRONTEND_NOT_RUNNING' } } }"`) do set "FRONTEND_STATUS=%%I"
exit /b 0

:WaitForBackendReady
for /L %%I in (1,1,40) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $resp = Invoke-WebRequest -Uri '%BACKEND_HEALTH_URL%' -UseBasicParsing -TimeoutSec 2; if ($resp.StatusCode -eq 200) { exit 0 } } catch {} ; exit 1" >nul 2>&1
    if not errorlevel 1 exit /b 0
    ping -n 2 127.0.0.1 >nul
)

echo [ERROR] Backend did not become ready on port 8000.
exit /b 1

:WaitForFrontendReady
for /L %%I in (1,1,40) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $resp = Invoke-WebRequest -Uri '%FRONTEND_ROOT_URL%' -Headers @{Accept='text/html,application/xhtml+xml'} -UseBasicParsing -TimeoutSec 2; if ($resp.StatusCode -eq 200 -and $resp.Content -match 'NME Frontend') { exit 0 } } catch {} ; exit 1" >nul 2>&1
    if not errorlevel 1 exit /b 0
    ping -n 2 127.0.0.1 >nul
)

echo [ERROR] Frontend did not become ready on port 5173.
exit /b 1
