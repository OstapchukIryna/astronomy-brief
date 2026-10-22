CLASSIFIER_SYSTEM = (
    "You decide whether a reader's question is about an astronomy picture. "
    "You get the picture's title and the question. "
    "The question is on topic if it asks about the picture, the objects in it, "
    "or the astronomy and physics around them. "
    'Answer with JSON only: {"on_topic": true} or {"on_topic": false}.'
)

ANSWER_SYSTEM = (
    "You answer a reader's question about an astronomy picture. "
    "You get NASA's description of the picture. Use it first, and add "
    "well-established facts only where the description is not enough. "
    "If you are not sure, say so instead of guessing. "
    "Answer in English, in up to 3 short sentences, in plain words without jargon."
)


def classifier_message(title: str, question: str) -> str:
    return f"Title: {title}\n\nQuestion:\n{question}"


def answer_message(title: str, explanation: str, question: str) -> str:
    return f"Title: {title}\n\nText:\n{explanation}\n\nQuestion:\n{question}"
