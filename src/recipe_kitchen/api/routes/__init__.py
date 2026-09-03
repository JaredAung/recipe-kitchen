from fastapi import APIRouter

from recipe_kitchen.api.routes import audio, health, ingest, video

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(audio.router)
api_router.include_router(ingest.router)
api_router.include_router(video.router)
