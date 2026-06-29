"""Task Takeover workflow graph construction.

This module builds the LangGraph StateGraph for the Task Takeover workflow.
"""

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from forge.workflow.nodes import (
    escalate_to_blocked,
    generate_plan,
    route_triage_gate,
    triage_gate,
    triage_task,
)
from forge.workflow.nodes.task_takeover_planning import plan_approval_gate, route_plan_approval
from forge.workflow.task_takeover.state import TaskTakeoverState
from forge.workflow.utils import resolve_shared_resume_node

logger = logging.getLogger(__name__)


def route_entry(state: TaskTakeoverState) -> str:
    """Route workflow based on current progress for resume/retry.

    New tickets start at triage_check. In-flight tickets with a saved current_node
    resume at the appropriate point.

    Args:
        state: Current workflow state.

    Returns:
        Next node name based on current progress.
    """
    current_node = state.get("current_node", "")

    if current_node and current_node not in ("entry", "route_entry", "__end__", "", "start"):
        logger.info(f"Resuming task takeover workflow at node: {current_node}")

        # Shared nodes: same resume mapping across all workflow types
        shared = resolve_shared_resume_node(current_node)
        if shared is not None:
            if shared is END:
                logger.info(f"Workflow at terminal state '{current_node}', returning END")
            return shared

        # Task takeover-specific resume mapping
        if current_node == "triage_check":
            return "triage_check"
        elif current_node == "triage_gate":
            return "triage_gate"
        elif current_node == "generate_plan":
            return "generate_plan"
        elif current_node == "plan_approval_gate":
            return "plan_approval_gate"
        elif current_node == "escalate_blocked":
            return "escalate_blocked"
        else:
            logger.warning(f"Unrecognized current_node '{current_node}', restarting from triage")

    # New tasks start at triage
    return "triage_check"


def _route_after_triage_check(state: TaskTakeoverState) -> str:
    """Route after triage_check based on what triage_check set as current_node."""
    node = state.get("current_node", "triage_gate")
    if node in ("analyze_bug", "generate_plan"):
        return "generate_plan"
    if node in ("triage_gate", "escalate_blocked"):
        return node
    return "triage_gate"


def build_task_takeover_graph() -> StateGraph[TaskTakeoverState, Any, Any]:
    """Create the Task Takeover workflow graph.

    Returns:
        Configured StateGraph ready for compilation.
    """
    graph = StateGraph(TaskTakeoverState)

    # Entry routing
    graph.add_node("route_entry", lambda state: state)

    # Nodes
    graph.add_node("triage_check", triage_task)
    graph.add_node("triage_gate", triage_gate)
    graph.add_node("generate_plan", generate_plan)
    graph.add_node("plan_approval_gate", plan_approval_gate)
    graph.add_node("escalate_blocked", escalate_to_blocked)

    # Set entry point
    graph.set_entry_point("route_entry")

    # Entry routing edges
    graph.add_conditional_edges(
        "route_entry",
        route_entry,
        {
            "triage_check": "triage_check",
            "triage_gate": "triage_gate",
            "generate_plan": "generate_plan",
            "plan_approval_gate": "plan_approval_gate",
            "escalate_blocked": "escalate_blocked",
            END: END,
        },
    )

    # Triage flow
    graph.add_conditional_edges(
        "triage_check",
        _route_after_triage_check,
        {
            "triage_gate": "triage_gate",
            "generate_plan": "generate_plan",
            "escalate_blocked": "escalate_blocked",
        },
    )
    graph.add_conditional_edges(
        "triage_gate",
        route_triage_gate,
        {
            END: END,
            "triage_check": "triage_check",
        },
    )

    # Planning flow
    graph.add_edge("generate_plan", "plan_approval_gate")
    graph.add_conditional_edges(
        "plan_approval_gate",
        route_plan_approval,
        {
            "generate_plan": "generate_plan",
            END: END,
        },
    )

    graph.add_edge("escalate_blocked", END)

    return graph
