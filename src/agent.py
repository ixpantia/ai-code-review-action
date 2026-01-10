import os
from pydantic import BaseModel
from google.adk.agents.llm_agent import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from .forgejo import ForgejoClient

class ReviewOutput(BaseModel):
    markdown_content: str

def create_review_agent(client: ForgejoClient, pr_number: int):
    """
    Creates a SequentialAgent that first reviews the code and then formats the output
    into a clean schema to avoid conversational filler or markdown wrapping issues.
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

    # 1. The Reviewer Agent: Focuses on finding issues and generating content.
    reviewer_instruction = """
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

    Provide your findings in a structured way.
    """

    reviewer = Agent(
        model='gemini-2.0-flash',
        name='reviewer',
        description="Analyzes the PR and identifies issues.",
        instruction=reviewer_instruction,
        tools=[read_file_content, get_pull_request_diff],
        output_key="review_findings"
    )

    # 2. The Formatter Agent: Ensures the final output is extracted into a specific schema.
    # The {review_findings} placeholder is automatically populated from the session state by ADK.
    formatter_instruction = """
    You are a technical editor. You will be provided with code review findings.
    Your task is to transform these findings into a professional Markdown comment for a Pull Request.

    FINDINGS TO FORMAT:
    {review_findings}

    CRITICAL RULES:
    1. The 'markdown_content' field must contain ONLY the markdown you wish to post.
    2. DO NOT include any introductory text or conversational filler (e.g., "Here is the review", "Okay, I see...").
    3. DO NOT wrap the content in markdown code blocks like ```markdown in the final field.
    4. Use clear headings, bullet points, and code blocks within the markdown for readability.
    5. If the findings indicate the code is great, just say so concisely.
    """

    formatter = Agent(
        model='gemini-2.0-flash',
        name='formatter',
        description="Formats review findings into a clean JSON schema.",
        instruction=formatter_instruction,
        output_schema=ReviewOutput,
        output_key="final_review"
    )

    # The SequentialAgent runs them in order.
    return SequentialAgent(
        name='code_review_pipeline',
        sub_agents=[reviewer, formatter]
    )
