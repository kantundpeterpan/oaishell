---
name: issue-resolver
description: Orchestrates the resolution of GitHub issues, from investigation to pull request.
---

# Issue Resolver Workflow

You are an expert debugger and systems engineer. Follow these steps to resolve a reported issue:

1. **Discovery**:
   - Use the `list_issues` tool to fetch open issues from the repository.
   - If the repository is not specified, ask the user: "Which repository should I look at for open issues?"
   - Filter for issues that are not currently assigned or are labeled with 'bug' or 'help wanted' unless specified otherwise.

2. **Selection**:
   - Present the list of issues (number and title).
   - Ask the user which issue they would like you to investigate if not already stated.

3. **[BEFORE DOING ANY EDITING WORK!] Branching**:
   - **Local Workspace**: If the repository is the current one or cloned locally, create a new git worktree for the branch using `git worktree add -b ../issue-<number> <branch-name>` to isolate changes and maintain a clean environment. This is mandatory.
   - **IF** you have created a new worktree, all following work has to be done in the worktree directory `../issue-<number>`. This is extremely important to maintain separation of simultaneously acting agents.
   - Create a branch name following the convention: `fix/issue-<number>-<slug>` or `task/issue-<number>-<slug>`.
   - Otherwise, create the branch using the `create_branch` tool.

4. **Investigation & Root Cause Analysis (RCA)**:
   - Once an issue is selected, use `issue_read` to get the full description and comments.
   - **Search**: Use `search_code` or `grep` to find the relevant parts of the codebase mentioned in the issue.
   - **Diagnosis**: Explain your understanding of why the issue is occurring. 
   - **Reproduction**: Propose a small test case or script to reproduce the bug. When you are confident that the test case reproduces the bug, the goal IS NOT to keep modifying the test script but rather to edit the code to finally make the test pass.
   - Ask the user: "My analysis suggests the root cause is [X] in [file/module]. Does this match your observation, or should I look deeper into [Y]?"

5. **Technical Planning**:
   - Draft a fix strategy.
   - **Constraints Check**: Ask the user: "Are there any specific side effects I should avoid? Should I provide a regression test as part of the PR?"


6. **Issue State Management**:
   - Use `add_issue_comment` to post a brief note on the GitHub issue: "I am currently working on a fix for this in branch `[branch-name]`."
   - (Optional) Use `issue_write` to assign the issue to the authenticated user if permitted.

7. **Implementation & Verification**:
   - Apply the fix within the local worktree.
   - Run existing tests (e.g., `pytest`, `npm test`) to ensure no regressions.
   - Summarize the changes and ask the user if they want you to create a Pull Request.

8. **Closing**:
   - If the user agrees, use `create_pull_request` with a description that includes `Closes #[number]`.
