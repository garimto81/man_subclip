"""
FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings
from src.database import engine, Base

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="원본 영상을 Proxy로 렌더링하고, 타임코드 기반으로 서브클립을 추출하는 플랫폼",
)


@app.on_event("startup")
async def startup_event():
    """Create database tables and verify dependencies on startup"""
    import logging
    logger = logging.getLogger(__name__)

    # 1. ffmpeg 설치 확인
    try:
        from src.utils.ffmpeg_check import check_ffmpeg_installation, verify_ffmpeg_capabilities
        ffmpeg_info = check_ffmpeg_installation()
        logger.info(f"ffmpeg 확인: {ffmpeg_info['version']}")

        capabilities = verify_ffmpeg_capabilities()
        logger.info(f"ffmpeg 기능: {capabilities}")
    except Exception as e:
        logger.warning(f"ffmpeg 확인 실패 (일부 기능 제한될 수 있음): {e}")

    # 2. GCS 인증 확인 (설정된 경우)
    if settings.use_gcs:
        try:
            from src.utils.gcs_auth import check_gcs_connection
            gcs_status = check_gcs_connection(
                project_id=settings.gcs_project_id,
                credentials_path=settings.gcs_credentials_path,
                bucket_name=settings.gcs_bucket_name
            )
            if gcs_status["status"] == "ok":
                logger.info(f"GCS 연결 확인: {settings.gcs_bucket_name}")
            else:
                logger.warning(f"GCS 연결 문제: {gcs_status.get('error', 'unknown')}")
        except Exception as e:
            logger.warning(f"GCS 확인 실패: {e}")

    # 3. Import models to register them with Base
    from src.models import Video, Clip  # noqa
    Base.metadata.create_all(bind=engine)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Video Proxy & Subclip Platform API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with dependency status"""
    from src.utils.ffmpeg_check import check_ffmpeg_installation, verify_ffmpeg_capabilities

    health = {"status": "healthy", "dependencies": {}}

    # 1. ffmpeg 상태 확인
    try:
        ffmpeg_info = check_ffmpeg_installation()
        capabilities = verify_ffmpeg_capabilities()
        health["dependencies"]["ffmpeg"] = {
            "status": "ok",
            "version": ffmpeg_info.get("version", "unknown"),
            "capabilities": capabilities
        }
    except Exception as e:
        health["dependencies"]["ffmpeg"] = {
            "status": "error",
            "message": str(e)
        }
        health["status"] = "degraded"

    # 2. GCS 상태 확인 (설정된 경우)
    if settings.use_gcs:
        try:
            from src.utils.gcs_auth import check_gcs_connection
            gcs_status = check_gcs_connection(
                project_id=settings.gcs_project_id,
                credentials_path=settings.gcs_credentials_path,
                bucket_name=settings.gcs_bucket_name
            )
            health["dependencies"]["gcs"] = {
                "status": gcs_status["status"],
                "bucket": settings.gcs_bucket_name,
                "project": settings.gcs_project_id
            }
            if gcs_status["status"] != "ok":
                health["dependencies"]["gcs"]["error"] = gcs_status.get("error")
                health["status"] = "degraded"
        except Exception as e:
            health["dependencies"]["gcs"] = {
                "status": "error",
                "message": str(e)
            }
            health["status"] = "degraded"
    else:
        health["dependencies"]["gcs"] = {"status": "disabled"}

    return health


# Include routers
from src.api.videos import router as videos_router
from src.api.clips import router as clips_router
from src.api.gcs import router as gcs_router
from src.api.search import router as search_router

app.include_router(videos_router)
app.include_router(clips_router)
app.include_router(gcs_router)
app.include_router(search_router)
