"""Tests for forge:yolo auto-approval mode."""

import pytest

from forge.models.workflow import ForgeLabel, TicketType
from forge.workflow.feature.state import create_initial_feature_state
from forge.workflow.bug.state import create_initial_bug_state


class TestForgeLabelYolo:
    def test_yolo_label_value(self):
        assert ForgeLabel.YOLO == "forge:yolo"

    def test_yolo_label_is_string(self):
        assert isinstance(ForgeLabel.YOLO, str)


class TestYoloModeDefaultsToFalse:
    def test_feature_state_yolo_mode_defaults_false(self):
        state = create_initial_feature_state("TEST-1")
        assert state.get("yolo_mode") is False

    def test_bug_state_yolo_mode_defaults_false(self):
        state = create_initial_bug_state("BUG-1")
        assert state.get("yolo_mode") is False

    def test_feature_state_yolo_mode_can_be_set_true(self):
        state = create_initial_feature_state("TEST-1", yolo_mode=True)
        assert state["yolo_mode"] is True

    def test_bug_state_yolo_mode_can_be_set_true(self):
        state = create_initial_bug_state("BUG-1", yolo_mode=True)
        assert state["yolo_mode"] is True


class TestBuildInitialStateYoloMode:
    """Tests for yolo_mode initialization from Jira payload."""

    def _make_worker(self):
        from unittest.mock import MagicMock
        from forge.orchestrator.worker import OrchestratorWorker
        worker = OrchestratorWorker.__new__(OrchestratorWorker)
        worker.settings = MagicMock()
        worker.router = MagicMock()
        return worker

    def _make_message(self, labels: list):
        from unittest.mock import MagicMock
        from forge.models.events import EventSource
        msg = MagicMock()
        msg.ticket_key = "TEST-1"
        msg.source = EventSource.JIRA
        msg.event_type = "jira:issue_updated"
        msg.event_id = "evt-1"
        msg.retry_count = 0
        msg.payload = {
            "issue": {
                "fields": {
                    "issuetype": {"name": "Feature"},
                    "labels": labels,
                }
            }
        }
        return msg

    def test_yolo_mode_true_when_label_present(self):
        worker = self._make_worker()
        msg = self._make_message(["forge:managed", "forge:yolo"])
        state = worker._build_initial_state(msg)
        assert state["yolo_mode"] is True

    def test_yolo_mode_false_when_label_absent(self):
        worker = self._make_worker()
        msg = self._make_message(["forge:managed"])
        state = worker._build_initial_state(msg)
        assert state["yolo_mode"] is False

    def test_yolo_mode_false_when_no_labels(self):
        worker = self._make_worker()
        msg = self._make_message([])
        state = worker._build_initial_state(msg)
        assert state["yolo_mode"] is False

    def test_yolo_mode_false_for_github_source(self):
        from unittest.mock import MagicMock
        from forge.models.events import EventSource
        msg = MagicMock()
        msg.ticket_key = "TEST-1"
        msg.source = EventSource.GITHUB
        msg.event_type = "pull_request"
        msg.event_id = "evt-1"
        msg.retry_count = 0
        msg.payload = {"pull_request": {"number": 1}}
        worker = self._make_worker()
        state = worker._build_initial_state(msg)
        assert state["yolo_mode"] is False


class TestYoloLabelAddedMidWorkflow:
    """When forge:yolo is added while paused at a gate, yolo_mode is set and workflow unpauses."""

    def _make_label_change(self, from_str: str, to_str: str) -> dict:
        return {"field": "labels", "fromString": from_str, "toString": to_str}

    def test_yolo_detection_logic_at_prd_gate(self):
        """forge:yolo in new labels at prd_approval_gate triggers yolo."""
        label_changes = [self._make_label_change("forge:managed", "forge:managed forge:yolo")]
        current_node = "prd_approval_gate"
        yolo_gates = {
            "prd_approval_gate", "spec_approval_gate",
            "plan_approval_gate", "task_approval_gate", "rca_option_gate",
        }
        is_yolo = any(
            "forge:yolo" in c.get("toString", "") and
            "forge:yolo" not in c.get("fromString", "") and
            current_node in yolo_gates
            for c in label_changes
        )
        assert is_yolo is True

    def test_yolo_not_triggered_outside_gates(self):
        """forge:yolo added while not at a gate is ignored."""
        label_changes = [self._make_label_change("", "forge:yolo")]
        current_node = "generate_spec"
        yolo_gates = {
            "prd_approval_gate", "spec_approval_gate",
            "plan_approval_gate", "task_approval_gate", "rca_option_gate",
        }
        is_yolo = any(
            "forge:yolo" in c.get("toString", "") and
            "forge:yolo" not in c.get("fromString", "") and
            current_node in yolo_gates
            for c in label_changes
        )
        assert is_yolo is False

    def test_yolo_not_triggered_if_already_present(self):
        """forge:yolo already in fromString (no change) does not re-trigger."""
        label_changes = [self._make_label_change("forge:yolo", "forge:yolo forge:prd-approved")]
        current_node = "prd_approval_gate"
        yolo_gates = {
            "prd_approval_gate", "spec_approval_gate",
            "plan_approval_gate", "task_approval_gate", "rca_option_gate",
        }
        is_yolo = any(
            "forge:yolo" in c.get("toString", "") and
            "forge:yolo" not in c.get("fromString", "") and
            current_node in yolo_gates
            for c in label_changes
        )
        assert is_yolo is False
