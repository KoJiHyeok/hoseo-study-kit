# 매일 마감·제출 상태 점검 (Windows) — 설치: auto\install-daily-windows.ps1  (매일 07:40)
# 수동 실행: pwsh -File auto\daily-check.ps1
$Root = Split-Path -Parent $PSScriptRoot
$Log = Join-Path $Root "auto\last-run.log"
Set-Location $Root
function Stamp { Get-Date -Format "yyyy-MM-dd HH:mm" }

# Aside 가 떠 있어야 LMS 에 접근할 수 있다 (사용자 로그인 보유)
if (-not (Get-Process -Name Aside -ErrorAction SilentlyContinue)) {
    $exe = "$env:ProgramFiles\Aside\Application\Aside.exe"
    if (Test-Path $exe) { Start-Process $exe; Start-Sleep -Seconds 40 }
}
if (-not (Get-Process -Name Aside -ErrorAction SilentlyContinue)) {
    Add-Content $Log "$(Stamp) 실패: Aside 가 실행되지 않음 (LMS 접근 불가)" -Encoding utf8
    python auto\notify.py "⚠️ 자동점검 실패: Aside 미실행. 수동 확인 필요" | Out-Null
    exit 1
}

$prompt = Get-Content (Join-Path $Root "auto\PROMPT.md") -Raw -Encoding utf8
claude -p $prompt --permission-mode bypassPermissions *>> (Join-Path $Root "auto\last-run.out")
if ($LASTEXITCODE -ne 0) { Add-Content $Log "$(Stamp) 실패: claude 종료코드 $LASTEXITCODE" -Encoding utf8 }
exit $LASTEXITCODE
