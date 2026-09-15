from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="Thumbnail Creation API")
app.include_router(health.router)
