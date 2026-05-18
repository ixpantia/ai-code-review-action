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
    Eres un ingeniero de software experto realizando una revisión de código.

    Tu objetivo es proporcionar retroalimentación constructiva sobre el Pull Request proporcionado.
    Responde siempre en español.

    Sigue estos pasos en orden:
    1. Llama a 'get_pull_request_diff' para obtener el diff completo y entender qué cambió.
    2. Siempre llama a 'get_general_review_checklist' y aplica cada punto al review.
    3. Según las extensiones de archivo y el contenido del diff, decide qué checklists especializados aplican:
       - Si el diff incluye código SQL o archivos .sql, llama a 'get_sql_review_checklist' y aplica cada punto.
       - Si el diff incluye código R o archivos .R / .Rmd, llama a 'get_r_review_checklist' y aplica cada punto.
       - Es válido llamar a ambos, uno o ninguno según lo que haya en el diff.
    4. Si necesitas más contexto sobre un archivo específico, usa 'read_file_content'.
    5. Para cada punto del checklist, indica si el código pasa o falla, y explica el motivo de los fallos.
    6. También señala cualquier problema general no cubierto por los checklists (errores de lógica, vulnerabilidades de seguridad, rendimiento, etc.).

    Presenta los hallazgos de forma estructurada, agrupados por checklist / categoría.
    """

    reviewer = Agent(
        model='gemini-2.0-flash',
        name='reviewer',
        description="Analiza el PR e identifica problemas usando checklists específicos por lenguaje.",
        instruction=reviewer_instruction,
        tools=[read_file_content, get_pull_request_diff, get_general_review_checklist, get_sql_review_checklist, get_r_review_checklist],
        output_key="review_findings"
    )

    # 2. The Formatter Agent: Ensures the final output is extracted into a specific schema.
    # The {review_findings} placeholder is automatically populated from the session state by ADK.
    formatter_instruction = """
    Eres un editor técnico. Se te proporcionarán los hallazgos de una revisión de código.
    Tu tarea es transformar esos hallazgos en un comentario profesional en Markdown para un Pull Request.
    Responde siempre en español.

    HALLAZGOS A FORMATEAR:
    {review_findings}

    REGLAS CRÍTICAS:
    1. El campo 'markdown_content' debe contener ÚNICAMENTE el markdown que deseas publicar.
    2. NO incluyas texto introductorio ni relleno conversacional (ej: "Aquí está el review", "De acuerdo, veo que...").
    3. NO envuelvas el contenido en bloques de código markdown como ```markdown en el campo final.
    4. Usa encabezados claros, viñetas y bloques de código dentro del markdown para mayor legibilidad.
    5. Si los hallazgos indican que el código está bien, dilo de forma concisa.
    """

    formatter = Agent(
        model='gemini-2.0-flash',
        name='formatter',
        description="Formatea los hallazgos del review en un esquema JSON limpio.",
        instruction=formatter_instruction,
        output_schema=ReviewOutput,
        output_key="final_review"
    )

    # The SequentialAgent runs them in order.
    return SequentialAgent(
        name='code_review_pipeline',
        sub_agents=[reviewer, formatter]
    )
