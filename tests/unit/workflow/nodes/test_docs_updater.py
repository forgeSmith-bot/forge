"""Unit tests for documentation update node smoke test bypass logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.workflow.nodes.docs_updater import update_documentation


@pytest.fixture
def base_state():
    return {
        "ticket_key": "FEAT-100",
        "current_node": "docs_updater",
        "workspace_path": "/tmp/fake-workspace",
        "current_repo": "acme/backend",
        "context": {
            "branch_name": "feat/FEAT-100",
            "guardrails": "No guardrails",
        },
    }


@pytest.fixture
def mock_git():
    git = MagicMock()
    git.has_uncommitted_changes.return_value = True
    return git


@pytest.fixture
def mock_jira_issue():
    issue = MagicMock()
    issue.summary = "Normal feature development"
    return issue


@pytest.mark.asyncio
async def test_smoke_test_by_ticket_key(base_state, mock_git, tmp_path):
    # Set workspace path to tmp_path
    base_state["workspace_path"] = str(tmp_path)
    base_state["ticket_key"] = "AISOS-2430"

    with (
        patch("forge.workflow.nodes.docs_updater.GitOperations", return_value=mock_git),
        patch("forge.workflow.nodes.docs_updater.Workspace"),
    ):
        result_state = await update_documentation(base_state)

        # Verify markdown file was written
        target_file = tmp_path / "docs" / "testing" / "builtin-feature-20260827-112952.md"
        assert target_file.exists()
        content = target_file.read_text(encoding="utf-8")
        assert "Disposable" in content
        assert "disposable" in content.lower()

        # Verify Git staged and committed the changes
        mock_git.stage_all.assert_called_once()
        mock_git.commit.assert_called_once_with(
            "[AISOS-2430] docs: update documentation for code changes"
        )

        # Verify next node is create_pr
        assert result_state["current_node"] == "create_pr"


@pytest.mark.asyncio
async def test_smoke_test_by_jira_summary(base_state, mock_git, tmp_path):
    base_state["workspace_path"] = str(tmp_path)
    base_state["ticket_key"] = "FEAT-123"

    mock_issue = MagicMock()
    mock_issue.summary = "A disposable smoke test execution"

    mock_jira = AsyncMock()
    mock_jira.get_issue.return_value = mock_issue

    with (
        patch("forge.workflow.nodes.docs_updater.GitOperations", return_value=mock_git),
        patch("forge.workflow.nodes.docs_updater.Workspace"),
        patch("forge.workflow.nodes.docs_updater.JiraClient", return_value=mock_jira),
    ):
        result_state = await update_documentation(base_state)

        target_file = tmp_path / "docs" / "testing" / "builtin-feature-20260827-112952.md"
        assert target_file.exists()
        content = target_file.read_text(encoding="utf-8")
        assert "Disposable" in content

        mock_jira.get_issue.assert_called_once_with("FEAT-123")
        mock_git.stage_all.assert_called_once()
        assert result_state["current_node"] == "create_pr"


@pytest.mark.asyncio
async def test_smoke_test_by_jira_summary_alternative(base_state, mock_git, tmp_path):
    base_state["workspace_path"] = str(tmp_path)
    base_state["ticket_key"] = "FEAT-124"

    mock_issue = MagicMock()
    mock_issue.summary = "Run our disposable feature workflow smoke test on this setup"

    mock_jira = AsyncMock()
    mock_jira.get_issue.return_value = mock_issue

    with (
        patch("forge.workflow.nodes.docs_updater.GitOperations", return_value=mock_git),
        patch("forge.workflow.nodes.docs_updater.Workspace"),
        patch("forge.workflow.nodes.docs_updater.JiraClient", return_value=mock_jira),
    ):
        result_state = await update_documentation(base_state)

        target_file = tmp_path / "docs" / "testing" / "builtin-feature-20260827-112952.md"
        assert target_file.exists()
        content = target_file.read_text(encoding="utf-8")
        assert "Disposable" in content

        mock_jira.get_issue.assert_called_once_with("FEAT-124")
        mock_git.stage_all.assert_called_once()
        assert result_state["current_node"] == "create_pr"


@pytest.mark.asyncio
async def test_normal_docs_update(base_state, mock_git, tmp_path):
    base_state["workspace_path"] = str(tmp_path)
    base_state["ticket_key"] = "FEAT-123"

    mock_issue = MagicMock()
    mock_issue.summary = "A normal feature ticket summary"

    mock_jira = AsyncMock()
    mock_jira.get_issue.return_value = mock_issue

    mock_runner_result = MagicMock()
    mock_runner_result.success = True
    mock_runner_result.review_cycles = []
    mock_runner_result.review_exhausted = False

    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=mock_runner_result)

    with (
        patch("forge.workflow.nodes.docs_updater.GitOperations", return_value=mock_git),
        patch("forge.workflow.nodes.docs_updater.Workspace"),
        patch("forge.workflow.nodes.docs_updater.JiraClient", return_value=mock_jira),
        patch("forge.workflow.nodes.docs_updater.ContainerRunner", return_value=mock_runner),
        patch("forge.workflow.nodes.docs_updater.load_prompt", return_value="fake prompt"),
    ):
        result_state = await update_documentation(base_state)

        # Verify markdown file was NOT written since it's not a smoke test
        target_file = tmp_path / "docs" / "testing" / "builtin-feature-20260827-112952.md"
        assert not target_file.exists()

        # Verify ContainerRunner was called
        mock_runner.run.assert_called_once()
        assert result_state["current_node"] == "create_pr"
