# AI Orchestrator - One-command setup: install, configure (if needed), run
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
Write-Host "AI Orchestrator - Installing..."
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -q
Write-Host "Starting..."
python main.py
