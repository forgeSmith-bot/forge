"""Tests for workflow registry."""

from unittest.mock import patch

import pytest

from forge.models.workflow import TicketType


class TestDefaultRouter:
    """Tests for create_default_router."""

    @pytest.fixture(autouse=True)
    def mock_settings(self):
        """Mock settings to enable task takeover."""
        from forge.config import Settings, TaskTakeoverSettings

        mock_s = Settings()
        mock_s.task_takeover = TaskTakeoverSettings(enabled=True)

        with patch("forge.config.get_settings", return_value=mock_s):
            yield

    def test_creates_router_with_workflows(self):
        """create_default_router returns router with workflows."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()
        workflows = router.list_workflows()

        assert len(workflows) >= 3

    def test_resolves_feature_to_feature_workflow(self):
        """Feature tickets resolve to FeatureWorkflow."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()
        workflow = router.resolve(TicketType.FEATURE, [], {})

        assert workflow is not None
        assert workflow.name == "feature"

    def test_resolves_bug_to_bug_workflow(self):
        """Bug tickets resolve to BugWorkflow."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()
        workflow = router.resolve(TicketType.BUG, [], {})

        assert workflow is not None
        assert workflow.name == "bug"

    def test_resolves_to_task_takeover_workflow_with_trigger_labels(self):
        """Tickets with forge:managed and task takeover trigger labels resolve to TaskTakeoverWorkflow."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()

        # Feature ticket with task takeover triggers
        workflow = router.resolve(
            TicketType.FEATURE,
            ["forge:managed", "forge:task-takeover"],
            {},
        )
        assert workflow is not None
        assert workflow.name == "task_takeover"

        # Bug ticket with task takeover triggers
        workflow = router.resolve(
            TicketType.BUG,
            ["forge:managed", "forge:managed:task-takeover"],
            {},
        )
        assert workflow is not None
        assert workflow.name == "task_takeover"

        # Standalone task ticket with takeover triggers
        workflow = router.resolve(
            TicketType.TASK,
            ["forge:managed", "forge:managed:task"],
            {},
        )
        assert workflow is not None
        assert workflow.name == "task_takeover"

    def test_resolves_to_general_workflow_without_trigger_labels(self):
        """Tickets with forge:managed but without task takeover trigger labels resolve to general workflows."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()

        # Feature ticket without task takeover triggers
        workflow = router.resolve(
            TicketType.FEATURE,
            ["forge:managed"],
            {},
        )
        assert workflow is not None
        assert workflow.name == "feature"

        # Bug ticket without task takeover triggers
        workflow = router.resolve(
            TicketType.BUG,
            ["forge:managed"],
            {},
        )
        assert workflow is not None
        assert workflow.name == "bug"

    def test_task_takeover_has_priority_over_bug_workflow(self):
        """Conflicting labels (e.g. both forge:managed:bug and forge:managed:task) prioritize Task Takeover routing."""
        from forge.workflow.registry import create_default_router

        router = create_default_router()

        # A Bug ticket with both forge:managed and forge:managed:task should resolve to TaskTakeoverWorkflow, not BugWorkflow
        workflow = router.resolve(
            TicketType.BUG,
            ["forge:managed", "forge:managed:task"],
            {},
        )
        assert workflow is not None
        assert workflow.name == "task_takeover"
