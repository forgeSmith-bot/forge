<p align="center">
  <img src="docs/images/logo.png" alt="Forge Logo" width="1000">
</p>

<p align="center">
  <a href="https://github.com/Forge-sdlc/forge/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/Forge-sdlc/forge/actions/workflows/ci.yml/badge.svg">
  </a>
  <a href="https://github.com/Forge-sdlc/forge/actions/workflows/docs.yml">
    <img alt="Docs" src="https://github.com/Forge-sdlc/forge/actions/workflows/docs.yml/badge.svg">
  </a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-blue">
  <img alt="License MIT" src="https://img.shields.io/badge/license-MIT-green">
</p>

<p align="center">
  <img alt="Jira Ticket" src="https://img.shields.io/badge/Jira-Ticket-0052CC">
  <img alt="AI Planning" src="https://img.shields.io/badge/AI-Planning-7C3AED">
  <img alt="Containerized Code" src="https://img.shields.io/badge/Code-Containerized-2496ED">
  <img alt="GitHub PR" src="https://img.shields.io/badge/GitHub-PR-181717">
  <img alt="CI Repair" src="https://img.shields.io/badge/CI-Auto--repair-F97316">
  <img alt="Human Review" src="https://img.shields.io/badge/Human-Review-16A34A">
</p>

# Forge

Forge turns Jira tickets into reviewed GitHub pull requests.

It plans work, asks for human approval, implements changes in isolated containers, opens PRs, fixes CI failures, and pauses for review before anything is merged. Forge is built for teams that want AI to participate in the software delivery lifecycle without bypassing the controls that make engineering work trustworthy.

Forge is for work that cannot be handled by a single prompt: cross-repo changes, approval gates, CI failures, review feedback, audit trails, and project-level visibility.

<p align="center">
  🎫 <strong>Jira ticket</strong> → 🧭 <strong>Human-gated plan</strong> → 📦 <strong>Repo-scoped implementation</strong> → 🔀 <strong>GitHub PRs</strong> → 🛠️ <strong>CI repair</strong> → 👀 <strong>Human review</strong> → 📊 <strong>Summary + dashboards</strong>
</p>

## What Forge Does

Forge connects Jira, GitHub, and AI coding agents into one event-driven workflow:

- **Turns product intent into implementation plans**: Generate PRDs, behavioral specs, epics, tasks, RCA reports, and concrete fix plans from Jira issues.
- **Plans across repositories**: Decompose features and bugs across the repositories configured for a Jira project, then create repo-scoped epics, tasks, implementation passes, and PRs.
- **Keeps humans in the loop**: Pause at approval gates, answer reviewer questions, regenerate artifacts from feedback, and require human PR review before merge.
- **Implements code in controlled environments**: Run implementation inside ephemeral Podman containers with repository access scoped to the task.
- **Handles the PR lifecycle**: Create fork-based PRs, write PR descriptions, respond to review feedback, rebase when needed, and keep Jira updated.
- **Repairs failing CI**: Analyze failing checks, apply fixes, push updates, and retry until the workflow is ready for review or blocked with a clear reason.
- **Adapts to each project**: Use skills to customize how Forge writes plans, implements code, reasons about CI, and follows team conventions.

## Model Backends

Forge is built on [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) and passes agents a LangChain chat model instance.

The built-in model factory supports direct Anthropic API credentials and Google Vertex AI-backed models. Because the agent layer is model-object based, Forge can be extended to any LangChain-compatible chat model by adding it to the model factory.

## Where Forge Is Different

Forge is not just an agent with a large prompt or a folder of skills. It is a stateful delivery workflow that decides what should happen next, when to pause, which artifact needs review, which repository should be changed, and how to recover when something fails.

- **Workflow first, agents second**: LangGraph coordinates the lifecycle from ticket intake to PR review. Agents perform bounded stage work; the workflow owns routing, checkpoints, retries, approvals, and handoffs.
- **Cross-repo by design**: Forge can plan features and bugs across services, clients, infrastructure, and documentation repos, then split the work into repo-scoped units that can be implemented and reviewed independently.
- **Controlled write boundaries**: Agents do not directly mutate Jira, GitHub, or production repositories. Implementation agents write only inside their local/container workspace; Forge's integration layer performs external updates such as Jira comments, labels, branch pushes, and PR creation at explicit workflow steps.
- **Native engineering loop**: Forge works through Jira tickets, Jira comments, Jira labels, GitHub PRs, GitHub reviews, and CI webhooks instead of forcing teams into a separate agent UI.
- **Traceable by default**: Work is reflected back into Jira and GitHub as comments, labels, PRs, review updates, CI decisions, and post-merge summaries, so teams can follow why the workflow moved or paused.
- **Project visibility**: Prometheus metrics, Langfuse traces, and Grafana dashboards expose workflow throughput, step latency, ticket execution cost, model usage, CI behavior, and observability health by project, ticket type, workflow step, and Jira issue.
- **Evidence-backed bug fixing**: Bug workflows include triage, codebase investigation, RCA validation, fix-option selection, plan approval, implementation, qualitative review, and post-merge summaries.
- **Bounded autonomy**: Forge can move quickly, but approval gates, review gates, retry budgets, blocked states, and audit comments keep the system inspectable.

