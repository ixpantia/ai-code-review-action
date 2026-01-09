import os
import json
import requests
import subprocess
import sys

def main():
    # Forgejo/GitHub Actions provide the event path in an environment variable
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        print("Error: GITHUB_EVENT_PATH not found.")
        sys.exit(1)

    with open(event_path, 'r') as f:
        event_data = json.load(f)

    # Check if this is a pull request event
    if "pull_request" not in event_data:
        print("This action only supports pull_request events.")
        sys.exit(0)

    pr_number = event_data["pull_request"]["number"]
    repository = os.getenv("GITHUB_REPOSITORY")
    api_url = os.getenv("GITHUB_API_URL", "https://forgejo.example.com/api/v1")
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        print("Error: GITHUB_TOKEN is required to post comments.")
        sys.exit(1)

    print(f"Processing PR #{pr_number} in {repository}...")

    # 1. Print the git diff
    # We assume the workspace is already checked out and we can compare against the base branch
    # Or we can use the Forgejo API to get the diff. Using git CLI is often easier in actions.
    try:
        # Avoid "dubious ownership" errors in Docker containers
        workspace = os.getenv("GITHUB_WORKSPACE", "/github/workspace")
        subprocess.run(["git", "config", "--global", "--add", "safe.directory", workspace], check=True)

        # Fetch base branch to ensure we can diff against it
        base_ref = event_data["pull_request"]["base"]["ref"]
        subprocess.run(["git", "fetch", "origin", base_ref], check=True)

        print("--- GIT DIFF START ---")
        diff_output = subprocess.check_output(
            ["git", "diff", f"origin/{base_ref}...HEAD"],
            text=True
        ).strip()

        if not diff_output:
            print("The diff is empty.")
        else:
            print(diff_output)
        print("--- GIT DIFF END ---")
    except Exception as e:
        print(f"Warning: Could not get git diff via CLI: {e}")
        # Fallback: could use API but let's stick to CLI for now as it's standard for actions

    # 2. Leave a comment on the PR
    # Forgejo API is compatible with GitHub API for comments
    comment_url = f"{api_url}/repos/{repository}/issues/{pr_number}/comments"

    payload = {
        "body": "Successfully processed the pull request and printed the diff to logs!"
    }

    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }

    print(f"Posting comment to {comment_url}...")
    response = requests.post(comment_url, json=payload, headers=headers)

    if response.status_code == 201:
        print("Successfully posted comment.")
    else:
        print(f"Failed to post comment. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
