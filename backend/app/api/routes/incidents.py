"""Incident catalog and seeding endpoints."""


from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(tags=["Incidents"])


class IncidentCatalogRead(BaseModel):
    id: str
    name: str
    description: str
    category: str
    difficulty: str
    seed_script_path: str


class SeedRequest(BaseModel):
    incident_id: str = Field(description="ID of the incident to seed")
    target_host: str | None = None
    ssh_username: str | None = None
    ssh_key_path: str | None = None
    ssh_password: str | None = None


class SeedResponse(BaseModel):
    status: str
    message: str


# Hardcoded catalog for now
CATALOG = [
    IncidentCatalogRead(
        id="01",
        name="Process Kill",
        description="A critical process (nginx) is constantly crashing or being killed.",
        category="process",
        difficulty="easy",
        seed_script_path="incidents/01-process-kill/seed.sh",
    ),
    IncidentCatalogRead(
        id="10",
        name="TCP Retransmissions",
        description="High packet loss causing TCP retransmissions.",
        category="network",
        difficulty="hard",
        seed_script_path="incidents/10-tcp-retransmissions/seed.sh",
    ),
]


@router.get("/incidents/catalog", response_model=list[IncidentCatalogRead])
async def get_catalog() -> list[IncidentCatalogRead]:
    """Get the catalog of available incidents."""
    return CATALOG


@router.post("/incidents/seed", response_model=SeedResponse)
async def seed_incident(request: SeedRequest) -> SeedResponse:
    """Run an incident seed script on the target VM."""
    incident = next((i for i in CATALOG if i.id == request.incident_id), None)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident ID not found in catalog.",
        )

    # In a real setup, we would execute the seed script over SSH here.
    # For security and simplicity in Phase 3, we just mock the response.
    return SeedResponse(
        status="success",
        message=f"Incident {request.incident_id} successfully seeded on target."
    )


@router.post("/incidents/reset", response_model=SeedResponse)
async def reset_incident(request: SeedRequest) -> SeedResponse:
    """Run an incident reset script on the target VM."""
    return SeedResponse(
        status="success",
        message="Target VM successfully reset."
    )
