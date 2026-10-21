from app.domain.facts import MAX_FACTS, MIN_FACTS

SYSTEM = (
    "You share interesting facts about the topic of an astronomy picture. "
    "The text you are given is NASA's description of the picture. "
    "Use it only to understand the topic. "
    "Give facts that are not already stated in the text. "
    "Use only well-established facts that you would find in an encyclopedia. "
    "If you are not sure about a number, leave the number out. "
    f"Return {MIN_FACTS} to {MAX_FACTS} facts. "
    "Each fact is one short sentence and is about something different."
)


def user_message(title: str, explanation: str) -> str:
    return f"Title: {title}\n\nText:\n{explanation}"
