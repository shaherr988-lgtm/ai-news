# Optional 4th backup layer for the daily digest trigger, run from this
# machine via Windows Task Scheduler (repeated every ~30 min, with a
# "start only if network connection is available" condition) — see the
# project's memory notes for why the primary triggers (GitHub Actions +
# cron-job.org) are already reliable on their own; this is an intentional
# extra layer, not a replacement.
#
# Reads RUN_DAILY_TOKEN from .env (gitignored, never hardcoded here) so this
# script is safe to commit even though it authenticates a real request.
# Calling /internal/run-daily is harmless if today's digest already sent —
# the endpoint's own idempotency guard just no-ops.

$ErrorActionPreference = "Stop"

$envPath = Join-Path $PSScriptRoot "..\.env"
$tokenLine = Get-Content $envPath | Where-Object { $_ -match "^RUN_DAILY_TOKEN=" }
if (-not $tokenLine) {
    Write-Error "RUN_DAILY_TOKEN not found in .env"
    exit 1
}
$token = ($tokenLine -split "=", 2)[1].Trim()

$url = "https://ai-news-web-qon6.onrender.com/internal/run-daily?token=$token"
$response = Invoke-WebRequest -Uri $url -Method Post -UseBasicParsing -TimeoutSec 60
Write-Output "Triggered: $($response.StatusCode) $($response.Content)"
