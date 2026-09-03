import logging

from fastapi import FastAPI

from recipe_kitchen.api.routes import api_router

logging.getLogger("recipe_kitchen").setLevel(logging.INFO)

app = FastAPI(title="recipe-kitchen")
app.include_router(api_router)
