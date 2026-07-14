"""Unit tests for the CLI health command."""

import argparse
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.cli import cmd_health
from forge.config import Settings


@pytest.mark.asyncio
async def test_health_configured_vertex_ai():
    """Verify that a correctly configured Vertex AI environment outputs healthy status and correct parameters."""
    test_settings = Settings(
        redis_url="redis://localhost:6379/0",
        jira_base_url="https://test.atlassian.net",
        jira_api_token="test-token",
        jira_user_email="test@example.com",
        github_token="test-github-token",
        anthropic_vertex_project_id="test-project",
        anthropic_vertex_region="us-central1",
        anthropic_api_key="",
        llm_model="claude-sonnet-4-5@20250929",
    )

    mock_redis_client = MagicMock()
    mock_redis_client.ping = AsyncMock(return_value=True)

    with (
        patch("forge.cli.get_settings", return_value=test_settings),
        patch("forge.orchestrator.checkpointer.get_redis_client", return_value=mock_redis_client),
        patch("sys.stdout.write") as mock_stdout_write,
    ):
        args = argparse.Namespace(json=True)
        exit_code = await cmd_health(args)

        assert exit_code == 0
        written = "".join(call.args[0] for call in mock_stdout_write.call_args_list)
        data = json.loads(written)

        assert data["status"] == "healthy"
        assert data["redis"]["status"] == "connected"
        assert data["llm"]["backend"] == "vertex-ai"
        assert data["llm"]["vertex_project"] == "test-project"
        assert data["llm"]["vertex_location"] == "us-central1"


@pytest.mark.asyncio
async def test_health_missing_vertex_project():
    """Verify that an environment with Vertex AI backend but missing project returns warning."""
    test_settings = Settings(
        redis_url="redis://localhost:6379/0",
        jira_base_url="https://test.atlassian.net",
        jira_api_token="test-token",
        jira_user_email="test@example.com",
        github_token="test-github-token",
        anthropic_vertex_project_id="",
        anthropic_vertex_region="us-central1",
        anthropic_api_key="",
        llm_model="claude-sonnet-4-5@20250929",
    )

    mock_redis_client = MagicMock()
    mock_redis_client.ping = AsyncMock(return_value=True)

    with (
        patch("forge.cli.get_settings", return_value=test_settings),
        patch("forge.orchestrator.checkpointer.get_redis_client", return_value=mock_redis_client),
        patch("sys.stdout.write") as mock_stdout_write,
    ):
        args = argparse.Namespace(json=True)
        exit_code = await cmd_health(args)

        assert exit_code == 0  # Should be 0 since warning, not unhealthy
        written = "".join(call.args[0] for call in mock_stdout_write.call_args_list)
        data = json.loads(written)

        assert data["status"] == "warning"
        assert data["llm"]["backend"] == "vertex-ai"
        assert data["llm"]["vertex_project"] is None


@pytest.mark.asyncio
async def test_health_gemini_api():
    """Verify that Google GenAI / Gemini configuration works and outputs healthy status."""
    test_settings = Settings(
        redis_url="redis://localhost:6379/0",
        jira_base_url="https://test.atlassian.net",
        jira_api_token="test-token",
        jira_user_email="test@example.com",
        github_token="test-github-token",
        google_api_key="valid-key",
        llm_model="gemini-2.5-pro",
        anthropic_api_key="",
    )

    mock_redis_client = MagicMock()
    mock_redis_client.ping = AsyncMock(return_value=True)

    with (
        patch("forge.cli.get_settings", return_value=test_settings),
        patch("forge.orchestrator.checkpointer.get_redis_client", return_value=mock_redis_client),
        patch("sys.stdout.write") as mock_stdout_write,
    ):
        args = argparse.Namespace(json=True)
        exit_code = await cmd_health(args)

        assert exit_code == 0
        written = "".join(call.args[0] for call in mock_stdout_write.call_args_list)
        data = json.loads(written)

        assert data["status"] == "healthy"
        assert data["llm"]["backend"] == "google-genai"


