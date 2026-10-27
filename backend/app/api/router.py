"""Single place where all route modules are mounted."""

from fastapi import APIRouter

from app.api.routes import (
    account,
    admin,
    assets,
    auth,
    avatars,
    folders,
    generation,
    health,
    projects,
    purposes,
    renders,
    scenes,
    templates,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(admin.router)
api_router.include_router(avatars.router)
api_router.include_router(folders.router)
api_router.include_router(projects.router)
api_router.include_router(purposes.router)
api_router.include_router(templates.router)
api_router.include_router(scenes.project_scenes_router)
api_router.include_router(scenes.scenes_router)
api_router.include_router(generation.projects_router)
api_router.include_router(generation.scenes_router)
api_router.include_router(renders.projects_router)
api_router.include_router(renders.jobs_router)
api_router.include_router(assets.router)
api_router.include_router(assets.project_media_router)
