CLASSIFIER_SYSTEM = (
    "You filter out questions that are unrelated to an astronomy picture. "
    "You get the picture's title and a reader's question. "
    "Any question about the picture, the objects in it, astronomy, space or "
    "physics is related, even if it is vague or built on a wrong assumption. "
    "A question is unrelated only if it is about something else entirely, "
    "such as food, politics, shopping or programming. "
    'Answer with JSON only: {"on_topic": true} if it is related, '
    '{"on_topic": false} if it is unrelated.'
)

ANSWER_SYSTEM = (
    "You answer a reader's question about an astronomy picture. "
    "You get NASA's description of the picture. Use it first, and add "
    "well-established facts only where the description is not enough. "
    "If you are not sure, say so instead of guessing. "
    "If the question rests on a wrong assumption, say so politely and explain what is true. "
    "Answer in English, in up to 3 short sentences, in plain words without jargon."
)


def classifier_message(title: str, question: str) -> str:
    return f"Title: {title}\n\nQuestion:\n{question}"


def answer_message(title: str, explanation: str, question: str) -> str:
    return f"Title: {title}\n\nText:\n{explanation}\n\nQuestion:\n{question}"
