# Docker 빠른 시작 가이드

## 1단계: Docker Desktop 시작

Windows에서 Docker Desktop을 실행하세요.
- 작업 표시줄에 Docker 아이콘이 나타날 때까지 기다리기
- 또는: `docker ps` 명령이 정상 작동할 때까지 기다리기

## 2단계: docker-compose 파일 수정

`docker-compose.yml` 첫 줄의 `version:` 제거 (이미 완료됨)

## 3단계: 서비스 실행

```bash
cd D:\AI\claude01\man_subclip

# 빌드 및 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 서비스 상태 확인
docker-compose ps
```

## 4단계: 접속

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432

## 5단계: 테스트

### API 테스트
브라우저에서 http://localhost:8000/docs 접속하여 Swagger UI 사용

### 전체 워크플로우 테스트
1. http://localhost 접속
2. 비디오 업로드
3. 라이브러리에서 확인
4. 비디오 플레이어에서 클립 추출

## 6단계: 정리

```bash
# 서비스 중지
docker-compose down

# 볼륨까지 삭제 (데이터 삭제)
docker-compose down -v
```

## 트러블슈팅

### Docker Desktop이 시작되지 않음
- Windows 서비스에서 "Docker Desktop Service" 확인
- WSL 2 업데이트 필요할 수 있음

### 포트 충돌 (8000, 80, 5432)
```bash
# 포트 변경 (docker-compose.yml 수정)
services:
  backend:
    ports:
      - "8001:8000"  # 8001로 변경
  frontend:
    ports:
      - "8080:80"    # 8080으로 변경
```

### 빌드 실패
```bash
# 캐시 없이 재빌드
docker-compose build --no-cache
docker-compose up -d
```
