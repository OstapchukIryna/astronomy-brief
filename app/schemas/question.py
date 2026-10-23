import datetime as dt

from pydantic import BaseModel


class QuestionRequest(BaseModel):
    date: dt.date
    question: str


class AnswerResponse(BaseModel):
    date: dt.date
    answer: str
