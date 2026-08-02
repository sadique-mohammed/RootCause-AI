"""Health check endpoint."""

from fastapi import APIRouter

from backend.app.api.schemas import HealthResponse

from backend.app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def check_health() -> HealthResponse:
    """Verify the API is running and return configuration context."""
    model = settings.ollama_model if settings.litellm_provider == "ollama" else (settings.gemini_model if settings.litellm_provider == "gemini" else settings.openai_model)
    return HealthResponse(
        status="ok", 
        version="1.0.0",
        llm_provider=settings.litellm_provider,
        llm_model=model
    )
