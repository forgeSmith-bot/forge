"""Task Takeover workflow implementation."""

from typing import Any, cast

from langgraph.graph import StateGraph

from forge.models.workflow import TicketType
from forge.workflow.base import BaseWorkflow
from forge.workflow.task_takeover.state import (
    TaskTakeoverState,
    create_initial_task_takeover_state,
)


class TaskTakeoverWorkflow(BaseWorkflow):
    """Workflow for Task Takeover tickets."""

    name = "task_takeover"
    description = "Task Takeover workflow"

    @property
    def state_schema(self) -> type:
        return TaskTakeoverState

    def matches(self, _ticket_type: TicketType, labels: list[str], _event: dict[str, Any]) -> bool:
        """Return True only if task_takeover is enabled and any exact task-takeover trigger is present."""
        try:
            from forge.config import get_settings

            settings = get_settings()
            if not settings.task_takeover or not settings.task_takeover.enabled:
                return False
        except Exception:
            return False

        # Define the exact trigger labels
        trigger_labels = {
            "forge:task-takeover",
            "forge:managed:task",
            "forge:managed:task-takeover",
        }

        # Include custom trigger from settings if available
        if (
            settings.task_takeover
            and settings.task_takeover.labels
            and settings.task_takeover.labels.trigger
        ):
            trigger_labels.add(settings.task_takeover.labels.trigger)

        # Check if any exact trigger label is present in the labels list
        return any(label in labels for label in trigger_labels)

    def build_graph(self) -> StateGraph[Any]:
        """Construct the LangGraph StateGraph for Task Takeover."""
        from forge.workflow.task_takeover.graph import build_task_takeover_graph

        return build_task_takeover_graph()

    def create_initial_state(self, ticket_key: str, **kwargs: Any) -> dict[str, Any]:
        """Create initial state for a new Task Takeover workflow run."""
        return cast(dict[str, Any], create_initial_task_takeover_state(ticket_key, **kwargs))


__all__ = ["TaskTakeoverWorkflow", "TaskTakeoverState", "create_initial_task_takeover_state"]
