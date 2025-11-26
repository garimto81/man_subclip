# check_ffmpeg.ps1
# ffmpeg 설치 상태 확인 및 PATH 문제 해결 스크립트

Write-Host "=== ffmpeg 설치 상태 확인 ===" -ForegroundColor Cyan

# 1. ffmpeg 명령어 확인
$ffmpegPath = Get-Command ffmpeg -ErrorAction SilentlyContinue

if ($ffmpegPath) {
    Write-Host "[OK] ffmpeg 발견: $($ffmpegPath.Source)" -ForegroundColor Green

    # 버전 정보 출력
    $version = & ffmpeg -version 2>&1 | Select-Object -First 1
    Write-Host "[OK] 버전: $version" -ForegroundColor Green
} else {
    Write-Host "[ERROR] ffmpeg를 찾을 수 없습니다!" -ForegroundColor Red
    Write-Host ""
    Write-Host "해결 방법:" -ForegroundColor Yellow
    Write-Host "1. winget으로 설치: winget install Gyan.FFmpeg" -ForegroundColor White
    Write-Host "2. 또는 Chocolatey로 설치: choco install ffmpeg" -ForegroundColor White
    Write-Host "3. 설치 후 새 PowerShell 창을 열어주세요 (PATH 업데이트 필요)" -ForegroundColor White
    Write-Host ""

    # PATH 환경 변수 출력
    Write-Host "현재 PATH에서 ffmpeg 관련 경로:" -ForegroundColor Yellow
    $env:PATH -split ';' | Where-Object { $_ -match 'ffmpeg' } | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor Gray
    }

    exit 1
}

# 2. ffprobe 확인
$ffprobePath = Get-Command ffprobe -ErrorAction SilentlyContinue

if ($ffprobePath) {
    Write-Host "[OK] ffprobe 발견: $($ffprobePath.Source)" -ForegroundColor Green
} else {
    Write-Host "[WARNING] ffprobe를 찾을 수 없습니다. 일부 메타데이터 기능이 제한될 수 있습니다." -ForegroundColor Yellow
}

# 3. 간단한 테스트
Write-Host ""
Write-Host "=== 기능 테스트 ===" -ForegroundColor Cyan

try {
    $testOutput = & ffmpeg -encoders 2>&1 | Select-String "libx264"
    if ($testOutput) {
        Write-Host "[OK] H.264 인코더 (libx264) 사용 가능" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] H.264 인코더를 찾을 수 없습니다" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] 테스트 실패: $_" -ForegroundColor Red
}

try {
    $hlsOutput = & ffmpeg -muxers 2>&1 | Select-String "hls"
    if ($hlsOutput) {
        Write-Host "[OK] HLS 먹서 사용 가능" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] HLS 먹서를 찾을 수 없습니다" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] HLS 테스트 실패: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 검사 완료 ===" -ForegroundColor Cyan
Write-Host "ffmpeg가 정상적으로 설치되어 있습니다." -ForegroundColor Green
