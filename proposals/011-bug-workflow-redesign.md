# Proposal: Bug Workflow Redesign — Triage, Container Analysis, Reflection, and Planning

**Author:** eshulman2  
**Date:** 2026-05-12  
**Status:** Under Review

## Summary

The current bug workflow generates an RCA from the Jira ticket description alone, without exploring the codebase, and goes directly to implementation after a single approval gate. This proposal redesigns it with five new stages: a triage check that ensures the ticket has enough information before analysis begins, a container-based analysis agent that explores repos and produces a structured RCA with 1–4 fix options, a reflection loop that validates the RCA using a critic agent, an option selection gate where the user picks a fix approach, and a planning stage that produces an approved implementation plan before any code is written. Multi-repo fixes are decomposed into linked Jira tasks, reusing the existing task execution infrastructure.

---

## Motivation

### Problem Statement

The current bug workflow has three fundamental weaknesses:

1. **No triage.** The workflow starts immediately from whatever the reporter typed into Jira. Under-specified tickets — missing stack traces, reproduction steps, affected versions — go into analysis and produce low-quality or incorrect RCAs. There is no mechanism to ask the reporter for what's missing.

2. **Analysis without code exploration.** `analyze_bug` sends the Jira description and summary to an agent with no repo access. The RCA is generated from the bug report alone, which means it can only reflect what the reporter described — not what the code actually does. Root causes that require reading the implementation are missed.

3. **No planning before implementation.** After RCA approval the workflow goes directly to `implement_bug_fix`. There is no opportunity to align on how the fix should be structured, which files it touches, or how it should be tested before the container starts writing code. For multi-repo bugs there is no decomposition at all.

### Current Workarounds

Engineers either write highly detailed bug reports (putting all the context that the agent would need into the description), or they accept low-quality RCAs and provide manual feedback through the revision gate. Multi-repo bugs are handled by manually creating tasks and not using Forge for them.

---

## Proposal

### Overview

Replace the current single-gate RCA flow with a five-stage pipeline:

```
triage_check → [triage_gate if needed] → analyze_bug → reflect_rca
             → rca_option_gate → plan_bug_fix → plan_approval_gate
             → decompose_plan → [existing task execution loop]
```

Everything from `setup_workspace` onward is unchanged.

### Detailed Design

#### Full graph

```
route_entry
    ↓
triage_check ─── sufficient ──→ analyze_bug ←──────────────────────┐
    │                                ↓                              │ (feedback)
    └── missing ──→ triage_gate      reflect_rca ──── gaps ──→ analyze_bug
                    (pause)     ↓         ↑                (max 3 iterations)
                          ──────┘    passes
                                     ↓
                              rca_option_gate (pause)
                                     │
                        ┌────────────┴────────────┐
                    >option N                 feedback
                        ↓                        ↓
                  plan_bug_fix           regenerate_rca → analyze_bug loop
                        ↓
                  plan_approval_gate (pause, forge:plan-approved label)
                        │
               ┌────────┴────────┐
           approved           feedback
               ↓                  ↓
         decompose_plan    regenerate_plan → plan_bug_fix
               ↓
        [linked Jira tasks]
               ↓
        setup_workspace → implement_bug_fix → local_review
            → create_pr → teardown_workspace
            → ci_evaluator → human_review_gate → END
```

#### Stage 1: Triage

**`triage_check`** (no container) evaluates the Jira ticket against six required fields:

1. Steps to reproduce
2. Expected vs actual behavior
3. Environment (OS, runtime, infrastructure)
4. Affected versions
5. Error output (stack trace, log snippet, or error message)
6. Affected component / repo

If all six are present or clearly inferable, routes directly to `analyze_bug` — no pause.

If any are missing, posts a targeted Jira comment naming only the absent fields, sets `forge:triage-pending`, and routes to `triage_gate`. On resume, `triage_check` re-evaluates the updated ticket (description + all comments). Repeats until satisfied. No iteration limit.

#### Stage 2: Analysis

