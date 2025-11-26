"""
GCS Authentication Utility

GCS 인증 상태를 확인하고 명확한 에러 메시지를 제공합니다.
"""
import os
from pathlib import Path
from typing import Optional, Dict
import logging

from google.cloud import storage
from google.oauth2 import service_account
from google.auth.exceptions import DefaultCredentialsError

logger = logging.getLogger(__name__)


class GCSAuthenticationError(Exception):
    """GCS 인증 실패 시 발생"""
    pass


def get_credentials_from_file(credentials_path: str) -> service_account.Credentials:
    """
    서비스 계정 키 파일에서 인증 정보를 로드합니다.

    Args:
        credentials_path: 서비스 계정 JSON 키 파일 경로

    Returns:
        Credentials 객체

    Raises:
        GCSAuthenticationError: 키 파일이 없거나 유효하지 않은 경우
    """
    # 절대 경로 변환
    abs_path = Path(credentials_path).resolve()

    if not abs_path.exists():
        raise GCSAuthenticationError(
            f"GCS 서비스 계정 키 파일을 찾을 수 없습니다: {abs_path}\n"
            "해결 방법:\n"
            "1. Google Cloud Console에서 서비스 계정 키를 생성하세요\n"
            "2. 키 파일을 backend/secrets/gcs-key.json 에 저장하세요\n"
            "3. 또는 .env에서 GCS_CREDENTIALS_PATH를 올바른 경로로 설정하세요"
        )

    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(abs_path)
        )
        logger.info(f"GCS 인증 정보 로드 완료: {abs_path}")
        return credentials
    except Exception as e:
        raise GCSAuthenticationError(
            f"GCS 서비스 계정 키 파일이 유효하지 않습니다: {e}\n"
            "해결 방법:\n"
            "1. JSON 파일 형식이 올바른지 확인하세요\n"
            "2. 키가 만료되지 않았는지 확인하세요"
        )


def get_gcs_client_with_validation(
    project_id: str,
    credentials_path: str,
    bucket_name: Optional[str] = None
) -> storage.Client:
    """
    GCS 클라이언트를 생성하고 연결을 검증합니다.

    Args:
        project_id: GCP 프로젝트 ID
        credentials_path: 서비스 계정 JSON 키 파일 경로
        bucket_name: (선택) 버킷 접근 권한도 검증

    Returns:
        검증된 GCS Client

    Raises:
        GCSAuthenticationError: 인증 또는 권한 문제
    """
    credentials = get_credentials_from_file(credentials_path)

    try:
        client = storage.Client(
            project=project_id,
            credentials=credentials
        )

        # 버킷 접근 권한 검증
        if bucket_name:
            bucket = client.bucket(bucket_name)
            if not bucket.exists():
                raise GCSAuthenticationError(
                    f"GCS 버킷에 접근할 수 없습니다: {bucket_name}\n"
                    "확인 사항:\n"
                    "1. 버킷 이름이 올바른지 확인하세요\n"
                    "2. 서비스 계정에 'Storage Object Viewer' 권한이 있는지 확인하세요"
                )

        logger.info(f"GCS 클라이언트 생성 완료: project={project_id}")
        return client

    except DefaultCredentialsError as e:
        raise GCSAuthenticationError(
            f"GCS 인증 실패 (DefaultCredentialsError): {e}\n"
            "해결 방법:\n"
            "1. GOOGLE_APPLICATION_CREDENTIALS 환경 변수 설정\n"
            "   $env:GOOGLE_APPLICATION_CREDENTIALS = 'path/to/key.json'\n"
            "2. 또는 gcloud auth application-default login 실행\n"
            "3. 또는 코드에서 명시적으로 credentials 전달"
        )


def check_gcs_connection(
    project_id: str,
    credentials_path: str,
    bucket_name: str
) -> Dict[str, any]:
    """
    GCS 연결 상태를 종합적으로 확인합니다.

    Returns:
        Dict with 'status', 'project', 'bucket', 'error' (if any)
    """
    result = {
        "status": "unknown",
        "project": project_id,
        "bucket": bucket_name,
        "credentials_path": credentials_path,
        "error": None
    }

    try:
        # 1. 키 파일 확인
        credentials = get_credentials_from_file(credentials_path)
        result["credentials_valid"] = True

        # 2. 클라이언트 생성
        client = storage.Client(project=project_id, credentials=credentials)
        result["client_created"] = True

        # 3. 버킷 접근
        bucket = client.bucket(bucket_name)
        result["bucket_exists"] = bucket.exists()

        if result["bucket_exists"]:
            # 4. 파일 목록 조회 테스트 (권한 확인)
            blobs = list(bucket.list_blobs(max_results=1))
            result["can_list_objects"] = True
            result["status"] = "ok"
        else:
            result["status"] = "bucket_not_found"
            result["error"] = f"버킷을 찾을 수 없습니다: {bucket_name}"

    except GCSAuthenticationError as e:
        result["status"] = "auth_error"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def generate_signed_url(
    bucket_name: str,
    blob_name: str,
    credentials_path: str,
    expiration_minutes: int = 10
) -> str:
    """
    GCS 객체에 대한 Signed URL을 생성합니다.

    Args:
        bucket_name: 버킷 이름
        blob_name: 객체 경로
        credentials_path: 서비스 계정 키 파일 경로
        expiration_minutes: URL 유효 시간 (분)

    Returns:
        Signed URL 문자열

    Raises:
        GCSAuthenticationError: 인증 실패
    """
    from datetime import timedelta

    credentials = get_credentials_from_file(credentials_path)
    client = storage.Client(credentials=credentials)

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET"
    )

    logger.info(f"Signed URL 생성: {blob_name} ({expiration_minutes}분 유효)")
    return url
