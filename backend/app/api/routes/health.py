"""Health check endpoint."""

from fastapi import APIRouter

from backend.app.api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def check_health() -> HealthResponse:
    """Verify the API is running."""
    return HealthResponse(status="ok", version="1.0.0")
