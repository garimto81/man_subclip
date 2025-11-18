"""
FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="원본 영상을 Proxy로 렌더링하고, 타임코드 기반으로 서브클립을 추출하는 플랫폼",
)

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
    """Health check endpoint"""
    return {"status": "healthy"}


# Include routers
from src.api.videos import router as videos_router
app.include_router(videos_router)
# TODO: Add clips router when implemented
# from src.api.clips import router as clips_router
# app.include_router(clips_router)
