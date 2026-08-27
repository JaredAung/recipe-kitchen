from fastapi import FastAPI

from recipe_kitchen.api.routes import api_router

app = FastAPI(title="recipe-kitchen")
app.include_router(api_router)
