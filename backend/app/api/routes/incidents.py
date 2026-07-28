"""Incident catalog and seeding endpoints."""


from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import paramiko
from pathlib import Path
from backend.app.config import settings

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
        id="04",
        name="DNS Failure",
        description="Drops outbound DNS traffic using iptables.",
        category="network",
        difficulty="medium",
        seed_script_path="incidents/seed/04-dns-failure.sh",
    ),
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

    script_path = Path(incident.seed_script_path)
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Seed script not found locally.")

    host = request.target_host or settings.target_host
    user = request.ssh_username or settings.target_user
    key_path = request.ssh_key_path or settings.target_ssh_key

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    import os
    try:
        connect_kwargs = {"hostname": host, "username": user, "timeout": 10}
        if key_path:
            connect_kwargs["key_filename"] = os.path.expanduser(key_path)
        password = request.ssh_password or settings.target_password
        if password is not None:
            connect_kwargs["password"] = password

        client.connect(**connect_kwargs)
        
        script_content = script_path.read_text()
        # Use sudo bash to execute the script content
        stdin, stdout, stderr = client.exec_command("sudo bash")
        stdin.write(script_content)
        stdin.close()
        
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        if exit_status != 0:
            raise HTTPException(status_code=500, detail=f"Seed script failed: {err}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH execution failed: {e}")
    finally:
        client.close()

    return SeedResponse(status="success", message="Incident seeded successfully")


@router.post("/incidents/reset", response_model=SeedResponse)
async def reset_incident(request: SeedRequest) -> SeedResponse:
    """Run an incident reset script on the target VM."""
    incident = next((i for i in CATALOG if i.id == request.incident_id), None)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident ID not found in catalog.",
        )

    # Assuming reset scripts are just changing 'seed' to 'reset' in path
    script_path = Path(incident.seed_script_path.replace("/seed/", "/reset/"))
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Reset script not found locally.")

    host = request.target_host or settings.target_host
    user = request.ssh_username or settings.target_user
    key_path = request.ssh_key_path or settings.target_ssh_key

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    import os
    try:
        connect_kwargs = {"hostname": host, "username": user, "timeout": 10}
        if key_path:
            connect_kwargs["key_filename"] = os.path.expanduser(key_path)
        password = request.ssh_password or settings.target_password
        if password is not None:
            connect_kwargs["password"] = password

        client.connect(**connect_kwargs)
        
        script_content = script_path.read_text()
        stdin, stdout, stderr = client.exec_command("sudo bash")
        stdin.write(script_content)
        stdin.close()
        
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        if exit_status != 0:
            raise HTTPException(status_code=500, detail=f"Reset script failed: {err}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH execution failed: {e}")
    finally:
        client.close()

    return SeedResponse(status="success", message="Incident reset successfully")
