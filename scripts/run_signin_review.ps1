$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$log = Join-Path $repo "logs\task_run.log"
"=== $(Get-Date -Format o) start ===" | Out-File -Append -Encoding utf8 $log
& "$repo\venv\Scripts\python.exe" "$repo\scripts\pull_signin_logs.py" --hours 24 2>&1 | Out-File -Append -Encoding utf8 $log
"exit code: $LASTEXITCODE" | Out-File -Append -Encoding utf8 $log