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

    # 1. Get the git diff via Forgejo API
    print("--- GIT DIFF START ---")
    diff_url = f"{api_url}/repos/{repository}/pulls/{pr_number}.diff"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff"
    }

    try:
        diff_response = requests.get(diff_url, headers=headers)
        if diff_response.status_code == 200:
            diff_output = diff_response.text.strip()
            if not diff_output:
                print("The diff is empty.")
            else:
                print(diff_output)
        else:
            print(f"Error fetching diff: {diff_response.status_code}")
            print(diff_response.text)
    except Exception as e:
        print(f"Error: Could not get git diff via API: {e}")
    print("--- GIT DIFF END ---")

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
