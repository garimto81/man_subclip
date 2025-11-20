#!/bin/bash
# IAM 권한 전파 자동 체크 스크립트

echo "=== IAM 권한 전파 자동 체크 시작 ==="
echo "2분 간격으로 최대 30분 동안 체크합니다."
echo ""

attempt=1
max_attempts=15  # 30분 (2분 x 15)

while [ $attempt -le $max_attempts ]; do
    echo "[$attempt/$max_attempts] 시도 중... ($(date '+%H:%M:%S'))"

    # API 호출
    response=$(curl -s -X POST http://localhost:8002/api/preview \
        -H "Content-Type: application/json" \
        -d '{"hand_id": "h_wsop24_ev1_sample_03"}')

    # 성공 여부 확인
    if echo "$response" | grep -q '"status":"pending"'; then
        echo ""
        echo "===================================="
        echo "✅ 성공! IAM 권한이 적용되었습니다!"
        echo "===================================="
        echo ""
        echo "응답:"
        echo "$response" | python -m json.tool
        exit 0
    elif echo "$response" | grep -q "Permission denied"; then
        echo "   ❌ 여전히 Permission denied (대기 중...)"
    else
        echo "   ⚠️  예상치 못한 응답:"
        echo "$response" | python -m json.tool
    fi

    # 마지막 시도가 아니면 2분 대기
    if [ $attempt -lt $max_attempts ]; then
        echo "   다음 체크까지 2분 대기..."
        echo ""
        sleep 120
    fi

    attempt=$((attempt + 1))
done

echo ""
echo "===================================="
echo "❌ 30분 경과: IAM 권한이 적용되지 않았습니다."
echo "===================================="
echo "GCP 콘솔에서 수동으로 권한을 확인해주세요:"
echo "https://console.cloud.google.com/storage/browser/wsop-archive-raw?project=gg-poker-prod"
exit 1