## Why Forge

Most AI coding tools start at the editor. Forge starts at the ticket.

That changes the shape of the work. Instead of asking a coding agent to make an isolated change, Forge manages the path from request to reviewed pull request:

1. Understand the issue.
2. Produce the right planning artifact.
3. Ask for approval or clarification.
4. Decompose the work into repo-scoped executable tasks.
5. Implement and review the code.
6. Open a pull request.
7. Watch CI and fix failures.
8. Wait for human review.
9. Report the outcome back to Jira.

The goal is not to remove engineering judgment. The goal is to give engineering teams an automated delivery loop where judgment is applied at explicit checkpoints.

Forge also makes the delivery loop observable. Teams can inspect individual ticket execution in Jira, GitHub, Langfuse, and Grafana, while project dashboards show where work is flowing, where it is blocked, how much CI repair is happening, and which workflow stages cost the most time or model budget.

## Workflows

### Feature Workflow

Forge can take a Jira Feature from idea to one or more pull requests:

```text
Feature Ticket
  -> PRD
  -> Behavioral Spec
  -> Cross-repo Epics
  -> Repo-scoped Implementation Tasks
  -> Containerized Implementation
  -> Local AI Review
  -> GitHub PRs
  -> CI Fix Loop
  -> AI Review
  -> Human Review
```

At each planning stage, reviewers can approve, request revisions, or ask questions without advancing the workflow.

### Bug Workflow

Forge can take a Jira Bug through diagnosis, planning, implementation, and post-merge reporting:

```text
Bug Ticket
  -> Triage
  -> Root Cause Analysis
  -> Fix Options
  -> Plan Approval
  -> Repo-scoped Implementation Tasks
  -> Fix PRs
  -> CI + Review
  -> Post-merge Summary
```

For bugs, Forge investigates the codebase, proposes concrete fix options, waits for an option selection, implements the chosen approach across the affected repos, and posts a summary after merge.

## Human Control

Forge is designed around approval gates, auditability, and recoverability:

- **Approval gates** before major planning transitions.
- **Q&A mode** for asking questions about generated artifacts before approving.
- **Revision requests** for regenerating artifacts with human feedback.
- **Containerized implementation** so coding work happens in isolated task environments.
- **Controlled external writes** so agents work locally while Forge performs Jira/GitHub mutations through explicit workflow steps.
- **Local review before PR creation** to catch obvious issues before reviewers see them.
- **CI repair loop** with bounded retry attempts and clear blocked states.
- **Human PR review** before merge, even when autonomous mode is enabled.
- **Resumable workflows** that checkpoint state and resume from the failed node.
- **Operational dashboards** for tracking workflow health, ticket execution, model usage, and project-level delivery trends.

Forge can run with more automation when a ticket is trusted, but the final code review gate remains a human checkpoint.

## Customization

Forge uses skills to adapt agent behavior to your project.

Skills are Markdown instruction files that define how Forge should produce PRDs, specs, implementation plans, code changes, CI analysis, and review feedback. They customize stages inside the workflow; they do not replace the workflow itself. Teams can keep shared defaults while overriding only the parts that are specific to a stack, repository, or Jira project.

This lets Forge follow local engineering conventions without forking the orchestrator.

## Architecture

Forge is event-driven:

```text
Jira + GitHub Webhooks
  -> FastAPI Gateway
  -> Redis Streams Queue
  -> LangGraph Workflow
  -> Host Orchestrator Agent
  -> Container Agent for Implementation
  -> Jira + GitHub Updates
```

Jira and GitHub send webhooks to Forge. Forge queues events, resumes the right workflow state, runs the next node, and posts the result back to Jira or GitHub. Planning runs through the host orchestrator. Code implementation runs in short-lived containers. Agents generate artifacts and local code changes; Forge's workflow and integration layer decide when those outputs become Jira updates, branch pushes, or pull requests.

