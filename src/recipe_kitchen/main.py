import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from recipe_kitchen.api.routes import api_router
from recipe_kitchen.core.config import get_settings

logging.getLogger("recipe_kitchen").setLevel(logging.INFO)

app = FastAPI(title="recipe-kitchen")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
