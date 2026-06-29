"""Tests for WorkflowRouter."""

from langgraph.graph import StateGraph

from forge.models.workflow import TicketType
from forge.workflow.base import BaseState, BaseWorkflow


class MockWorkflow(BaseWorkflow):
    """Test workflow that matches Features."""

    name = "mock"
    description = "Mock workflow for testing"

    @property
    def state_schema(self) -> type:
        return BaseState

    def matches(self, ticket_type: TicketType, _labels: list[str], _event: dict) -> bool:
        return ticket_type == TicketType.FEATURE

    def build_graph(self) -> StateGraph:
        graph = StateGraph(BaseState)
        graph.add_node("start", lambda s: s)
        graph.set_entry_point("start")
        return graph


class MockBugWorkflow(BaseWorkflow):
    """Test workflow that matches Bugs."""

    name = "mock_bug"
    description = "Mock bug workflow for testing"

    @property
    def state_schema(self) -> type:
        return BaseState

    def matches(self, ticket_type: TicketType, _labels: list[str], _event: dict) -> bool:
        return ticket_type == TicketType.BUG

    def build_graph(self) -> StateGraph:
        graph = StateGraph(BaseState)
        graph.add_node("start", lambda s: s)
        graph.set_entry_point("start")
        return graph


class TestWorkflowRouter:
    """Tests for WorkflowRouter."""

    def test_register_workflow(self):
        """Can register a workflow class."""
        from forge.workflow.router import WorkflowRouter

        router = WorkflowRouter()
        router.register(MockWorkflow)

        assert len(router.list_workflows()) == 1

    def test_resolve_returns_matching_workflow(self):
        """Resolve returns workflow that matches ticket."""
        from forge.workflow.router import WorkflowRouter

        router = WorkflowRouter()
        router.register(MockWorkflow)
        router.register(MockBugWorkflow)

        workflow = router.resolve(
            ticket_type=TicketType.FEATURE,
            labels=[],
            event={},
        )

        assert workflow is not None
        assert workflow.name == "mock"

    def test_resolve_returns_none_when_no_match(self):
        """Resolve returns None when no workflow matches."""
        from forge.workflow.router import WorkflowRouter

        router = WorkflowRouter()
        router.register(MockWorkflow)

        workflow = router.resolve(
            ticket_type=TicketType.BUG,
            labels=[],
            event={},
        )

        assert workflow is None

    def test_resolve_first_match_wins(self):
        """First registered workflow that matches is returned."""
        from forge.workflow.router import WorkflowRouter

        class AnotherFeatureWorkflow(MockWorkflow):
            name = "another_feature"

        router = WorkflowRouter()
        router.register(MockWorkflow)
        router.register(AnotherFeatureWorkflow)

        workflow = router.resolve(
            ticket_type=TicketType.FEATURE,
            labels=[],
            event={},
        )

        assert workflow.name == "mock"

    def test_list_workflows(self):
        """List returns all registered workflows."""
        from forge.workflow.router import WorkflowRouter

        router = WorkflowRouter()
        router.register(MockWorkflow)
        router.register(MockBugWorkflow)

        workflows = router.list_workflows()

        assert len(workflows) == 2
        assert workflows[0]["name"] == "mock"
        assert workflows[1]["name"] == "mock_bug"

    def test_resolve_exact_matching_no_accidental_prefix_triggers(self):
        """Verify that prefix-based triggers do not resolve to TaskTakeoverWorkflow."""
        from forge.workflow.router import WorkflowRouter
        from forge.workflow.task_takeover import TaskTakeoverWorkflow

        router = WorkflowRouter()
        router.register(TaskTakeoverWorkflow)

        # Labels starting with triggers but are not exact matches should not resolve
        prefix_labels_cases = [
            ["forge:managed", "forge:task-takeover-fake"],
            ["forge:managed", "forge:managed:task-fake"],
            ["forge:managed", "forge:managed:task-takeover-fake"],
        ]

        for labels in prefix_labels_cases:
            workflow = router.resolve(
                ticket_type=TicketType.BUG,
                labels=labels,
                event={},
            )
            assert workflow is None, f"Accidentally resolved with prefix-trigger labels: {labels}"

        # An exact match still resolves correctly
        workflow = router.resolve(
            ticket_type=TicketType.BUG,
            labels=["forge:managed", "forge:task-takeover"],
            event={},
        )
        assert workflow is not None
        assert workflow.name == "task_takeover"
