from fastapi import APIRouter

from recipe_kitchen.api.routes import audio, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(audio.router)
