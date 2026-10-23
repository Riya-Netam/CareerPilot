from fastapi import APIRouter

from app.api.routes import (admin, applications, auth, cover_letters, dashboard, health, jobs, resumes, roadmaps, users)

api_router = APIRouter()
for module in (health, auth, users, resumes, jobs, roadmaps, cover_letters, applications, dashboard, admin):
    api_router.include_router(module.router)
