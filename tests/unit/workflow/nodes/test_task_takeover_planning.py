"""Unit tests for task takeover planning nodes."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.graph import END

from forge.models.workflow import ForgeLabel
from forge.workflow.nodes.task_takeover_planning import (
    generate_plan,
    plan_approval_gate,
    route_plan_approval,
)
from forge.workflow.task_takeover.state import (
    TaskTakeoverState,
    create_initial_task_takeover_state,
)
from forge.workflow.utils.repo_resolution import repo_from_labels, repo_mentioned_in_text


def make_task_state(**overrides: Any) -> TaskTakeoverState:
    """Create a TaskTakeoverState dict for planning tests."""
    state = create_initial_task_takeover_state("TASK-002")
    state_dict = cast(dict[str, Any], state)
    state_dict.update(overrides)
    return cast(TaskTakeoverState, state_dict)


@pytest.fixture
def base_task_state() -> TaskTakeoverState:
    return make_task_state()


def _make_mock_jira(summary="Implement user session logout", project_key="TASK", labels=None):
    jira = AsyncMock()
    issue = MagicMock()
    issue.summary = summary
    issue.description = "Task description"
    issue.project_key = project_key
    issue.labels = labels or []
    jira.get_issue = AsyncMock(return_value=issue)
    jira.get_comments = AsyncMock(return_value=[])
    jira.add_comment = AsyncMock()
    jira.set_workflow_label = AsyncMock()
    jira.get_project_default_repo = AsyncMock(return_value="owner/project")
    jira.get_project_repos = AsyncMock(return_value=["owner/project"])
    jira.close = AsyncMock()
    return jira


def _make_mock_agent_success(plan_content="## Plan\n\nTask Takeover Plan details."):
    agent = MagicMock()
    agent.run_task = AsyncMock(return_value=plan_content)
    agent.close = AsyncMock()
    return agent


def _make_mock_agent_failure():
    agent = MagicMock()
    agent.run_task = AsyncMock(side_effect=RuntimeError("Planning agent failed"))
    agent.close = AsyncMock()
    return agent


class TestRepoResolution:
    """Tests for standalone task target repository inference."""

    def test_repo_from_labels(self) -> None:
        assert repo_from_labels(["forge:managed", "repo:forge-sdlc/forge"]) == "forge-sdlc/forge"

    def test_repo_from_full_repo_mention(self) -> None:
        repos = ["openshift/installer", "forge-sdlc/forge"]
        text = "Update the configuration in forge-sdlc/forge."

        assert repo_mentioned_in_text(text, repos) == "forge-sdlc/forge"

    def test_repo_from_unambiguous_basename_mention(self) -> None:
        repos = ["openshift/installer", "forge-sdlc/forge"]
        text = "Forge should support opening generated pull requests as drafts."

        assert repo_mentioned_in_text(text, repos) == "forge-sdlc/forge"

    def test_ambiguous_basename_mention_is_ignored(self) -> None:
        repos = ["org/service", "other/service"]
        text = "Update service behavior."

        assert repo_mentioned_in_text(text, repos) is None


class TestGeneratePlan:
    """Tests for the generate_plan node."""

    @pytest.mark.asyncio
    async def test_generate_plan_success(self, base_task_state: TaskTakeoverState) -> None:
        """Verify successful generation of task takeover plan."""
        mock_jira = _make_mock_jira()
        agent = _make_mock_agent_success("## Plan\n\nTask Takeover Plan details.")

        with (
            patch("forge.workflow.nodes.task_takeover_planning.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.task_takeover_planning.ForgeAgent", return_value=agent),
            patch("forge.workflow.nodes.task_takeover_planning.GitOperations") as mock_git,
        ):
            mock_git_instance = MagicMock()
            mock_git_instance.clone = MagicMock()
            mock_git.return_value = mock_git_instance
            result = await generate_plan(base_task_state)

        assert result["plan_content"] == "## Plan\n\nTask Takeover Plan details."
        assert result["current_node"] == "task_plan_approval_gate"
        mock_jira.set_workflow_label.assert_called_once_with("TASK-002", ForgeLabel.PLAN_PENDING)
        assert mock_jira.add_comment.call_count == 2  # Ack comment + Plan comment
        agent.run_task.assert_awaited_once()
        assert agent.run_task.call_args.kwargs["task"] == "task-takeover-planning"

    @pytest.mark.asyncio
    async def test_generate_plan_uses_repo_mentioned_in_ticket(
        self, base_task_state: TaskTakeoverState, tmp_path
    ) -> None:
        """A standalone Forge task should use forge-sdlc/forge, not the first AISOS repo."""
        mock_jira = _make_mock_jira(
            summary="Forge: allow repository metadata to open PRs as drafts first",
            project_key="AISOS",
        )
        mock_jira.get_project_default_repo = AsyncMock(return_value="openshift/installer")
        mock_jira.get_project_repos = AsyncMock(
            return_value=["openshift/installer", "forge-sdlc/forge"]
        )

        agent = _make_mock_agent_success("## Plan\n\nTask Takeover Plan details.")
        workspace = MagicMock()
        workspace.path = tmp_path

        with (
            patch("forge.workflow.nodes.task_takeover_planning.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.task_takeover_planning.ForgeAgent", return_value=agent),
            patch("forge.workflow.nodes.task_takeover_planning.WorkspaceManager") as mock_manager,
            patch("forge.workflow.nodes.task_takeover_planning.GitOperations") as mock_git,
        ):
            mock_manager.return_value.create_workspace.return_value = workspace
            mock_git.return_value.clone = MagicMock()
            result = await generate_plan(base_task_state)

        assert result["current_repo"] == "forge-sdlc/forge"
        mock_manager.return_value.create_workspace.assert_called_once()
        assert mock_manager.return_value.create_workspace.call_args.kwargs["repo_name"] == "forge-sdlc/forge"

    @pytest.mark.asyncio
    async def test_generate_plan_with_truncation(self, base_task_state: TaskTakeoverState) -> None:
        """Verify plan comment is truncated if it exceeds maximum comment size."""
        mock_jira = _make_mock_jira()
        long_plan = "A" * 30_000
        agent = _make_mock_agent_success(long_plan)

        with (
            patch("forge.workflow.nodes.task_takeover_planning.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.task_takeover_planning.ForgeAgent", return_value=agent),
            patch("forge.workflow.nodes.task_takeover_planning.GitOperations") as mock_git,
        ):
            mock_git_instance = MagicMock()
            mock_git_instance.clone = MagicMock()
            mock_git.return_value = mock_git_instance
            await generate_plan(base_task_state)

        # Plan comment is the second comment
        plan_comment = mock_jira.add_comment.call_args_list[1].args[1]
        assert len(plan_comment) <= 25_500
        assert "truncated" in plan_comment.lower()

    @pytest.mark.asyncio
    async def test_generate_plan_failure_retries(self, base_task_state: TaskTakeoverState) -> None:
        """Verify planning agent failure increments retry_count and handles errors."""
        mock_jira = _make_mock_jira()
        agent = _make_mock_agent_failure()

        with (
            patch("forge.workflow.nodes.task_takeover_planning.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.task_takeover_planning.ForgeAgent", return_value=agent),
            patch("forge.workflow.nodes.task_takeover_planning.GitOperations") as mock_git,
        ):
            mock_git_instance = MagicMock()
            mock_git_instance.clone = MagicMock()
            mock_git.return_value = mock_git_instance
            result = await generate_plan(base_task_state)

        assert result["retry_count"] == 1
        assert result["last_error"] is not None
        assert result["current_node"] == "generate_plan"


class TestRegeneratePlanFlow:
    """Tests for the regeneration flow when a revision is requested."""

    @pytest.mark.asyncio
    async def test_regenerate_plan_with_feedback(self, base_task_state: TaskTakeoverState) -> None:
        """Verify regenerate plan with revision request and feedback details."""
        state = {
            **base_task_state,
            "revision_requested": True,
            "feedback_comment": "Please add more detailed logging.",
            "plan_content": "## Plan\n\nOld Plan content.",
        }

        mock_jira = _make_mock_jira()
        agent = _make_mock_agent_success("## Plan\n\nNew Plan content with logging.")

        with (
            patch("forge.workflow.nodes.task_takeover_planning.JiraClient", return_value=mock_jira),
            patch("forge.workflow.nodes.task_takeover_planning.ForgeAgent", return_value=agent),
            patch("forge.workflow.nodes.task_takeover_planning.GitOperations") as mock_git,
        ):
            mock_git_instance = MagicMock()
            mock_git_instance.clone = MagicMock()
            mock_git.return_value = mock_git_instance
            result = await generate_plan(state)

        assert result["plan_content"] == "## Plan\n\nNew Plan content with logging."
        assert result["revision_requested"] is False
        assert result["feedback_comment"] is None
        assert result["current_node"] == "task_plan_approval_gate"


class TestPlanApprovalGate:
    """Tests for plan_approval_gate node."""

    def test_plan_approval_gate_pauses(self, base_task_state: TaskTakeoverState) -> None:
        """Verify plan_approval_gate pauses the state."""
        result = plan_approval_gate(base_task_state)
        assert result["is_paused"] is True
        assert result["current_node"] == "plan_approval_gate"


class TestRoutePlanApproval:
    """Tests for route_plan_approval function."""

    def test_route_plan_approval_paused(self, base_task_state: TaskTakeoverState) -> None:
        """Verify it returns END when state is paused."""
        state = {**base_task_state, "is_paused": True}
        assert route_plan_approval(state) == END

    def test_route_plan_approval_revision_requested(
        self, base_task_state: TaskTakeoverState
    ) -> None:
        """Verify it returns generate_plan when revision is requested and is_paused is False."""
        state = {**base_task_state, "is_paused": False, "revision_requested": True}
        assert route_plan_approval(state) == "generate_plan"

    def test_route_plan_approval_approved(self, base_task_state: TaskTakeoverState) -> None:
        """Verify it returns END when plan is approved (no other flags)."""
        state = {**base_task_state, "is_paused": False}
        assert route_plan_approval(state) == END
