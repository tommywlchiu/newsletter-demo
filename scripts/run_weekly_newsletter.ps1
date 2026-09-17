# Fires every Monday 8:50am via Windows Task Scheduler (see workflows/weekly_autorun_prompt.md
# for what it actually does). Runs Claude Code unattended and unattended-permission,
# against this repo, with the standing authorization spelled out in that prompt file.
#
# Registered by: Register-ScheduledTask (see conversation history / README for the
# exact registration command if this ever needs to be recreated).

$ErrorActionPreference = "Stop"
# Derived from the script's own location (scripts/<this file> -> repo root) rather
# than hardcoded, so this file doesn't bake in a machine-specific absolute path
# (2026-09-17 finding: the old hardcoded path had leaked a real Windows username
# and machine name into every commit that touched this file, on a public repo).
$repoDir = Split-Path -Parent $PSScriptRoot
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

# claude.exe writes UTF-8 to stdout. Without this, Windows PowerShell 5.1 decodes
# console output using the system codepage, mangling em-dashes/bullets/etc. before
# the pipeline ever sees them. And this build's Tee-Object has no -Encoding param
# at all (it always writes UTF-16LE), which every plain-text log reader then
# mangles further. So this uses Out-File -Encoding utf8 instead of Tee-Object —
# nothing streams to the console either way since no one watches an unattended
# run live. Both fixes needed, or run logs come out unreadable (2026-09-17 finding).
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

& $claudeExe -p $prompt --model claude-sonnet-5 --permission-mode bypassPermissions *>&1 |
    Out-File -FilePath $runLog -Encoding utf8

exit $LASTEXITCODE
