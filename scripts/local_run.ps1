# Local run helper — Andrei AI Agent System (Windows)
# Usage: .\scripts\local_run.ps1 telegram|daily|crew|dashboard

param(
    [Parameter(Position = 0)]
    [ValidateSet("telegram", "daily", "crew", "dashboard", "api")]
    [string]$Command = "telegram"
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Python = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "venv missing. Run first:" -ForegroundColor Yellow
    Write-Host "  py -3.12 -m venv venv"
    Write-Host "  .\venv\Scripts\pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
    Write-Host ".env created from .env.example — edit it with your API keys!" -ForegroundColor Yellow
}

switch ($Command) {
    "telegram" { & $Python (Join-Path $Root "scripts\test_telegram.py") }
    "daily"    { & $Python (Join-Path $Root "run_daily.py") }
    "crew"     { & $Python (Join-Path $Root "run_crew.py") "ce prioritati am azi?" }
    "dashboard" { & $Python -m streamlit run (Join-Path $Root "src\dashboard\app.py") }
    "api"      { & $Python -m src.api.server }
}