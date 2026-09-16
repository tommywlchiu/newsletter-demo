# Fires every Monday 8:50am via Windows Task Scheduler (see workflows/weekly_autorun_prompt.md
# for what it actually does). Runs Claude Code unattended and unattended-permission,
# against this repo, with the standing authorization spelled out in that prompt file.
#
# Registered by: Register-ScheduledTask (see conversation history / README for the
# exact registration command if this ever needs to be recreated).

$ErrorActionPreference = "Stop"
$repoDir = "REDACTED_LOCAL_PATH"
$logDir = Join-Path $repoDir "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$runLog = Join-Path $logDir "run_$stamp.log"

# The extension's version number changes on auto-update, so find the current one
# rather than hardcoding a path that will silently go stale.
$claudeExe = Get-ChildItem "$env:USERPROFILE\.vscode\extensions" -Filter "anthropic.claude-code-*" -Directory |
    Sort-Object Name -Descending |
    Select-Object -First 1 |
    ForEach-Object { Join-Path $_.FullName "resources\native-binary\claude.exe" }

if (-not $claudeExe -or -not (Test-Path $claudeExe)) {
    Add-Content -Path (Join-Path $logDir "weekly-runs.log") -Value "$(Get-Date -AsUTC -Format o) FAILED claude.exe not found under .vscode\extensions"
    exit 1
}

$promptPath = Join-Path $repoDir "workflows\weekly_autorun_prompt.md"
$prompt = Get-Content -Raw -Path $promptPath

Set-Location $repoDir

& $claudeExe -p $prompt --model claude-sonnet-5 --permission-mode bypassPermissions *>&1 |
    Tee-Object -FilePath $runLog

exit $LASTEXITCODE
