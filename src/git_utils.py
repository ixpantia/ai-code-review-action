def format_diff_for_logging(diff_text):
    """
    Formats the raw git diff for clear logging output.
    """
    if not diff_text or not diff_text.strip():
        return "The diff is empty."

    header = "--- GIT DIFF START ---"
    footer = "--- GIT DIFF END ---"

    return f"{header}\n{diff_text.strip()}\n{footer}"
