"""Incident catalog and seeding endpoints."""

import asyncio
import os
from pathlib import Path
from typing import Any

import paramiko
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

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


class SeedResponse(BaseModel):
    status: str
    message: str


# Only incidents with real scripts are advertised. The harness must not claim
# success until it has executed and verified the requested state transition.
CATALOG = [
    IncidentCatalogRead(
        id="01",
        name="Nginx Won't Start",
        description="Nginx fails to start due to a syntax error in nginx.conf.",
        category="service",
        difficulty="easy",
        seed_script_path="incidents/seed/01-nginx-wont-start.sh",
    ),
    IncidentCatalogRead(
        id="02",
        name="Disk Full",
        description="Root partition filled to capacity by a hidden file.",
        category="disk",
        difficulty="easy",
        seed_script_path="incidents/seed/02-disk-full.sh",
    ),
    IncidentCatalogRead(
        id="03",
        name="Memory Leak / OOM",
        description="A runaway process continuously allocates memory until OOM.",
        category="memory",
        difficulty="medium",
        seed_script_path="incidents/seed/03-memory-leak-oom.sh",
    ),
    IncidentCatalogRead(
        id="04",
        name="DNS Failure",
        description="Drops outbound DNS traffic using iptables.",
        category="network",
        difficulty="medium",
        seed_script_path="incidents/seed/04-dns-failure.sh",
    ),
    IncidentCatalogRead(
        id="05",
        name="Wrong Default Route",
        description="Default gateway replaced with a bogus unreachable address.",
        category="network",
        difficulty="medium",
        seed_script_path="incidents/seed/05-wrong-default-route.sh",
    ),
    IncidentCatalogRead(
        id="06",
        name="Interface Down",
        description="A secondary network interface is administratively brought down.",
        category="network",
        difficulty="easy",
        seed_script_path="incidents/seed/06-interface-down.sh",
    ),
    IncidentCatalogRead(
        id="07",
        name="High CPU Runaway",
        description="An infinite loop process consumes 100% of one CPU core.",
        category="process",
        difficulty="easy",
        seed_script_path="incidents/seed/07-high-cpu-runaway.sh",
    ),
    IncidentCatalogRead(
        id="08",
        name="Port Conflict",
        description="A rogue process occupies port 80, preventing nginx from binding.",
        category="service",
        difficulty="medium",
        seed_script_path="incidents/seed/08-port-conflict.sh",
    ),
    IncidentCatalogRead(
        id="09",
        name="Expired TLS Certificate",
        description="Nginx configured with an already-expired self-signed TLS certificate.",
        category="security",
        difficulty="medium",
        seed_script_path="incidents/seed/09-expired-tls-cert.sh",
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


def _execute_script_via_ssh(
    script_path: Path,
) -> None:
    """SSH into the configured lab VM and execute a bash script via sudo."""
    host = settings.target_host
    user = settings.target_user
    key_path = settings.target_ssh_key

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    if settings.ssh_accept_unknown_host_keys:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        connect_kwargs: dict[str, Any] = {
            "hostname": host,
            "username": user,
            "timeout": 10,
        }
        if key_path:
            connect_kwargs["key_filename"] = os.path.expanduser(key_path)
        password = settings.target_password
        if password is not None:
            connect_kwargs["password"] = password

        client.connect(**connect_kwargs)

        script_content = script_path.read_text()
        stdin, stdout, stderr = client.exec_command("sudo bash")
        stdin.write(script_content)
        stdin.close()

        exit_status = stdout.channel.recv_exit_status()
        # Must read streams to avoid blocking / channel deadlock
        stdout.read()
        err = stderr.read().decode()

        if exit_status != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Script failed (exit {exit_status}): {err}",
            )
    except HTTPException:
        raise
    except paramiko.SSHException as e:
        raise HTTPException(
            status_code=500,
            detail=f"SSH connection failed: {e}",
        ) from e
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"SSH execution failed: {e}",
        ) from e
    finally:
        client.close()


def _require_incident_mutation_enabled(authorization: str | None) -> None:
    """Reject privileged lab mutation endpoints unless explicitly enabled."""
    if not settings.incident_mutation_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incident seed/reset endpoints are disabled. Set INCIDENT_MUTATION_ENABLED=true for a lab VM.",
        )

    if settings.incident_control_token:
        expected = f"Bearer {settings.incident_control_token}"
        if authorization != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid incident control token.",
            )


@router.get("/incidents/catalog", response_model=list[IncidentCatalogRead])
async def get_catalog() -> list[IncidentCatalogRead]:
    """Get the catalog of available incidents."""
    return CATALOG


@router.post("/incidents/seed", response_model=SeedResponse)
async def seed_incident(
    request: SeedRequest,
    authorization: str | None = Header(default=None),
) -> SeedResponse:
    """Run an incident seed script on the target VM."""
    _require_incident_mutation_enabled(authorization)
    incident = next((i for i in CATALOG if i.id == request.incident_id), None)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident ID not found in catalog.",
        )

    script_path = Path(incident.seed_script_path)
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Seed script not found locally.")

    await asyncio.to_thread(_execute_script_via_ssh, script_path)
    return SeedResponse(status="success", message="Incident seeded successfully")


@router.post("/incidents/reset", response_model=SeedResponse)
async def reset_incident(
    request: SeedRequest,
    authorization: str | None = Header(default=None),
) -> SeedResponse:
    """Run an incident reset script on the target VM."""
    _require_incident_mutation_enabled(authorization)
    incident = next((i for i in CATALOG if i.id == request.incident_id), None)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident ID not found in catalog.",
        )

    # Reset scripts mirror seed scripts with /seed/ replaced by /reset/
    script_path = Path(incident.seed_script_path.replace("/seed/", "/reset/"))
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Reset script not found locally.")

    await asyncio.to_thread(_execute_script_via_ssh, script_path)
    return SeedResponse(status="success", message="Incident reset successfully")
