import os
import json
import sys
from src.forgejo import ForgejoClient
from src.git_utils import format_diff_for_logging
from src.agent import create_review_agent

def main():
    # Load event data
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        print("Error: GITHUB_EVENT_PATH not found.")
        sys.exit(1)

    with open(event_path, 'r') as f:
        event_data = json.load(f)

    event_name = os.getenv("GITHUB_EVENT_NAME")
    repository = os.getenv("GITHUB_REPOSITORY")
    api_url = os.getenv("GITHUB_API_URL", "https://forgejo.example.com/api/v1")
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        print("Error: GITHUB_TOKEN is required.")
        sys.exit(1)

    # Initialize Forgejo Client
    client = ForgejoClient(api_url, token, repository)

    # Logic for Pull Request Synchronize/Open (Print Diff & Success)
    if event_name == "pull_request":
        pr_number = event_data["pull_request"]["number"]
        print(f"Processing PR #{pr_number} in {repository}...")

        # 1. Fetch and print the diff
        diff_text = client.get_pr_diff(pr_number)
        print(format_diff_for_logging(diff_text))

        # 2. Leave a success comment
        success_message = "Successfully processed the pull request and printed the diff to logs!"
        if client.post_pr_comment(pr_number, success_message):
            print("Successfully posted success comment.")
        else:
            sys.exit(1)

    # Logic for Comment Trigger (#review)
    elif event_name == "issue_comment":
        # Check if it's a pull request comment (Forgejo/Gitea uses issue_comment for PRs too)
        if "pull_request" not in event_data["issue"]:
            print("Comment is not on a pull request. Ignoring.")
            sys.exit(0)

        comment_body = event_data["comment"]["body"].strip()
        if "#review" not in comment_body:
            print("Comment does not contain #review. Ignoring.")
            sys.exit(0)

        pr_number = event_data["issue"]["number"]
        print(f"Triggering AI Review for PR #{pr_number}...")

        # Verify Google API Key for the Agent
        if not os.getenv("GOOGLE_API_KEY"):
            error_msg = "Error: GOOGLE_API_KEY is not set. Cannot run AI review."
            print(error_msg)
            client.post_pr_comment(pr_number, error_msg)
            sys.exit(1)

        # 1. Initialize the Agent
        agent = create_review_agent(client, pr_number)

        # 2. Run the Agent
        try:
            # We pass a simple prompt to start the review process
            # The agent has tools to get the diff and read files.
            response = agent.run("Please review the changes in this pull request and provide your feedback.")

            # 3. Post the agent's response back to the PR
            if response and hasattr(response, 'text'):
                review_content = response.text
            else:
                review_content = str(response)

            if client.post_pr_comment(pr_number, review_content):
                print("Successfully posted AI review.")
            else:
                print("Failed to post AI review comment.")
                sys.exit(1)

        except Exception as e:
            error_msg = f"An error occurred during AI review: {str(e)}"
            print(error_msg)
            client.post_pr_comment(pr_number, error_msg)
            sys.exit(1)

    else:
        print(f"Unsupported event type: {event_name}")
        sys.exit(0)

if __name__ == "__main__":
    main()
