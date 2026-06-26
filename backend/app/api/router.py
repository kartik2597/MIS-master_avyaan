from fastapi import APIRouter

from app.api.routes import auth, dashboard, employees, health, imports, uploads


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(health.router, tags=["health"])
