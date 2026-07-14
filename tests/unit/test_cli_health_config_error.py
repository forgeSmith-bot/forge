"""Unit tests for the CLI health command configuration error handling."""

import argparse
import json
from unittest.mock import patch

import pytest

from forge.cli import cmd_health


@pytest.mark.asyncio
async def test_health_config_error_json():
    """Verify that a configuration exception during get_settings outputs valid JSON structure with status unhealthy and exits with 1."""
    with patch("forge.cli.get_settings", side_effect=ValueError("Invalid config fields")):
        args = argparse.Namespace(json=True)
        with patch("sys.stdout.write") as mock_stdout_write:
            exit_code = await cmd_health(args)
            assert exit_code == 1
            written = "".join(call.args[0] for call in mock_stdout_write.call_args_list)
            data = json.loads(written)
            assert data["status"] == "unhealthy"
            assert data["error"] == "Configuration error"
            assert "Invalid config fields" in data["details"]


@pytest.mark.asyncio
async def test_health_config_error_text(capsys):
    """Verify that a configuration exception in text mode outputs cleanly to stderr and exits with 1."""
    with patch("forge.cli.get_settings", side_effect=ValueError("Invalid config fields")):
        args = argparse.Namespace(json=False)
        exit_code = await cmd_health(args)
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error: Configuration loading failed: Invalid config fields" in captured.err
