"""
78초 ~ 136초 구간만 자른 짧은 클립용 hand 추가
원본 영상 기준: 1498.5초 ~ 1556.5초 (58초)
"""

from google.cloud import firestore

# Firestore 클라이언트 (환경 변수 GOOGLE_APPLICATION_CREDENTIALS 사용)
GCP_PROJECT = 'gg-poker-prod'
db = firestore.Client(project=GCP_PROJECT)

# 짧은 클립 hand 데이터
short_clip_hand = {
    'hand_id': 'h_wsop24_ev1_short_clip_01',
    'video_ref_id': 'wsop24_ev1_part1_short',  # 새 video_id
    'event_id': 'wsop24_ev1',
    'media_refs': {
        'master_gcs_uri': 'gs://wsop-archive-raw/Archive-MAM_Sample.mp4',
        'time_range': {
            'start_seconds': 1498.5,  # 원본 78초 지점
            'end_seconds': 1556.5,    # 원본 136초 지점
            'duration_seconds': 58.0
        }
    },
    'hand_number': 999,
    'table_id': 'feature_table_1',
    'blinds': {
        'small_blind': 1000,
        'big_blind': 2000,
        'ante': 200
    },
    'pot': {
        'pot_preflop': 3400,
        'pot_final': 125000
    },
    'players': [
        {
            'display_name': 'Sample Player 1',
            'position': 'BTN'
        },
        {
            'display_name': 'Sample Player 2',
            'position': 'BB'
        }
    ]
}

def add_short_clip():
    """짧은 클립 hand를 Firestore에 추가"""

    hand_id = short_clip_hand['hand_id']

    try:
        # 기존 문서 확인
        hand_ref = db.collection('hands').document(hand_id)
        existing = hand_ref.get()

        if existing.exists:
            print(f"[WARN] 이미 존재하는 hand: {hand_id}")
            print("[INFO] 덮어쓰기 진행...")

        # 문서 생성/업데이트
        hand_ref.set(short_clip_hand)
        print(f"[SUCCESS] Hand 추가 완료: {hand_id}")
        print(f"   - Video Ref: {short_clip_hand['video_ref_id']}")
        print(f"   - GCS URI: {short_clip_hand['media_refs']['master_gcs_uri']}")
        print(f"   - Time Range: {short_clip_hand['media_refs']['time_range']['start_seconds']}s ~ {short_clip_hand['media_refs']['time_range']['end_seconds']}s")
        print(f"   - Duration: {short_clip_hand['media_refs']['time_range']['duration_seconds']}초")
        print()
        print("[NEXT] 다음 명령어로 Proxy HLS 변환 시작:")
        print(f'   Invoke-RestMethod -Uri "http://localhost:8002/api/preview" -Method Post -ContentType "application/json" -Body \'{{"hand_id": "{hand_id}"}}\' | ConvertTo-Json')

    except Exception as e:
        print(f"[ERROR] 실패: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    add_short_clip()
