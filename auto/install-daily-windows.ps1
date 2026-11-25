# 매일 07:40 자동 점검을 작업 스케줄러에 등록 (Windows). 노트북이 켜져 있고 로그인돼 있을 때만 돈다.
# 끄기: Unregister-ScheduledTask -TaskName StudyKitDaily -Confirm:$false
# 즉시 실행: Start-ScheduledTask -TaskName StudyKitDaily
$Root = Split-Path -Parent $PSScriptRoot
$shell = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $shell) { $shell = (Get-Command powershell).Source }
$action = New-ScheduledTaskAction -Execute $shell `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Root\auto\daily-check.ps1`"" `
    -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Daily -At 7:40am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName StudyKitDaily -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Output "OK: 매일 07:40 자동 점검 등록 (작업 이름 StudyKitDaily). 놓친 실행은 켜질 때 따라 돈다."