## Quick Start

This guide helps you set up the core Forge orchestrator and supporting services locally on your machine.

### Prerequisites

To run Forge locally, you will need:
* **Python 3.11+**
* **Podman** (or Docker) for containerized code execution
* **Jira Cloud API access** (API token, user email, and base URL)
* **GitHub personal access token** (classic or fine-grained with repo access)
* **LLM backend credentials** (direct Anthropic API key, or Google Vertex AI credentials)

---

### Step-by-Step Installation

#### 1. Clone the Repository
Clone and navigate to the project directory:
```bash
git clone https://github.com/Forge-sdlc/forge.git
cd forge
```

#### 2. Set Up the Environment
We use `uv` for python package and environment management. Initialize the environment and install dependencies:
```bash
uv sync
```

Copy the example environment configuration to `.env`:
```bash
cp .env.example .env
```
Open `.env` in your text editor and fill in your required LLM provider credentials, Jira API details, and GitHub tokens (as outlined in the configuration comments).

#### 3. Build the Task Execution Image
Forge executes code changes in isolated, ephemeral environments. Build the local task execution container image using Podman:
```bash
podman build -t localhost/forge-dev:latest -f containers/Containerfile containers/
```
*(Note: Keep `CONTAINER_IMAGE=localhost/forge-dev:latest` inside your `.env` so Forge knows to target this local image).*

---

### Running Core Services

#### 4. Start Redis Stack
Forge uses Redis Stack (not standard Redis) for state checkpointing and event streams. Spin up a Redis Stack container on port `6380` to avoid conflict with other Redis instances:
```bash
podman run -d --name redis-stack -p 6380:6379 redis/redis-stack-server:latest
```

#### 5. Start the FastAPI Gateway
The API gateway receives incoming Jira and GitHub webhooks. Start the FastAPI server using `uv`:
```bash
uv run uvicorn forge.main:app --reload --port 8000 --host 0.0.0.0
```

#### 6. Start the Forge Worker
The Celery/workflow worker processes background tasks and drives the LangGraph workflow graph. Run the worker in a separate terminal:
```bash
uv run forge worker
```

---

### Running Extra Observability Services (Optional)

Forge includes a developer observability stack that provides Prometheus metrics, Langfuse tracing, and preconfigured Grafana dashboards for local performance tuning and monitoring.

#### Local Prometheus & Grafana Monitoring
You can spin up Prometheus and Grafana using Docker Compose:
```bash
docker compose -f devtools/docker-compose.dev.yml up -d
```
Once started, the following local dashboards will be available:
- **Prometheus**: `http://localhost:9092`
- **Grafana**: `http://localhost:3010` (Default credentials: username `admin`, password `grafana`)

#### LLM Tracing with Langfuse
To enable complete LLM execution tracing and inspect agent tool calls:
1. Set `LANGFUSE_ENABLED=true` in your `.env`.
2. Configure your public/secret keys and point `LANGFUSE_HOST` to your instance (e.g., `https://cloud.langfuse.com` or a local self-hosted instance).

---

See [Getting Started](https://Forge-sdlc.github.io/forge/getting-started/) for the full setup path, including environment variables, webhooks, and local development options.

## Documentation

- [Getting Started](https://Forge-sdlc.github.io/forge/getting-started/): Install Forge and run your first workflow.
- [Feature Workflow](https://Forge-sdlc.github.io/forge/guide/feature-workflow/): Understand the feature pipeline and approval gates.
- [Bug Workflow](https://Forge-sdlc.github.io/forge/guide/bug-workflow/): Understand triage, RCA, fix options, and bug implementation.
- [PR Commands](https://Forge-sdlc.github.io/forge/guide/pr-commands/): Rebase PRs and handle CI gate skips.
- [Configuration Reference](https://Forge-sdlc.github.io/forge/reference/config/): Environment variables and project configuration.
- [Skills System](https://Forge-sdlc.github.io/forge/skills/): Customize Forge for your team and stack.
- [Developer Guide](https://Forge-sdlc.github.io/forge/developer-guide/): Local testing, debugging, Prometheus metrics, Langfuse tracing, and Grafana dashboards.

## Contributing

The most useful way to extend Forge is to teach it how your team works.

Contributions can improve the orchestrator, workflow stages, integrations, or default skills. Teams can also publish project-specific skill sets that customize planning, implementation, CI behavior, and review conventions.

See [Contributing](https://Forge-sdlc.github.io/forge/dev/contributing/) for the full guide.
