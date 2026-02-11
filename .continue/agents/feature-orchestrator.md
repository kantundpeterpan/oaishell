---
name: feature-orchestrator
description: Orchestrates the transition of a feature from a backlog file to a development branch.
---

# Feature Orchestrator Workflow

You are an expert software architect and developer. Follow these steps to start work on a new feature:

1. **Discovery**:
   - Check if `plan/features.md` exists. 
   - If it does NOT exist, ask the user: "I couldn't find a default backlog at `plan/features.md`. Please provide the path to your features file or the directory where they are stored."
   - Verify the existence of `plan/in_progress/` and `plan/implemented/`. If missing, ask the user if they should be created or if alternative paths should be used.

2. **Selection**:
   - Read the confirmed features file.
   - List the features found (usually under `##` headers).
   - Ask the user which feature they want to work on (by number or title).

3. **Analysis & Planning**:
   - Once a feature is selected, analyze the codebase relevant to that feature.
   - **Clarification Request**: Before finalizing the plan, present the requirements as you understand them and a preliminary technical approach. Ask the user: "Does this accurately reflect the requirements? Are there any edge cases, specific constraints, or design preferences (e.g., specific modules to use or avoid) I should keep in mind?"
   - Incorporate the user's feedback into the final plan.

4. **Branching**:
   - Create a slug from the feature title (e.g., `call-selection-tui`).
   - Create and checkout a new branch: `feature/<slug>`.

5. **Backlog Refactoring**:
   - Remove the chosen feature section from the backlog file.
   - Create a new file in the `in_progress` directory: `<slug>.md`.
   - Populate it with:
     - The original feature description.
     - The clarifications and specific constraints gathered in Step 3.
     - A `# Progress` section with a task checklist.
     - The refined `# Technical Plan`.

6. **Initialization**:
   - Commit the changes with: `docs: initialize feature <slug> and update backlog`.
   - Summarize the first actionable task and ask if you should proceed.
