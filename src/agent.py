from google.adk.agents.llm_agent import Agent
from .forgejo import ForgejoClient

def create_review_agent(client: ForgejoClient, pr_number: int, head_sha: str):
    """
    Creates an ADK agent configured for code review.
    """

    def read_file_content(path: str) -> str:
        """
        Reads the content of a file from the repository at the given path using the Forgejo API.
        Useful for getting more context about the changes in the diff.
        """
        content = client.get_file_content(path, head_sha)
        if content is None:
            return f"Error: Could not retrieve file content for {path} at {head_sha}"
        return content

    def get_conversation() -> str:
        """
        Returns the full comment conversation in the pull request.
        Useful to understand context from previous discussions.
        """
        comments = client.get_pr_comments(pr_number)
        if not comments:
            return "No comments in this pull request yet."

        formatted_comments = []
        for c in comments:
            user = c.get("user", {}).get("login", "unknown")
            body = c.get("body", "")
            formatted_comments.append(f"[{user}]: {body}")

        return "\n---\n".join(formatted_comments)

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
    2. Use 'get_conversation' to understand the context of the PR and any previous feedback or discussions.
    3. If you need more context to understand a change, use 'read_file_content' to see the full file.
    4. Look for:
       - Logic errors or bugs.
       - Security vulnerabilities.
       - Performance improvements.
       - Code style and readability issues.
       - Missing tests or documentation.

    IMPORTANT: Your response MUST contain ONLY the professional Markdown feedback to be posted as a comment.
    Do not include any conversational filler, meta-talk, or descriptions of your internal process.
    Start your final response directly with the review content.
    Be concise but thorough. If the code looks great, say so!
    """

    # Note: Ensure GOOGLE_API_KEY is set in the environment
    agent = Agent(
        model='gemini-2.0-flash',
        name='code_reviewer',
        description="An agent that reviews code changes in a Pull Request.",
        instruction=instruction,
        tools=[read_file_content, get_pull_request_diff, get_conversation],
    )

    return agent
