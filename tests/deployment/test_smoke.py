import os
import time
import uuid

import httpx
import pytest


URL = os.environ.get("AGENT_SERVER_URL", "http://127.0.0.1:8123").rstrip("/")
RESTART_THREAD_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "bmad-ci-restart-test"))
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DEPLOYMENT_TESTS") != "1",
    reason="Set RUN_DEPLOYMENT_TESTS=1 with a running Agent Server",
)


@pytest.fixture
def client():
    deadline = time.monotonic() + 150
    last_error = "Server did not start"
    with httpx.Client(base_url=URL, timeout=30) as session:
        while time.monotonic() < deadline:
            try:
                response = session.get("/ok", timeout=2)
                if response.status_code == 200 and response.json().get("ok") is True:
                    yield session
                    return
                last_error = f"/ok returned {response.status_code}: {response.text[:200]}"
            except (httpx.HTTPError, ValueError) as exc:
                last_error = str(exc)
            time.sleep(2)
    pytest.fail(f"Agent Server health check failed: {last_error}")


def post(client, path, payload):
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def new_thread(client):
    return post(client, "/threads", {})["thread_id"]


def run(client, thread_id, content):
    return post(client, f"/threads/{thread_id}/runs/wait", {
        "assistant_id": "bmad_agent",
        "input": {"messages": [{"role": "user", "content": content}]},
    })


def test_agent_server_health_and_registration(client):
    assistants = post(client, "/assistants/search", {"limit": 100})
    assert "bmad_agent" in [assistant["graph_id"] for assistant in assistants]


def test_multi_turn_persistence_and_isolation(client):
    thread_id = new_thread(client)
    try:
        first = run(client, thread_id, "Hello")
        assert len(first["messages"]) == 2
        second = run(client, thread_id, "Another task")
        assert len(second["messages"]) == 4
        assert second["artifacts"].count("Task step executed") == 2
    finally:
        client.delete(f"/threads/{thread_id}").raise_for_status()


@pytest.mark.parametrize("approved", [True, False])
def test_native_interrupt_resume(client, approved):
    thread_id = new_thread(client)
    try:
        paused = run(client, thread_id, "A critical operation")
        assert "Task step executed" not in paused["artifacts"]
        state = client.get(f"/threads/{thread_id}/state")
        state.raise_for_status()
        assert state.json()["next"] == ["human_approval"]
        result = post(client, f"/threads/{thread_id}/runs/wait", {
            "assistant_id": "bmad_agent",
            "command": {"resume": {"approved": approved}},
        })
        assert ("Task step executed" in result["artifacts"]) is approved
    finally:
        client.delete(f"/threads/{thread_id}").raise_for_status()


def test_execution_stream(client):
    thread_id = new_thread(client)
    try:
        with client.stream("POST", f"/threads/{thread_id}/runs/stream", json={
            "assistant_id": "bmad_agent",
            "input": {"messages": [{"role": "user", "content": "Stream this task"}]},
            "stream_mode": ["updates"],
        }) as response:
            response.raise_for_status()
            stream = list(response.iter_lines())
        assert any(line.startswith("event: updates") for line in stream)
        assert any("Task step executed" in line for line in stream)
    finally:
        client.delete(f"/threads/{thread_id}").raise_for_status()


def test_persistence_across_restart(client):
    if os.environ.get("VERIFY_RESTART") == "1":
        try:
            response = client.get(f"/threads/{RESTART_THREAD_ID}/state")
            response.raise_for_status()
            assert response.json()["values"]["messages"][0]["content"] == "Persist me"
            result = run(client, RESTART_THREAD_ID, "After restart")
            assert len(result["messages"]) == 4
        finally:
            client.delete(f"/threads/{RESTART_THREAD_ID}").raise_for_status()
    else:
        post(client, "/threads", {
            "thread_id": RESTART_THREAD_ID, "if_exists": "do_nothing",
        })
        result = run(client, RESTART_THREAD_ID, "Persist me")
        assert len(result["messages"]) == 2
