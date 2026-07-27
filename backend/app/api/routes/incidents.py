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


# Only incidents with real scripts are advertised. The harness must not claim
# success until it has executed and verified the requested state transition.
CATALOG = [
    IncidentCatalogRead(
        id="10",
        name="TCP Retransmissions",
        description="High packet loss causing TCP retransmissions.",
        category="network",
        difficulty="hard",
        seed_script_path="incidents/seed/10-tcp-retransmissions.sh",
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

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Incident execution harness is not connected to a target VM yet.",
    )


@router.post("/incidents/reset", response_model=SeedResponse)
async def reset_incident(request: SeedRequest) -> SeedResponse:
    """Run an incident reset script on the target VM."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Incident reset harness is not connected to a target VM yet.",
    )
