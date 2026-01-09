# IX Code Review Bot

An automated code review bot for Forgejo and Gitea that uses Google's Gemini AI to provide feedback on pull requests.

## Features

- **Automatic Diff Logging**: Automatically prints the git diff to the action logs when a PR is opened or synchronized.
- **AI Code Review**: Triggers an intelligent code review when someone comments `#review` on a pull request.
- **File Awareness**: The AI agent can read any file in the repository to gain better context for its review.
- **Direct Feedback**: Review comments are posted directly back to the pull request.

## Setup

### 1. Requirements

- A Forgejo or Gitea instance.
- A Google Gemini API Key (get one at [Google AI Studio](https://aistudio.google.com/app/apikey)).

### 2. Workflow Configuration

Create a file at `.forgejo/workflows/review.yml` (or `.gitea/workflows/review.yml`) in your repository:

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]
  issue_comment:
    types: [created]

jobs:
  review:
    # Ensure the job runs on PRs or when a comment is made on a PR
    if: github.event_name == 'pull_request' || (github.event_name == 'issue_comment' && github.event.issue.pull_request)
    runs-on: docker
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Fetch all history for accurate diffs

      - name: Run IX Code Review Bot
        uses: ./ix-code-review-bot # Path to where the action is stored
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          google_api_key: ${{ secrets.GOOGLE_API_KEY }}
```

## How to use

### Automatic Diff
Every time you push code to a PR, the bot will log the diff and leave a confirmation comment.

### Requesting a Review
To request an AI review, simply comment on the pull request with:
`#review`

The agent will then:
1. Fetch the pull request diff.
2. Read relevant files if necessary for context.
3. Post a detailed markdown comment with feedback on logic, security, performance, and style.

## Development

The project is modularized for easy extension:
- `main.py`: Entry point and event handling.
- `src/agent.py`: ADK Agent configuration and tools.
- `src/forgejo.py`: API client for interacting with Forgejo/Gitea.
- `src/git_utils.py`: Helpers for formatting git data.