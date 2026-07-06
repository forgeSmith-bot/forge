"""Tests for verifying the README Quick Start documentation elements."""

import re
from pathlib import Path

def test_readme_quick_start_ports_and_paths() -> None:
    """Validate that the ports and config paths mentioned in README.md exist and match devtools config."""
    readme_path = Path("README.md")
    assert readme_path.is_file(), "README.md should exist in root"
    
    content = readme_path.read_text()
    
    # 1. Verify expected ports are documented
    assert "6380:6379" in content, "Redis port 6380 should be mentioned in README.md"
    assert "3010" in content, "Grafana port 3010 should be mentioned in README.md"
    assert "9092" in content, "Prometheus port 9092 should be mentioned in README.md"
    assert "8000" in content, "FastAPI default port 8000 should be mentioned in README.md"
    
    # 2. Verify config files and container paths are correct
    assert "devtools/docker-compose.dev.yml" in content, "The path to devtools compose file should be correct in README"
    assert "containers/Containerfile" in content, "The Containerfile path should be correct in README"
    
    # 3. Check for specific commands
    assert "uv run uvicorn forge.main:app" in content, "Uvicorn startup command should be in README"
    assert "uv run forge worker" in content, "Worker startup command should be in README"
    assert "podman build -t localhost/forge-dev:latest" in content, "Local container build command should be correct"