**`analyze_bug`** runs in a standard container (same `ForgeAgent` infra as `implement_bug_fix`, full write permissions inside the container, repo access). Receives the full Jira ticket, `triage_missing_fields`, and any `reflection_critique` from a previous iteration.

The agent explores the codebase — clones repos, checks out branches, reads files, inspects git history — to locate the defect. The resulting RCA must include:
- Confirmed code location (file, function, line range)
- Mechanism of failure
- Trace from trigger to symptom
- **1–4 distinct fix options**, each with title, description, and trade-offs
- Embedded code snippets sufficient for the critic to validate without independent exploration

**`reflect_rca`** runs in a standard container (same infra). Receives the RCA text. Validates:
- Named files and functions exist at the stated locations
- Failure mechanism is actually possible given the code
- Fix options are genuinely distinct
- No unexplained gaps between trigger and symptom

Outputs `VALID` or a structured critique listing specific gaps. On gaps: stores critique in `reflection_critique`, routes back to `analyze_bug`. Max 3 iterations. After the third failed reflection, the best available RCA is used and a warning note is appended to the Jira comment.

#### Stage 3: RCA Option Gate

**`rca_option_gate`** pauses and posts a structured Jira comment presenting the fix options. Sets `forge:rca-pending` (reuses existing label).

```
## Root Cause Analysis
<rca summary>

## Fix Options

**Option 1: <title>**
<description and trade-offs>

**Option 2: <title>**
<description and trade-offs>

...

Reply with `>option N` to select an approach, or comment with feedback to revise the RCA.
```

Comment routing on resume:

| Comment | Action |
|---------|--------|
| `>option N` (case-insensitive) | Validate N in range → store `selected_fix_option` + `selected_fix_approach` → `plan_bug_fix` |
| `>option N` out of range | Post clarifying comment → re-pause |
| No `>option` prefix | RCA feedback → `regenerate_rca` → re-runs `analyze_bug` + `reflect_rca` → return to gate |
| Question (Q&A mode) | `answer_question` → return to gate |

#### Stage 4: Planning

**`plan_bug_fix`** runs in a standard container with repo access. Receives the full RCA and `selected_fix_approach`. Produces a concrete implementation plan: which files to change, what the changes accomplish, new tests required, order of operations, and which repos are involved. Posts the plan as a Jira comment and sets `forge:plan-pending`.

```
## Implementation Plan

**Approach: <selected option title>**

### Changes
1. `path/to/file.py` — <what changes and why>
2. `path/to/test_file.py` — <new regression test>
...

### Repos
- `repo-name` (tag: repo:repo-name)

### Order of operations
<step-by-step sequence>
```

**`plan_approval_gate`** pauses. Sets `forge:plan-pending` label.

| Trigger | Action |
|---------|--------|
| `forge:plan-approved` label applied | Route to `decompose_plan` |
| Plain comment | Feedback → `regenerate_plan` → re-runs `plan_bug_fix` → return to gate |

**`decompose_plan`** (no container) creates one Jira **Task** per repo, linked to the bug ticket via "implements" issue link. Each task gets a `repo:<repo-name>` label (same pattern as epic decomposition in the feature workflow) and scoped implementation instructions. Every approved plan produces at least one linked task — if no repo is explicitly identified, the task is created against the primary repo from the ticket context.

#### New state fields

```python
# Triage
triage_passed: bool
triage_missing_fields: list[str]

# Analysis / reflection
reflection_count: int
reflection_critique: str | None
rca_options: list[dict]          # [{title, description, tradeoffs}, ...]

# Option selection
selected_fix_option: int | None
selected_fix_approach: dict | None

# Planning
plan_content: str | None
linked_task_keys: list[str]      # Jira task keys created by decompose_plan
```

#### New `ForgeLabel` entries

```python
TRIAGE_PENDING = "forge:triage-pending"
PLAN_PENDING   = "forge:plan-pending"
PLAN_APPROVED  = "forge:plan-approved"
```

#### Prompts

