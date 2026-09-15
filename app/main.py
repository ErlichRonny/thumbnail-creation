from fastapi import FastAPI

from app.routers import health, images

app = FastAPI(title="Thumbnail Creation API")
app.include_router(health.router)
app.include_router(images.router)
