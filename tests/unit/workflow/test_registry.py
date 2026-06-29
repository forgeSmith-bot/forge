"""Tests for workflow registry."""

from forge.models.workflow import TicketType


class TestDefaultRouter:
    """Tests for create_default_router."""

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