| File | Status | Purpose |
|------|--------|---------|
| `triage-bug.md` | New | Evaluate ticket against six-field checklist; output missing fields or "sufficient" |
| `analyze-bug.md` | Rewrite | Container analysis with 1–4 fix options and embedded code evidence |
| `regenerate-rca.md` | Rewrite | Re-analyze incorporating user feedback; same output structure as `analyze-bug.md` |
| `reflect-rca.md` | New | Critic pass; output `VALID` or structured gaps |
| `plan-bug-fix.md` | New | Generate implementation plan from RCA + selected option |
| `regenerate-plan.md` | New | Revise plan incorporating user feedback |
| `fix-bug.md` | **Retired** | Replaced by `implement-task` prompt used with plan as context |

### User Experience

**Happy path (well-specified bug, single repo, one obvious fix):**

```
[Bug filed with all six fields present]

[Forge, immediately]
forge:rca-pending set on PROJ-123

## Root Cause Analysis
The session manager does not invalidate tokens on logout...

## Fix Options
**Option 1: Invalidate on logout**
Add token revocation in logout handler. Simple, targeted.

**Option 2: Short-lived tokens with refresh**
Switch to short-lived JWTs. More secure but larger change.

[Engineer]
>option 1

[Forge]
forge:plan-pending set on PROJ-123

## Implementation Plan
**Approach: Invalidate on logout**
1. `auth/session.py` — add revoke_token() call in logout()
2. `tests/test_auth.py` — add test for token invalid after logout
...

[Engineer applies forge:plan-approved]

[Forge creates PROJ-456: "Fix: Invalidate session token on logout (auth-service)"]
[Forge implements, opens PR, CI passes, ready for review]
```

**Under-specified bug:**

```
[Bug filed: "login is broken"]

[Forge]
forge:triage-pending set on PROJ-123

I need more information before I can analyze this bug:
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, runtime, infrastructure)
- Affected versions
- Error output (stack trace or error message)

[Reporter adds details]

[Forge resumes analysis...]
```

---

## Error Handling

All new nodes follow the existing pattern: exceptions are caught, stored in `last_error`, `retry_count` incremented. After max retries, `escalate_blocked` is called.

| Node | On failure | Special case |
|------|-----------|--------------|
| `triage_check` | Retry up to 3×, then escalate | — |
| `analyze_bug` | Retry up to 3×, then escalate | — |
| `reflect_rca` | Loop up to 3 iterations without `VALID` | After 3rd iteration: use best available RCA, append warning note to Jira comment, continue — do not escalate |
| `plan_bug_fix` | Retry up to 3×, then escalate | — |
| `decompose_plan` | Escalate immediately | No partial task creation — all tasks created atomically or not at all |
| `>option N` out of range | Post clarifying comment, re-pause | Not an escalation; no retry count incremented |

## Q&A Mode

The existing `answer_question` node is extended to cover all three new pause gates: `triage_gate`, `rca_option_gate`, and `plan_approval_gate`. A question comment at any of these gates routes to `answer_question` and returns to the originating gate, using the same `current_node` routing already in place for the RCA gate. No new Q&A infrastructure is required.

## Scope: What Is Not Changing

- `setup_workspace`, `implement_bug_fix`, `local_review`, `create_pr`, `teardown_workspace` — unchanged
- CI evaluation loop (`ci_evaluator`, `attempt_ci_fix`, `wait_for_ci_gate`) — unchanged
- Human review loop (`human_review_gate`, `implement_review`, `review_response_gate`) — unchanged
- `escalate_blocked` — unchanged, used by all new nodes on failure
- `route_entry` resume logic — extended to cover new nodes; all existing resume paths preserved

---

## Alternatives Considered

| Alternative | Pros | Cons | Why Not |
|-------------|------|------|---------|
| Always pause at triage gate | Simple, uniform flow | Adds friction to well-specified bugs | Conditional gate keeps happy path fast |
| Reflection inside container (opaque loop) | Simpler graph | Not observable or resumable independently | Graph node is more debuggable and testable |
| Single combined triage + analysis container | Fewer container invocations | Can't resume from triage without re-running analysis; mixed responsibilities | Separate nodes have cleaner contracts |
| Subtasks instead of linked tasks for decomposition | Closer to parent-child semantics | Jira doesn't support subtasks on Bug issue type | Linked tasks with "implements" is the correct Jira model |
| Comment prefix for plan approval (`>approve`) | Consistent with option selection | Inconsistent with all other approval gates (label-based) | Labels are the existing pattern |

