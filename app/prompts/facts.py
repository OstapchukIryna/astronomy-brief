# facts.py
SYSTEM = (
    "You extract key facts from a text about an astronomy picture. "
    "Use only the information in the text. Do not add facts that are not in it. "
    "Return 3 to 5 facts. Each fact is one short sentence and is about something different."
)


def user_message(title: str, explanation: str) -> str:
    return f"Title: {title}\n\nText:\n{explanation}"
