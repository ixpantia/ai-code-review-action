import os
from google.adk.agents.llm_agent import Agent
from .forgejo import ForgejoClient

def create_review_agent(client: ForgejoClient, pr_number: int):
    """
    Creates an ADK agent configured for code review.
    """

    def read_file_content(path: str) -> str:
        """
        Reads the content of a file from the repository at the given path.
        Useful for getting more context about the changes in the diff.
        """
        # In a CI environment, the repo is usually checked out at GITHUB_WORKSPACE
        workspace = os.getenv("GITHUB_WORKSPACE", ".")
        full_path = os.path.join(workspace, path)

        try:
            if not os.path.isfile(full_path):
                return f"Error: File not found at {path}"

            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def get_pull_request_diff() -> str:
        """
        Returns the full git diff of the current pull request.
        """
        diff = client.get_pr_diff(pr_number)
        return diff if diff else "Error: Could not retrieve diff."

    instruction = """
    You are an expert software engineer performing a code review.

    Your goal is to provide constructive feedback on the provided Pull Request.
    1. Start by reviewing the 'git diff' to understand what changed.
    2. If you need more context to understand a change, use 'read_file_content' to see the full file.
    3. Look for:
       - Logic errors or bugs.
       - Security vulnerabilities.
       - Performance improvements.
       - Code style and readability issues.
       - Missing tests or documentation.

    Format your response as a professional Markdown comment for the Pull Request.
    Be concise but thorough. If the code looks great, say so!

    IMPORTANT: Your response MUST consist ONLY of the final Markdown content you wish to post as a comment. Do not include any introductory text, thought process, or conversational filler like "Okay, I'm ready to review..." or "Here's my feedback:". Output only the Markdown.
    """

    # Note: Ensure GOOGLE_API_KEY is set in the environment
    agent = Agent(
        model='gemini-2.0-flash',
        name='code_reviewer',
        description="An agent that reviews code changes in a Pull Request.",
        instruction=instruction,
        tools=[read_file_content, get_pull_request_diff],
    )

    return agent
