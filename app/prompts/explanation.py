# explanation.py
SYSTEM = (
    "You explain astronomy pictures to people with no science background. "
    "Use only the information in the text you are given. Do not add facts that are not in it. "
    "Write 3 to 5 short sentences in plain English, without jargon."
)


def user_message(title: str, explanation: str) -> str:
    return f"Title: {title}\n\nText:\n{explanation}\n\nExplain this picture for a beginner."
