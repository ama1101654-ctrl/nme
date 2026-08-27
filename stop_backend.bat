@echo off
setlocal EnableExtensions

powershell -NoProfile -ExecutionPolicy Bypass -Command "$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; if (-not $connections) { Write-Host 'Backend already stopped on port 8000.'; exit 0 }; $procId = ($connections | Select-Object -First 1 -ExpandProperty OwningProcess); if (-not $procId) { Write-Host 'Backend already stopped on port 8000.'; exit 0 }; Stop-Process -Id $procId -ErrorAction Stop; Write-Host \"Stopped backend process ID: $procId\""