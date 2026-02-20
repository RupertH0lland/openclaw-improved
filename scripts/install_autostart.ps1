# Install AI Orchestrator to start with Windows
# Run as Administrator or current user
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Python = (Get-Command python).Source
$TaskName = "ai-orchestrator"
$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Root\main.py`" run" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
Write-Host "Installed. Orchestrator will start with Windows."