@pytest.mark.asyncio
async def test_health_anthropic_api():
    """Verify that Anthropic API configuration works and outputs healthy status."""
    test_settings = Settings(
        redis_url="redis://localhost:6379/0",
        jira_base_url="https://test.atlassian.net",
        jira_api_token="test-token",
        jira_user_email="test@example.com",
        github_token="test-github-token",
        anthropic_api_key="valid-key",
        llm_model="claude-sonnet-4-5@20250929",
    )

    mock_redis_client = MagicMock()
    mock_redis_client.ping = AsyncMock(return_value=True)

    with (
        patch("forge.cli.get_settings", return_value=test_settings),
        patch("forge.orchestrator.checkpointer.get_redis_client", return_value=mock_redis_client),
        patch("sys.stdout.write") as mock_stdout_write,
    ):
        args = argparse.Namespace(json=True)
        exit_code = await cmd_health(args)

        assert exit_code == 0
        written = "".join(call.args[0] for call in mock_stdout_write.call_args_list)
        data = json.loads(written)

        assert data["status"] == "healthy"
        assert data["llm"]["backend"] == "anthropic"


@pytest.mark.asyncio
async def test_health_redis_failure():
    """Verify that a Redis connection failure outputs disconnected and unhealthy status with exit code 1."""
    test_settings = Settings(
        redis_url="redis://localhost:6379/0",
        jira_base_url="https://test.atlassian.net",
        jira_api_token="test-token",
        jira_user_email="test@example.com",
        github_token="test-github-token",
        anthropic_api_key="valid-key",
        llm_model="claude-sonnet-4-5@20250929",
    )

    mock_redis_client = MagicMock()
    mock_redis_client.ping = AsyncMock(side_effect=Exception("Redis connection timed out"))

    with (
        patch("forge.cli.get_settings", return_value=test_settings),
        patch("forge.orchestrator.checkpointer.get_redis_client", return_value=mock_redis_client),
        patch("sys.stdout.write") as mock_stdout_write,
    ):
        args = argparse.Namespace(json=True)
        exit_code = await cmd_health(args)

        assert exit_code == 1
        written = "".join(call.args[0] for call in mock_stdout_write.call_args_list)
        data = json.loads(written)

        assert data["status"] == "unhealthy"
        assert data["redis"]["status"] == "disconnected"
        assert "Redis connection timed out" in data["redis"]["error"]


@pytest.mark.asyncio
async def test_health_secret_exclusion(capsys):
    """Ensure that secrets never appear in raw outputs in both JSON and text mode."""
    secret_token = "ultra-secret-token-123456"
    test_settings = Settings(
        redis_url="redis://localhost:6379/0",
        jira_base_url="https://test.atlassian.net",
        jira_api_token=secret_token,
        jira_user_email="test@example.com",
        github_token=secret_token,
        anthropic_api_key=secret_token,
        google_api_key=secret_token,
        llm_model="claude-sonnet-4-5@20250929",
    )

    mock_redis_client = MagicMock()
    mock_redis_client.ping = AsyncMock(return_value=True)

    # 1. Test JSON Mode
    with (
        patch("forge.cli.get_settings", return_value=test_settings),
        patch("forge.orchestrator.checkpointer.get_redis_client", return_value=mock_redis_client),
        patch("sys.stdout.write") as mock_stdout_write,
    ):
        args = argparse.Namespace(json=True)
        await cmd_health(args)
        written = "".join(call.args[0] for call in mock_stdout_write.call_args_list)
        assert secret_token not in written

    # 2. Test Text Mode
    with (
        patch("forge.cli.get_settings", return_value=test_settings),
        patch("forge.orchestrator.checkpointer.get_redis_client", return_value=mock_redis_client),
    ):
        args = argparse.Namespace(json=False)
        await cmd_health(args)
        captured = capsys.readouterr()
        assert secret_token not in captured.out
        assert secret_token not in captured.err
