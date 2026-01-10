import os
import json
import sys
import asyncio
from google.adk.runners import InMemoryRunner
from google.genai import types
from src.forgejo import ForgejoClient
from src.git_utils import format_diff_for_logging
from src.agent import create_review_agent

async def run_ai_review(client, pr_number, google_api_key, head_sha):
    """ Helper function to execute the AI review process using ADK InMemoryRunner. """
    print(f"Triggering AI Review for PR #{pr_number}...")

    if not google_api_key:
        error_msg = "Error: GOOGLE_API_KEY is not set. Please check your action configuration and secrets."
        print(error_msg)
        await asyncio.to_thread(client.post_pr_comment, pr_number, error_msg)
        return False

    # 1. Initialize the Agent
    agent = create_review_agent(client, pr_number, head_sha)

    # 2. Setup the Runner
    app_name = "ix-code-review-bot"
    runner = InMemoryRunner(agent, app_name=app_name)

    try:
        user_id = "forgejo-bot"
        session_id = f"pr-{pr_number}"

        # 3. Ensure the session is created
        await runner.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

        # 4. Prepare the initial message
        # We emphasize that the output should ONLY be the review markdown.
        new_message = types.Content(
            parts=[types.Part(text="Please review the changes in this pull request. Provide ONLY your final professional Markdown feedback for the PR comment. Do not include any meta-talk, planning, or internal thought process in your output.")]
        )

        # 5. Execute the agent via run_async
        full_response_text = ""
        current_turn_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            # We collect the text parts from the agent's events.
            # If the model starts a new turn (e.g. after a tool response),
            # we reset current_turn_text so that full_response_text
            # only contains the final response from the agent.
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        current_turn_text += part.text

                    # If the event indicates a tool call is being made,
                    # it's not the final response yet.
                    if part.function_call:
                        current_turn_text = ""

            # Update the full response with the most recent text block
            if current_turn_text:
                full_response_text = current_turn_text

        if not full_response_text:
            full_response_text = "AI Review completed but no feedback was generated."

        # 6. Post the agent's response back to the PR
        posted = await asyncio.to_thread(client.post_pr_comment, pr_number, full_response_text)
        if posted:
            print("Successfully posted AI review.")
            return True
        else:
            print("Failed to post AI review comment.")
            return False

    except Exception as e:
        error_msg = f"An error occurred during AI review: {str(e)}"
        print(error_msg)
        await asyncio.to_thread(client.post_pr_comment, pr_number, error_msg)
        return False

async def main():
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

    # Logic for Pull Request Events (Label Trigger)
    if event_name in ["pull_request", "pull_request_target"]:
        pr_data = event_data["pull_request"]
        pr_number = pr_data["number"]
        action = event_data.get("action")
        labels = pr_data.get("labels", [])

        target_label_name = "AI Codereview"
        has_ai_label = any(l.get("name", "").lower() == target_label_name.lower() for l in labels)

        should_trigger = False
        # THIS IS THE NAME OF THE ACTION DO NOT CHANGE
        if action == "label_updated":
            if event_data.get("label", {}).get("name", "").lower() == target_label_name.lower():
                should_trigger = True
        # THESE IS THE NAME OF THE ACTION DO NOT CHANGE
        elif action in ["opened", "synchronized"]:
            if has_ai_label:
                should_trigger = True

        if should_trigger:
            print(f"Triggering AI review for PR #{pr_number} (Action: {action})...")
            head_sha = pr_data["head"]["sha"]
            success = await run_ai_review(client, pr_number, google_api_key, head_sha)

            # Remove the label after review completion if it was present
            if has_ai_label:
                actual_label = next((l.get("name") for l in labels if l.get("name", "").lower() == target_label_name.lower()), target_label_name)
                client.remove_label(pr_number, actual_label)

            if not success:
                sys.exit(1)
        else:
            print(f"PR #{pr_number} event (Action: {action}) ignored (AI label not present or not triggered).")

    # Logic for Comment Trigger (#review)
    elif event_name == "issue_comment":
        if "pull_request" not in event_data["issue"]:
            print("Comment is not on a pull request. Ignoring.")
            return

        comment_body = event_data["comment"]["body"].strip()
        if "#review" in comment_body:
            pr_number = event_data["issue"]["number"]
            # Fetch PR details to get the HEAD SHA
            pr_details = client.get_pull_request(pr_number)
            if not pr_details:
                print(f"Could not fetch PR details for #{pr_number}")
                sys.exit(1)

            head_sha = pr_details["head"]["sha"]
            success = await run_ai_review(client, pr_number, google_api_key, head_sha)

            # Remove the label after review completion if it exists
            labels = pr_details.get("labels", [])
            target_label_name = "AI Codereview"
            actual_label = next((l.get("name") for l in labels if l.get("name", "").lower() == target_label_name.lower()), None)
            if actual_label:
                client.remove_label(pr_number, actual_label)

            if not success:
                sys.exit(1)
        else:
            print("Comment does not contain #review. Ignoring.")

    else:
        print(f"Unsupported event type: {event_name}")

if __name__ == "__main__":
    asyncio.run(main())
