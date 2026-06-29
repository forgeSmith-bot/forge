## Task Ticket

**Key:** {ticket_key}
**Summary:** {summary}

**Description:**
{description}

**Comments:**
{comments}

## Available Repositories

Use only these exact repository names when tagging `repo:<owner>/<name>` in the plan:

{known_repos}

## File Metadata

Here is the file metadata gathered from the repository to help guide your plan:

{file_metadata}

## Repository Grounding Requirements

Before writing `.forge/plan.md`, inspect the relevant repository using available repository, GitHub, or filesystem tools.

- Read repo guidance when present: `AGENTS.md`, `CLAUDE.md`, `.claude/AGENTS.md`, `.claude/CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `Makefile`, language-specific project files, docs, and repo-local skills or agent instructions.
- Confirm planned files, functions/classes, test locations, generated-file requirements, and validation commands against real repository contents.
- Follow discovered repository standards for architecture, naming, error handling, testing, packaging, documentation, and local agent workflow.
- Prefer codebase exploration focused on the ticket description, proposed solution/approach, nearby code, and validation commands. Broaden the search when needed to understand the context safely. Do not inspect project-management metadata such as unrelated branches, open issues, pull requests, milestones, or release boards unless explicitly required.
- Use nearby code and test patterns instead of guessing from path names alone.
- Do not invent generic paths, symbols, frameworks, test runners, or directory layouts. If repository inspection is unavailable, write the plan with an explicit blocking note explaining what repo access or configuration is required.

## Formulate Implementation Plan

Formulate a concrete implementation plan mapping the proposed solution to specific target files and test plans.

Your plan MUST include:
1. **Target Files**: List the specific, existing repository files to be modified, or new files to be created, incorporating the gathered file metadata and repository inspection.
2. **Implementation Steps**: Clear, sequential steps for implementing the proposed solution/approach.
3. **Test Plans**: A detailed validation plan describing how the changes will be tested. Map the proposed solutions to concrete unit or integration tests, naming specific test commands and test files (existing or new) to run.

---

Produce a detailed implementation plan.
Write the plan to `.forge/plan.md`.
