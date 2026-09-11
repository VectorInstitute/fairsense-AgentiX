"""Tests for the FastAPI service layer (``fairsense_agentix.service_api``).

Runs against the fake tool stack forced by ``tests/conftest.py``; no network or
model downloads. Uses ``TestClient`` as a context manager so the lifespan hook
initialises the shared engine and event bus exactly as in production.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fairsense_agentix.configs import settings
from fairsense_agentix.service_api import app_state
from fairsense_agentix.service_api.schemas import BatchRequest
from fairsense_agentix.service_api.server import app
from fairsense_agentix.service_api.utils import (
    detect_input_type,
    looks_like_csv,
    normalize_input_hint,
)


FIXTURES = Path(__file__).parent.parent / "fixtures"
HEALTH_MODULE = "fairsense_agentix.service_api.routes.health"


# ---------------------------------------------------------------------------
# Pure helpers (unit)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInputDetection:
    """Input-type detection and hint normalisation helpers."""

    def test_bytes_are_image(self) -> None:
        """Bytes are image."""
        assert detect_input_type(b"\x89PNG") == "image"

    @pytest.mark.parametrize("suffix", [".png", ".jpg", ".jpeg", ".gif", ".webp"])
    def test_image_suffixes(self, suffix: str) -> None:
        """Image suffixes."""
        assert detect_input_type(Path(f"photo{suffix}")) == "image"

    def test_csv_suffix(self) -> None:
        """Csv suffix."""
        assert detect_input_type(Path("scenario.csv")) == "csv"

    def test_plain_text(self) -> None:
        """Plain text."""
        assert detect_input_type("We need a young, energetic developer") == "text"

    def test_tabular_string_is_csv(self) -> None:
        """Tabular string is csv."""
        assert detect_input_type("a,b,c\n1,2,3\n4,5,6") == "csv"

    def test_looks_like_csv_rejects_prose_with_commas(self) -> None:
        """Looks like csv rejects prose with commas."""
        assert not looks_like_csv("Fast, cheap, reliable")
        assert not looks_like_csv("a,b\nc")  # inconsistent column counts

    @pytest.mark.parametrize(
        ("hint", "expected"),
        [
            (None, None),
            ("bias_text", "text"),
            ("bias_image", "image"),
            ("bias_image_vlm", "image"),
            ("risk", "csv"),
            ("text", "text"),
        ],
    )
    def test_normalize_input_hint(self, hint: str | None, expected: str | None) -> None:
        """Normalize input hint."""
        assert normalize_input_hint(hint) == expected  # type: ignore[arg-type]


@pytest.mark.unit
def test_batch_request_requires_items() -> None:
    with pytest.raises(ValueError, match="at least one item"):
        BatchRequest(items=[])


# ---------------------------------------------------------------------------
# HTTP surface (integration, fake tools)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _wait_for(predicate, timeout: float = 10.0) -> None:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("timed out waiting for background task")


@pytest.mark.integration
class TestHealth:
    """Readiness probe."""

    def test_health_reports_mock_mode(self, client: TestClient) -> None:
        """Health reports mock mode."""
        body = client.get("/v1/health").json()
        assert body["status"] == "ok"
        assert body["llm_provider"] == settings.llm_provider
        assert body["mock_mode"] is (settings.llm_provider == "fake")


@pytest.mark.integration
class TestShutdownGuard:
    """``/v1/shutdown`` must never be reachable by an unauthenticated remote."""

    def test_hidden_when_disabled(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Hidden when disabled."""
        monkeypatch.setattr(settings, "api_enable_shutdown_endpoint", False)
        assert client.post("/v1/shutdown").status_code == 404

    def test_remote_client_forbidden_without_token(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Remote client forbidden without token."""
        monkeypatch.setattr(settings, "api_enable_shutdown_endpoint", True)
        monkeypatch.setattr(settings, "api_shutdown_token", None)
        # No context manager: skip the lifespan so the shared event bus stays
        # bound to the module-scoped client's loop. The route needs no engine.
        remote = TestClient(app, client=("203.0.113.7", 50000))
        assert remote.post("/v1/shutdown").status_code == 403

    def test_wrong_token_forbidden(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Wrong token forbidden."""
        monkeypatch.setattr(settings, "api_enable_shutdown_endpoint", True)
        monkeypatch.setattr(settings, "api_shutdown_token", "s3cret")
        assert client.post("/v1/shutdown").status_code == 403
        response = client.post("/v1/shutdown", headers={"X-Shutdown-Token": "nope"})
        assert response.status_code == 403

    def test_authorized_shutdown_schedules_exit(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Authorized shutdown schedules exit."""
        # Never actually exit the test process.
        calls: list[int] = []
        monkeypatch.setattr(f"{HEALTH_MODULE}.os._exit", calls.append)
        monkeypatch.setattr(f"{HEALTH_MODULE}.time.sleep", lambda _s: None)
        monkeypatch.setattr(settings, "api_enable_shutdown_endpoint", True)
        monkeypatch.setattr(settings, "api_shutdown_token", "s3cret")

        response = client.post("/v1/shutdown", headers={"X-Shutdown-Token": "s3cret"})

        assert response.status_code == 200
        assert response.json()["status"] == "shutting_down"
        assert calls == [0]  # background task ran after the response was sent

    def test_loopback_allowed_without_token(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Loopback allowed without token."""
        monkeypatch.setattr(f"{HEALTH_MODULE}.os._exit", lambda _c: None)
        monkeypatch.setattr(f"{HEALTH_MODULE}.time.sleep", lambda _s: None)
        monkeypatch.setattr(settings, "api_enable_shutdown_endpoint", True)
        monkeypatch.setattr(settings, "api_shutdown_token", None)
        assert client.post("/v1/shutdown").status_code == 200


@pytest.mark.integration
class TestAnalyze:
    """Synchronous JSON and upload analysis routes."""

    def test_text_analysis(self, client: TestClient) -> None:
        """Text analysis."""
        response = client.post(
            "/v1/analyze",
            json={"content": "We want a young, energetic developer."},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["workflow_id"] == "bias_text"
        assert body["bias_result"] is not None
        assert body["risk_result"] is None
        assert body["metadata"]["run_id"] == body["run_id"]
        assert body["metadata"]["mock_mode"] is True
        assert body["bias_result"]["warnings"][0].startswith("MOCK MODE")

    def test_risk_hint_routes_to_risk_workflow(self, client: TestClient) -> None:
        """Risk hint routes to risk workflow."""
        response = client.post(
            "/v1/analyze",
            json={
                "content": "Deploying a resume screener for hiring decisions.",
                "input_type": "risk",
                "options": {"top_k": 3},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["workflow_id"] == "risk"
        assert body["risk_result"] is not None
        assert body["bias_result"] is None

    def test_invalid_hint_rejected(self, client: TestClient) -> None:
        """Invalid hint rejected."""
        response = client.post(
            "/v1/analyze",
            json={"content": "x", "input_type": "not_a_workflow"},
        )
        assert response.status_code == 422

    def test_upload_text_file(self, client: TestClient) -> None:
        """Upload text file."""
        path = FIXTURES / "bias_text" / "age_bias.txt"
        with path.open("rb") as fh:
            response = client.post(
                "/v1/analyze/upload",
                files={"file": (path.name, fh, "text/plain")},
            )
        assert response.status_code == 200
        assert response.json()["workflow_id"] == "bias_text"

    def test_upload_image_file(self, client: TestClient) -> None:
        """Upload image file."""
        path = FIXTURES / "bias_images" / "gender_bias.jpg"
        with path.open("rb") as fh:
            response = client.post(
                "/v1/analyze/upload",
                files={"file": (path.name, fh, "image/jpeg")},
            )
        assert response.status_code == 200
        assert response.json()["workflow_id"].startswith("bias_image")

    def test_upload_undecodable_text_is_400(self, client: TestClient) -> None:
        """Upload undecodable text is 400."""
        response = client.post(
            "/v1/analyze/upload",
            files={
                "file": ("blob.bin", b"\xff\xfe\x00\x80", "application/octet-stream"),
            },
        )
        assert response.status_code == 400
        assert "could not be decoded" in response.json()["detail"]


@pytest.mark.integration
class TestAsyncAnalyze:
    """Fire-and-forget analysis routes that stream over WebSocket."""

    def test_start_returns_run_id_and_stores_result(self, client: TestClient) -> None:
        """Start returns run id and stores result."""
        response = client.post(
            "/v1/analyze/start",
            json={"content": "Only native English speakers need apply."},
        )
        assert response.status_code == 200
        run_id = response.json()["run_id"]
        assert response.json()["status"] == "started"

        _wait_for(lambda: app_state.analysis_results.get(run_id) is not None)
        stored = app_state.analysis_results[run_id]
        assert stored is not None
        assert stored.run_id == run_id
        assert stored.workflow_id == "bias_text"

    def test_upload_start(self, client: TestClient) -> None:
        """Upload start."""
        path = FIXTURES / "bias_text" / "gender_bias.txt"
        with path.open("rb") as fh:
            response = client.post(
                "/v1/analyze/upload/start",
                files={"file": (path.name, fh, "text/plain")},
            )
        assert response.status_code == 200
        run_id = response.json()["run_id"]
        _wait_for(lambda: app_state.analysis_results.get(run_id) is not None)


@pytest.mark.integration
class TestBatch:
    """Batch job submission and polling."""

    def test_batch_lifecycle(self, client: TestClient) -> None:
        """Batch lifecycle."""
        response = client.post(
            "/v1/batch",
            json={
                "items": [
                    {"content": "Looking for a digital native."},
                    {"content": "Hiring risk scenario", "input_type": "risk"},
                ],
            },
        )
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        assert response.json()["total"] == 2

        _wait_for(
            lambda: (
                client.get(f"/v1/batch/{job_id}").json()["status"]
                in {"completed", "failed"}
            ),
        )
        final = client.get(f"/v1/batch/{job_id}").json()
        assert final["status"] == "completed", final["errors"]
        assert final["completed"] == 2
        assert [r["workflow_id"] for r in final["results"]] == ["bias_text", "risk"]

    def test_empty_batch_rejected(self, client: TestClient) -> None:
        """Empty batch rejected."""
        assert client.post("/v1/batch", json={"items": []}).status_code == 422

    def test_unknown_job_404(self, client: TestClient) -> None:
        """Unknown job 404."""
        assert client.get("/v1/batch/does-not-exist").status_code == 404


@pytest.mark.integration
def test_stream_delivers_completion_event(client: TestClient) -> None:
    """Events published for a run_id are delivered over the WebSocket."""
    run_id = "ws-test-run"
    with client.websocket_connect(f"/v1/stream/{run_id}") as ws:
        payload = {"run_id": run_id, "event": "analysis_complete", "context": {}}
        loop = app_state.event_bus._loop
        assert loop is not None
        queue = app_state.event_bus._queues[run_id]
        loop.call_soon_threadsafe(app_state.event_bus._enqueue, queue, payload)
        received = ws.receive_json()
    assert received["event"] == "analysis_complete"
    assert received["run_id"] == run_id
