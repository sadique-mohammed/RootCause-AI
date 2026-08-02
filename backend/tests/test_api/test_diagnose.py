"""Tests for API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import DiagnosisRun, EvidenceItemDB


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Test the /health endpoint."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


@pytest.mark.asyncio
@patch("backend.app.api.routes.diagnose.run_diagnosis", new_callable=AsyncMock)
@patch("backend.app.api.routes.diagnose.SSHRunner")
async def test_diagnose_post_success(
    mock_ssh_runner_class: MagicMock,
    mock_run_diagnosis: AsyncMock,
    async_client: AsyncClient,
) -> None:
    """Test starting a diagnosis successfully."""
    # Setup mock
    mock_runner = MagicMock()
    mock_runner.ping_connection.return_value = True
    mock_ssh_runner_class.return_value = mock_runner

    response = await async_client.post(
        "/api/v1/diagnose",
        json={"target_host": "10.0.0.1", "incident_description": "Server is down"},
    )

    assert response.status_code == 202
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "pending"
    assert mock_runner.ping_connection.called
    assert mock_run_diagnosis.await_count == 1


@pytest.mark.asyncio
@patch("backend.app.api.routes.diagnose.SSHRunner")
async def test_diagnose_post_preflight_fail(
    mock_ssh_runner_class: MagicMock,
    async_client: AsyncClient,
) -> None:
    """Test starting a diagnosis where preflight ping fails."""
    # Setup mock
    mock_runner = MagicMock()
    mock_runner.ping_connection.return_value = False
    mock_ssh_runner_class.return_value = mock_runner

    response = await async_client.post(
        "/api/v1/diagnose",
        json={"target_host": "10.0.0.1", "incident_description": "Server is down"},
    )

    assert response.status_code == 503
    data = response.json()
    assert "detail" in data
    assert "Pre-flight SSH ping failed" in data["detail"]


@pytest.mark.asyncio
async def test_get_diagnosis(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test retrieving a diagnosis."""
    # Insert dummy data
    run = DiagnosisRun(
        target_host="10.0.0.1",
        incident_description="Test incident",
        status="running",
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    response = await async_client.get(f"/api/v1/diagnose/{run.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(run.id)
    assert data["status"] == "running"
    assert data["incident_description"] == "Test incident"
    assert "evidence" in data
    assert len(data["evidence"]) == 0


@pytest.mark.asyncio
async def test_get_diagnosis_not_found(async_client: AsyncClient) -> None:
    """Test retrieving a non-existent diagnosis."""
    import uuid
    dummy_uuid = str(uuid.uuid4())

    response = await async_client.get(f"/api/v1/diagnose/{dummy_uuid}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_incidents_catalog(async_client: AsyncClient) -> None:
    """Test incidents catalog retrieval."""
    response = await async_client.get("/api/v1/incidents/catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "incident_id" not in data[0]  # Make sure schema matches
    assert "id" in data[0]


@pytest.mark.asyncio
async def test_incidents_seed_disabled_by_default(async_client: AsyncClient) -> None:
    """Incident mutation endpoints must fail closed unless explicitly enabled."""
    response = await async_client.post(
        "/api/v1/incidents/seed",
        json={"incident_id": "04"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
@patch("backend.app.api.routes.incidents.paramiko.SSHClient")
async def test_incidents_seed_success(
    mock_ssh_client: MagicMock,
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test incident seeding without real SSH connection."""
    monkeypatch.setattr("backend.app.api.routes.incidents.settings.incident_mutation_enabled", True)
    # Setup mock to return exit code 0
    mock_client_instance = MagicMock()
    mock_ssh_client.return_value = mock_client_instance
    mock_stdout = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_stdout.read.return_value = b"success"
    mock_client_instance.exec_command.return_value = (MagicMock(), mock_stdout, MagicMock())

    response = await async_client.post(
        "/api/v1/incidents/seed",
        json={"incident_id": "04"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_incidents_seed_not_found(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test incident seeding with invalid ID."""
    monkeypatch.setattr("backend.app.api.routes.incidents.settings.incident_mutation_enabled", True)
    response = await async_client.post(
        "/api/v1/incidents/seed",
        json={"incident_id": "invalid_id"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_command_log_not_found(async_client: AsyncClient) -> None:
    """The command log endpoint must preserve the API contract."""
    import uuid

    response = await async_client.get(f"/api/v1/diagnose/{uuid.uuid4()}/commands")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_evidence(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test retrieving evidence for a diagnosis run."""
    run = DiagnosisRun(
        target_host="10.0.0.1",
        incident_description="Test incident",
        status="completed",
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    evidence = EvidenceItemDB(
        run_id=run.id,
        step_number=1,
        tool_name="check_dns",
        tool_args={"domain": "example.com"},
        raw_output="timeout",
        key_finding="DNS timed out",
        relevance="DNS failure explains the incident",
        supports_conclusion=True,
    )
    db_session.add(evidence)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/diagnose/{run.id}/evidence")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tool_name"] == "check_dns"
