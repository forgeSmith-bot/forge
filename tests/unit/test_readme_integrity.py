"""Test suite verifying README.md structure and content integrity."""

import os
from pathlib import Path


def test_readme_exists_and_contains_quickstart():
    # Find the repository root README.md
    readme_path = Path("/workspace/README.md")
    assert readme_path.exists(), "README.md does not exist at root"
    
    content = readme_path.read_text()
    
    # Assert presence of key quick start headings and instructions
    assert "## Quick Start" in content, "README is missing '## Quick Start' section"
    assert "### 1. Prerequisites" in content, "README is missing Prerequisites subsection"
    assert "### 2. Core Services" in content, "README is missing Core Services subsection"
    assert "### 3. Optional Observability Services" in content, "README is missing Optional Observability Services subsection"

def test_readme_contains_commands_and_paths():
    readme_path = Path("/workspace/README.md")
    content = readme_path.read_text()
    
    # Verify the specific files/paths mentioned in the implementation plan
    assert "devtools/docker-compose.dev.yml" in content, "README should mention the developer docker-compose file path"
    assert "redis" in content, "README should contain redis instructions"
    assert "prometheus" in content, "README should mention prometheus"
    assert "grafana" in content, "README should mention grafana"
    assert "LANGFUSE_PUBLIC_KEY" in content, "README should mention Langfuse configuration keys"
    assert "uv run uvicorn forge.main:app" in content, "README should specify the FastAPI startup command"
    assert "uv run forge worker" in content, "README should specify the worker startup command"