---

## Implementation Plan

### Phases

1. **Phase 1: Triage** — `triage_check` node, `triage_gate`, `triage-bug.md` prompt, new `TRIAGE_PENDING` label, `route_entry` extended for resume (~1 day)
2. **Phase 2: Container analysis** — Rewrite `analyze_bug` for repo exploration, `analyze-bug.md` and `regenerate-rca.md` rewrites, `rca_options` state parsing (~1.5 days)
3. **Phase 3: Reflection loop** — `reflect_rca` node, `reflect-rca.md` prompt, loop routing with max-iteration handling (~1 day)
4. **Phase 4: Option selection gate** — `>option N` comment parsing, `selected_fix_approach` state, updated `rca_option_gate` routing (~0.5 days)
5. **Phase 5: Planning** — `plan_bug_fix` node, `plan_approval_gate`, `regenerate_plan`, `plan-bug-fix.md` and `regenerate-plan.md` prompts, `PLAN_PENDING`/`PLAN_APPROVED` labels (~1.5 days)
6. **Phase 6: Decomposition** — `decompose_plan` node, Jira task creation with "implements" link, `repo:<name>` tagging, `linked_task_keys` state (~1 day)
7. **Phase 7: Tests and cleanup** — Update `tests/flows/bug_workflow/`, retire `fix-bug.md`, extend `route_entry` for all new nodes, update Q&A routing to cover new gates (~1 day)

### Dependencies

- [ ] `ForgeAgent.run_task()` must support passing a workspace path for the analysis container (triage check does not need a workspace; analysis does)
- [ ] Jira client needs `create_issue_link()` for the "implements" link type used by `decompose_plan`
- [ ] `rca_options` parsing: structured output format must be defined in `analyze-bug.md` and consistently parseable by the orchestrator (JSON block or delimited sections)
- [ ] `forge:plan-approved` label must be registered in the worker's label-event routing table alongside existing approval labels

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Reflection loop runs 3× on every ticket, tripling analysis time | Med | Med | Cap at 3; monitor average iteration count; consider 2 as default |
| `analyze_bug` container produces inconsistently structured `rca_options` | High | High | Define strict output schema in prompt; add parsing validation with fallback |
| `triage_check` is too strict and blocks well-specified tickets | Low | Med | Prompt must use "clearly inferable" not "explicitly stated"; test against real ticket corpus |
| `decompose_plan` creates tasks with incorrect repo tags | Med | Med | Validate `repo:<name>` tags against known repos from project metadata before creating |
| Retiring `fix-bug.md` breaks any existing in-flight bug workflows | Low | High | `route_entry` resume routing preserves paths for existing checkpoints; retiring prompt only affects new invocations |

---

## Open Questions

- [ ] Should the triage checklist be configurable per Jira project (some projects always include stack traces; others are for infra bugs with no traces)?
- [ ] What is the maximum number of linked tasks `decompose_plan` should create? Is there a cap or does it follow the plan?
- [ ] Should Q&A mode be extended to `triage_gate` and `plan_approval_gate`, or is it only needed at the RCA option gate?
- [ ] After `reflect_rca` exhausts its 3 iterations without `VALID`, should the workflow pause for human review of the unvalidated RCA, or proceed with the warning note automatically?

---

## References

- [Design doc](../docs/superpowers/specs/2026-05-12-bug-workflow-design.md)
- [Current bug workflow graph](../src/forge/workflow/bug/graph.py)
- [Current bug workflow nodes](../src/forge/workflow/nodes/bug_workflow.py)
- [Feature workflow epic decomposition](../src/forge/workflow/feature/graph.py) — repo tagging pattern reference
