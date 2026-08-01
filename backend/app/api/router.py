from fastapi import APIRouter

from app.api import admin, ai, auth, notifications, todos

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(todos.router)
api_router.include_router(todos.categories_router)
api_router.include_router(notifications.router)
api_router.include_router(notifications.ws_router)
api_router.include_router(ai.router)
api_router.include_router(admin.router)
