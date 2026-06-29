"""Workflow router for matching tickets to workflows."""

from typing import Any

from forge.models.workflow import TicketType
from forge.workflow.base import BaseWorkflow


class WorkflowRouter:
    """Routes incoming tickets to appropriate workflows."""

    def __init__(self) -> None:
        self._workflows: list[type[BaseWorkflow]] = []

    def register(self, workflow_class: type[BaseWorkflow]) -> None:
        """Register a workflow class. First match wins."""
        self._workflows.append(workflow_class)

    def resolve(
        self,
        ticket_type: TicketType,
        labels: list[str],
        event: dict[str, Any],
    ) -> BaseWorkflow | None:
        """Find the first matching workflow for given ticket/event."""
        for workflow_class in self._workflows:
            if workflow_class.name == "task_takeover":
                # Guarantee exact label matching for resolving triggers, avoiding any prefix-based triggers
                allowed_triggers = {
                    "forge:task-takeover",
                    "forge:managed:task",
                    "forge:managed:task-takeover",
                }
                try:
                    from forge.config import get_settings

                    settings = get_settings()
                    if (
                        settings.task_takeover
                        and settings.task_takeover.labels
                        and settings.task_takeover.labels.trigger
                    ):
                        allowed_triggers.add(settings.task_takeover.labels.trigger)
                except Exception:
                    pass

                # Filter out labels that start with trigger prefixes but are not exact matches
                cleaned_labels = []
                for label in labels:
                    is_prefix_trigger = False
                    for trigger_prefix in ["forge:task-takeover", "forge:managed:task"]:
                        if label.startswith(trigger_prefix) and label not in allowed_triggers:
                            is_prefix_trigger = True
                            break
                    if not is_prefix_trigger:
                        cleaned_labels.append(label)

                instance = workflow_class()
                if instance.matches(ticket_type, cleaned_labels, event):
                    return instance
                continue

            instance = workflow_class()
            if instance.matches(ticket_type, labels, event):
                return instance
        return None

    def list_workflows(self) -> list[dict[str, str]]:
        """List all registered workflows (for health/debug endpoints)."""
        return [{"name": wf.name, "description": wf.description} for wf in self._workflows]
