"""Render endpoints.

The API never renders. It creates a job row, pushes a message to Redis and
returns 202 with a job id. The frontend polls GET /render-jobs/{id}.
"""

import uuid

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, SessionDep
from app.schemas.render import RenderJobCreatedResponse, RenderJobResponse
from app.services.render_service import RenderService
from app.services.storage.urls import public_url

projects_router = APIRouter(prefix="/projects", tags=["renders"])
jobs_router = APIRouter(prefix="/render-jobs", tags=["renders"])


def _to_response(job) -> RenderJobResponse:
    return RenderJobResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        output_url=public_url(job.output_asset.storage_key) if job.output_asset else None,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


@projects_router.post(
    "/{project_id}/render",
    response_model=RenderJobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_render(
    project_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> RenderJobCreatedResponse:
    job = await RenderService(session).create_job(project_id, current_user.id)
    return RenderJobCreatedResponse(job_id=job.id, status=job.status)


@jobs_router.get("/{job_id}", response_model=RenderJobResponse)
async def get_render_job(
    job_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> RenderJobResponse:
    job = await RenderService(session).get_job(job_id, current_user.id)
    return _to_response(job)
