# ffmpeg 설치 가이드 (Windows)

## 방법 1: Scoop (추천)

```powershell
# Scoop 설치 (PowerShell 관리자 권한)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# ffmpeg 설치
scoop install ffmpeg

# 확인
ffmpeg -version
```

## 방법 2: Chocolatey

```powershell
# Chocolatey 설치 (PowerShell 관리자 권한)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# ffmpeg 설치
choco install ffmpeg

# 확인
ffmpeg -version
```

## 방법 3: 수동 설치

1. https://www.gyan.dev/ffmpeg/builds/ 접속
2. "ffmpeg-release-essentials.zip" 다운로드
3. 압축 해제 → `C:\ffmpeg`로 이동
4. 환경 변수 PATH에 `C:\ffmpeg\bin` 추가
5. 새 터미널에서 `ffmpeg -version` 확인

## 설치 후 확인

```bash
# ffmpeg 버전 확인
ffmpeg -version

# 경로 확인 (Windows)
where ffmpeg

# Import 테스트
curl -X POST "http://localhost:8001/api/gcs/import?gcs_path=Archive-MAM_Sample.mp4"
```

## 주의사항

- **설치 후 터미널 재시작 필수** (PATH 반영)
- Backend 서버도 재시작 필요
