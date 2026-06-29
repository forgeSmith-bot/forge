"""Unit tests for the qualitative review node in Task Takeover workflow."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.workflow.nodes.task_takeover_review import (
    _extract_acceptance_criteria,
    _parse_qualitative_review,
    run_qualitative_review,
)
from forge.workflow.task_takeover.state import (
    TaskTakeoverState,
    create_initial_task_takeover_state,
)


def make_task_state(**overrides: Any) -> TaskTakeoverState:
    """Create a TaskTakeoverState dict for review tests."""
    state = create_initial_task_takeover_state("TASK-101")
    state_dict = cast(dict[str, Any], state)
    state_dict.update(overrides)
    return cast(TaskTakeoverState, state_dict)


@pytest.fixture
def base_task_state() -> TaskTakeoverState:
    return make_task_state(
        workspace_path="/tmp/fake-workspace-review",
        current_repo="owner/repo",
        context={"branch_name": "task/TASK-101"},
    )


def _make_mock_jira(description: str = "Acceptance Criteria:\n- Foo\n- Bar") -> AsyncMock:
    jira = AsyncMock()
    issue = MagicMock()
    issue.summary = "Fix session timeout"
    issue.description = description
    issue.project_key = "TASK"
    jira.get_issue = AsyncMock(return_value=issue)
    jira.add_comment = AsyncMock()
    jira.close = AsyncMock()
    return jira


class TestExtractAcceptanceCriteria:
    """Tests for _extract_acceptance_criteria."""

    def test_extract_found(self) -> None:
        desc = "Some setup info.\nAcceptance Criteria:\n1. Must run fast.\n2. Must pass."
        criteria = _extract_acceptance_criteria(desc)
        assert criteria.startswith("Acceptance Criteria:")
        assert "Must pass." in criteria

    def test_extract_not_found(self) -> None:
        desc = "Plain description without the heading."
        criteria = _extract_acceptance_criteria(desc)
        assert criteria == desc

    def test_extract_empty(self) -> None:
        assert _extract_acceptance_criteria("") == "No description or acceptance criteria provided."


class TestParseQualitativeReview:
    """Tests for _parse_qualitative_review."""

    def test_parse_adequate(self) -> None:
        output = "verdict: adequate\nfeedback: All is well!"
        verdict, feedback = _parse_qualitative_review(output)
        assert verdict == "adequate"
        assert feedback == "All is well!"

    def test_parse_tests_incomplete(self) -> None:
        output = "verdict: tests_incomplete\nfeedback: Please add more tests."
        verdict, feedback = _parse_qualitative_review(output)
        assert verdict == "tests_incomplete"
        assert feedback == "Please add more tests."

    def test_parse_invalid_defaults_to_incomplete(self) -> None:
        output = "verdict: perfect\nfeedback: Outstanding."
        verdict, feedback = _parse_qualitative_review(output)
        assert verdict == "tests_incomplete"


class TestRunQualitativeReview:
    """Tests for run_qualitative_review node."""

    @pytest.mark.asyncio
    async def test_run_qualitative_review_success(self, base_task_state: TaskTakeoverState) -> None:
        mock_jira = _make_mock_jira()
        mock_agent = AsyncMock()
        mock_agent.run_task = AsyncMock(
            return_value="verdict: adequate\nfeedback: Brilliant changes."
        )

        with (
            patch("forge.workflow.nodes.task_takeover_review.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.task_takeover_review.GitOperations") as mock_git,
            patch("forge.workflow.nodes.task_takeover_review.ForgeAgent", return_value=mock_agent),
            patch("forge.workflow.nodes.task_takeover_review.post_status_comment"),
        ):
            mock_git_instance = MagicMock()
            mock_git_instance._run_git = MagicMock()
            mock_git_instance._run_git.return_value.returncode = 0
            mock_git_instance._run_git.return_value.stdout = "diff contents"
            mock_git.return_value = mock_git_instance

            result = await run_qualitative_review(base_task_state)

        assert result["review_verdict"] == "adequate"
        assert result["review_feedback"] == "Brilliant changes."
        assert result["qualitative_review_retry_count"] == 0
        assert result["qualitative_review_failed"] is False
        assert result["current_node"] == "qualitative_review"
        assert result["last_error"] is None

        # Verify read-only agent was invoked
        mock_agent.run_task.assert_called_once()
        _, kwargs = mock_agent.run_task.call_args
        assert kwargs["include_tools"] is False

    @pytest.mark.asyncio
    async def test_run_qualitative_review_tests_incomplete(
        self, base_task_state: TaskTakeoverState
    ) -> None:
        mock_jira = _make_mock_jira()
        mock_agent = AsyncMock()
        mock_agent.run_task = AsyncMock(
            return_value="verdict: tests_incomplete\nfeedback: Write more unit tests."
        )

        with (
            patch("forge.workflow.nodes.task_takeover_review.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.task_takeover_review.GitOperations") as mock_git,
            patch("forge.workflow.nodes.task_takeover_review.ForgeAgent", return_value=mock_agent),
            patch("forge.workflow.nodes.task_takeover_review.post_status_comment"),
        ):
            mock_git_instance = MagicMock()
            mock_git_instance._run_git = MagicMock()
            mock_git_instance._run_git.return_value.returncode = 0
            mock_git_instance._run_git.return_value.stdout = "diff contents"
            mock_git.return_value = mock_git_instance

            result = await run_qualitative_review(base_task_state)

        assert result["review_verdict"] == "tests_incomplete"
        assert result["review_feedback"] == "Write more unit tests."
        assert result["qualitative_review_retry_count"] == 1
        assert result["qualitative_review_failed"] is True
        assert result["current_node"] == "qualitative_review"
        assert result["last_error"] is None

    @pytest.mark.asyncio
    async def test_run_qualitative_review_missing_workspace(
        self, base_task_state: TaskTakeoverState
    ) -> None:
        base_task_state["workspace_path"] = None

        result = await run_qualitative_review(base_task_state)
        assert result["last_error"] == "Workspace not set up"
        assert result["current_node"] == "qualitative_review"

    @pytest.mark.asyncio
    async def test_run_qualitative_review_exception_handling(
        self, base_task_state: TaskTakeoverState
    ) -> None:
        mock_jira = _make_mock_jira()
        mock_jira.get_issue = AsyncMock(side_effect=RuntimeError("Jira connection failure"))

        with (
            patch("forge.workflow.nodes.task_takeover_review.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.error_handler.notify_error") as mock_notify,
        ):
            result = await run_qualitative_review(base_task_state)

        assert result["last_error"] is not None
        assert "Jira connection failure" in result["last_error"]
        assert result["current_node"] == "qualitative_review"
        mock_notify.assert_called_once()
