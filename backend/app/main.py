from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.redis import close_redis, redis_client


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="API quản lý Todo, RBAC, thông báo realtime và trợ lý AI.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready", tags=["System"])
async def ready() -> dict[str, str]:
    await redis_client.ping()
    async with engine.connect() as connection:
        await connection.exec_driver_sql("SELECT 1")
    return {"status": "ready"}
