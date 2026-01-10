import os
import json
import sys
from google.adk.runners import InMemoryRunner
from google.genai import types
from src.forgejo import ForgejoClient
from src.git_utils import format_diff_for_logging
from src.agent import create_review_agent

def run_ai_review(client, pr_number, google_api_key):
    """ Helper function to execute the AI review process using ADK InMemoryRunner. """
    print(f"Triggering AI Review for PR #{pr_number}...")

    if not google_api_key:
        error_msg = "Error: GOOGLE_API_KEY is not set. Please check your action configuration and secrets."
        print(error_msg)
        client.post_pr_comment(pr_number, error_msg)
        return False

    # 1. Initialize the Agent
    agent = create_review_agent(client, pr_number)

    # 2. Setup the Runner
    # InMemoryRunner is the standard way to run an ADK agent in a script/CI environment
    app_name = "ix-code-review-bot"
    runner = InMemoryRunner(agent, app_name=app_name)

    try:
        # Create a session for the review
        user_id = "forgejo-bot"
        session_id = f"pr-{pr_number}"

        # Ensure the session is created before running the agent
        runner.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

        # Prepare the initial message
        new_message = types.Content(
            parts=[types.Part(text="Please review the changes in this pull request and provide your feedback.")]
        )

        # 3. Execute the agent via the runner
        # The runner returns a generator of events
        events = runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        )

        full_response_text = ""
        for event in events:
            # We collect the text parts from the agent's events
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        full_response_text += part.text

        if not full_response_text:
            full_response_text = "AI Review completed but no feedback was generated."

        # 4. Post the agent's response back to the PR
        if client.post_pr_comment(pr_number, full_response_text):
            print("Successfully posted AI review.")
            return True
        else:
            print("Failed to post AI review comment.")
            return False

    except Exception as e:
        error_msg = f"An error occurred during AI review: {str(e)}"
        print(error_msg)
        client.post_pr_comment(pr_number, error_msg)
        return False

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
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not token:
        print("Error: GITHUB_TOKEN is required.")
        sys.exit(1)

    # Initialize Forgejo Client
    client = ForgejoClient(api_url, token, repository)

    # Logic for Pull Request Events
    if event_name in ["pull_request", "pull_request_target"]:
        pr_number = event_data["pull_request"]["number"]
        action = event_data.get("action")

        if action in ["opened", "synchronize"]:
            print(f"Processing PR #{pr_number} (Action: {action}) in {repository}...")
            diff_text = client.get_pr_diff(pr_number)
            print(format_diff_for_logging(diff_text))
            client.post_pr_comment(pr_number, "Successfully processed the pull request and logged the diff.")

    # Logic for Comment Trigger (#review)
    elif event_name == "issue_comment":
        if "pull_request" not in event_data["issue"]:
            print("Comment is not on a pull request. Ignoring.")
            sys.exit(0)

        comment_body = event_data["comment"]["body"].strip()
        if "#review" in comment_body:
            pr_number = event_data["issue"]["number"]
            if not run_ai_review(client, pr_number, google_api_key):
                sys.exit(1)
        else:
            print("Comment does not contain #review. Ignoring.")
            sys.exit(0)

    else:
        print(f"Unsupported event type: {event_name}")
        sys.exit(0)

if __name__ == "__main__":
    main()
