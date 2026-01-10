import os
import json
import sys
import asyncio
from google.adk.runners import InMemoryRunner
from google.genai import types
from src.forgejo import ForgejoClient
from src.git_utils import format_diff_for_logging
from src.agent import create_review_agent

async def run_ai_review(client, pr_number, google_api_key):
    """ Helper function to execute the AI review process using ADK InMemoryRunner. """
    print(f"Triggering AI Review for PR #{pr_number}...")

    if not google_api_key:
        error_msg = "Error: GOOGLE_API_KEY is not set. Please check your action configuration and secrets."
        print(error_msg)
        await asyncio.to_thread(client.post_pr_comment, pr_number, error_msg)
        return False

    # 1. Initialize the Agent
    agent = create_review_agent(client, pr_number)

    # 2. Setup the Runner
    app_name = "ix-code-review-bot"
    runner = InMemoryRunner(agent, app_name=app_name)

    try:
        user_id = "forgejo-bot"
        session_id = f"pr-{pr_number}"

        # 3. Ensure the session is created (create_session is a coroutine in ADK)
        await runner.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

        # 4. Prepare the initial message
        new_message = types.Content(
            parts=[types.Part(text="Please review the changes in this pull request and provide your feedback.")]
        )

        # 5. Execute the agent via run_async (the primary way to run in an async context)
        full_response_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            # The agent is instructed to provide *only* the final Markdown comment.
            # We capture the last text part, assuming it's the complete final response.
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        # Overwrite to ensure we only keep the latest text from the agent
                        full_response_text = part.text

        if not full_response_text:
            full_response_text = "AI Review completed but no feedback was generated."
        else:
            # Clean up the response to extract only markdown if the model wrapped it in code blocks
            full_response_text = full_response_text.strip()
            if full_response_text.startswith("```markdown"):
                full_response_text = full_response_text.removeprefix("```markdown").removesuffix("```").strip()
            elif full_response_text.startswith("```"):
                full_response_text = full_response_text.removeprefix("```").removesuffix("```").strip()

        # 6. Post the agent's response back to the PR
        # Wrapping sync client call in to_thread to keep main loop responsive
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

    # Logic for Comment Trigger (#review)
    if event_name == "issue_comment":
        if "pull_request" not in event_data["issue"]:
            print("Comment is not on a pull request. Ignoring.")
            return

        comment_body = event_data["comment"]["body"].strip()
        if "#review" in comment_body:
            pr_number = event_data["issue"]["number"]
            success = await run_ai_review(client, pr_number, google_api_key)
            if not success:
                sys.exit(1)
        else:
            print("Comment does not contain #review. Ignoring.")

    else:
        print(f"Unsupported event type: {event_name}")

if __name__ == "__main__":
    asyncio.run(main())
