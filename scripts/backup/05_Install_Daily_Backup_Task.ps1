[CmdletBinding()]
param(
    [string]$ScriptsFolder = $PSScriptRoot,
    [string]$TaskName = "FreightCalc Daily Backup",
    [string]$DailyTime = "19:00",
    [string]$ProjectRoot = "C:\Docker-Projects\Freight-Calc-v1.5",
    [string]$BackupRoot = "C:\Docker-Backups\Freight-Calc",
    [string]$SecondaryCopyPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$backupScript = Join-Path $ScriptsFolder "01_Full_Backup.ps1"
if (-not (Test-Path $backupScript)) {
    throw "Backup script not found: $backupScript"
}

if ($DailyTime -notmatch '^(?:[01]\d|2[0-3]):[0-5]\d$') {
    throw "DailyTime must use HH:mm format, for example 19:00."
}

$timeParts = $DailyTime.Split(":")
$hour = [int]$timeParts[0]
$minute = [int]$timeParts[1]
$triggerTime = (Get-Date).Date.AddHours($hour).AddMinutes($minute)

$psArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$backupScript`"",
    "-ProjectRoot", "`"$ProjectRoot`"",
    "-BackupRoot", "`"$BackupRoot`""
)

if (-not [string]::IsNullOrWhiteSpace($SecondaryCopyPath)) {
    $psArgs += @("-SecondaryCopyPath", "`"$SecondaryCopyPath`"")
}

$argumentString = $psArgs -join " "

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $argumentString

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $triggerTime

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Highest

Write-Host "============================================================"
Write-Host " INSTALL DAILY FREIGHT CALCULATOR BACKUP TASK"
Write-Host "============================================================"
Write-Host "Task name : $TaskName"
Write-Host "User      : $currentUser"
Write-Host "Time      : $DailyTime"
Write-Host "Script    : $backupScript"
Write-Host ""
Write-Host "IMPORTANT:"
Write-Host "- This task does NOT push to GitHub."
Write-Host "- Docker Desktop / Docker services must be available when it runs."
Write-Host "- This configuration uses the current interactive Windows user."

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Daily Freight Calculator recovery-point backup. No GitHub push." `
    -Force | Out-Null

Write-Host "`n=== TASK INSTALLED ==="
Get-ScheduledTask -TaskName $TaskName |
    Select-Object TaskName, State, Description

Write-Host "`n=== NEXT RUN INFORMATION ==="
Get-ScheduledTaskInfo -TaskName $TaskName |
    Select-Object LastRunTime, LastTaskResult, NextRunTime

Write-Host "`nGitHub was NOT modified."
