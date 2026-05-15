import os
from pydantic import BaseModel
from google.adk.agents.llm_agent import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from .forgejo import ForgejoClient

_CHECKLISTS_DIR = os.path.join(os.path.dirname(__file__), "..", "code_reviews")

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

    def get_general_review_checklist() -> str:
        """
        Returns the general code review checklist that applies to every pull request,
        regardless of the programming language. Always call this tool.
        """
        checklist_path = os.path.join(_CHECKLISTS_DIR, "..", "code_review_general.md")
        try:
            with open(checklist_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading general checklist: {str(e)}"

    def get_sql_review_checklist() -> str:
        """
        Returns the SQL code review checklist.
        Call this tool when the pull request contains SQL code (e.g. .sql files or SQL queries).
        Use the returned checklist to guide your SQL-specific review findings.
        """
        checklist_path = os.path.join(_CHECKLISTS_DIR, "code_review_SQL.md")
        try:
            with open(checklist_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading SQL checklist: {str(e)}"

    def get_r_review_checklist() -> str:
        """
        Returns the R code review checklist.
        Call this tool when the pull request contains R code (e.g. .R or .Rmd files).
        Use the returned checklist to guide your R-specific review findings.
        """
        checklist_path = os.path.join(_CHECKLISTS_DIR, "code_review_R.md")
        try:
            with open(checklist_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading R checklist: {str(e)}"

    # 1. The Reviewer Agent: Focuses on finding issues and generating content.
    reviewer_instruction = """
    You are an expert software engineer performing a code review.

    Your goal is to provide constructive feedback on the provided Pull Request.

    Follow these steps in order:
    1. Call 'get_pull_request_diff' to retrieve the full diff and understand what changed.
    2. Always call 'get_general_review_checklist' and apply every item to the review.
    3. Based on the file extensions and content in the diff, decide which specialised checklists apply:
       - If the diff includes SQL code or .sql files, call 'get_sql_review_checklist' and apply every item.
       - If the diff includes R code or .R / .Rmd files, call 'get_r_review_checklist' and apply every item.
       - It is valid to call both, one, or neither depending on what is actually present.
    4. If you need more context about a specific file, use 'read_file_content'.
    5. For each checklist item, note whether the code passes or fails, and explain why for any failures.
    6. Also flag any general issues not covered by the checklists (logic errors, security vulnerabilities, performance, etc.).

    Provide your findings in a structured way, grouped by checklist / category.
    """

    reviewer = Agent(
        model='gemini-2.0-flash',
        name='reviewer',
        description="Analyzes the PR and identifies issues using language-specific checklists.",
        instruction=reviewer_instruction,
        tools=[read_file_content, get_pull_request_diff, get_general_review_checklist, get_sql_review_checklist, get_r_review_checklist],
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
