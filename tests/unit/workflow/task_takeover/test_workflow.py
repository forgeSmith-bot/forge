"""Tests for TaskTakeoverWorkflow."""

from unittest.mock import patch

import pytest
from langgraph.graph import StateGraph

from forge.models.workflow import TicketType
from forge.workflow.task_takeover import TaskTakeoverWorkflow
from forge.workflow.task_takeover.state import TaskTakeoverState


class TestTaskTakeoverWorkflow:
    """Tests for TaskTakeoverWorkflow class."""

    @pytest.fixture(autouse=True)
    def mock_settings(self):
        """Mock settings to enable task takeover."""
        from forge.config import Settings, TaskTakeoverSettings

        mock_s = Settings()
        mock_s.task_takeover = TaskTakeoverSettings(enabled=True)

        with patch("forge.config.get_settings", return_value=mock_s):
            yield

    def test_workflow_has_name(self):
        """TaskTakeoverWorkflow has name attribute."""
        workflow = TaskTakeoverWorkflow()
        assert workflow.name == "task_takeover"

    def test_workflow_has_description(self):
        """TaskTakeoverWorkflow has description."""
        workflow = TaskTakeoverWorkflow()
        assert workflow.description == "Task Takeover workflow"

    def test_state_schema_returns_task_takeover_state(self):
        """state_schema returns TaskTakeoverState."""
        workflow = TaskTakeoverWorkflow()
        assert workflow.state_schema is TaskTakeoverState

    def test_build_graph_returns_state_graph(self):
        """build_graph returns a StateGraph."""
        workflow = TaskTakeoverWorkflow()
        graph = workflow.build_graph()
        assert isinstance(graph, StateGraph)

    def test_create_initial_state(self):
        """create_initial_state returns TaskTakeoverState with defaults."""
        workflow = TaskTakeoverWorkflow()
        state = workflow.create_initial_state("TASK-123")

        assert state["ticket_key"] == "TASK-123"
        assert state["ticket_type"] == TicketType.TASK
        assert state["current_node"] == "start"

    def test_matches_strictly_when_both_managed_and_trigger_present(self):
        """matches returns True when forge:managed and exact trigger are present."""
        workflow = TaskTakeoverWorkflow()

        # Exact trigger "forge:task-takeover"
        assert (
            workflow.matches(TicketType.TASK, ["forge:managed", "forge:task-takeover"], {}) is True
        )

        # Exact trigger "forge:managed:task"
        assert (
            workflow.matches(TicketType.TASK, ["forge:managed", "forge:managed:task"], {}) is True
        )

        # Exact trigger "forge:managed:task-takeover"
        assert (
            workflow.matches(TicketType.TASK, ["forge:managed", "forge:managed:task-takeover"], {})
            is True
        )

    def test_matches_returns_false_when_only_managed_present(self):
        """matches returns False when only forge:managed is present without trigger."""
        workflow = TaskTakeoverWorkflow()
        assert workflow.matches(TicketType.TASK, ["forge:managed"], {}) is False
        assert (
            workflow.matches(TicketType.TASK, ["forge:managed", "forge:prd-drafting"], {}) is False
        )

    def test_matches_returns_true_when_only_trigger_present_without_managed(self):
        """matches returns True when trigger label is present even if forge:managed is missing."""
        workflow = TaskTakeoverWorkflow()
        assert workflow.matches(TicketType.TASK, ["forge:task-takeover"], {}) is True
        assert workflow.matches(TicketType.TASK, ["forge:managed:task"], {}) is True
        assert workflow.matches(TicketType.TASK, ["forge:managed:task-takeover"], {}) is True

    def test_matches_returns_false_with_non_trigger_labels(self):
        """matches returns False if no exact trigger label is present."""
        workflow = TaskTakeoverWorkflow()
        assert workflow.matches(TicketType.TASK, ["forge:managed-something"], {}) is False
        assert workflow.matches(TicketType.TASK, ["other-label"], {}) is False
