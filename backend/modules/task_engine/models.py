from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    QUIZ = "quiz"
    SHORT_ANSWER = "short_answer"
    GROUP_TASK = "group_task"
    PBL = "pbl"


class TaskStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class SubmissionStatus(str, Enum):
    SUBMITTED = "submitted"
    GRADED = "graded"


class TaskQuestion(BaseModel):
    question_id: str
    prompt: str
    answer_type: str = Field(
        description="single_choice | multiple_choice | fill_blank | short_text"
    )
    options: list[str] = Field(default_factory=list)
    standard_answer: str | list[str] | None = None
    score: float = 1.0


class Task(BaseModel):
    task_id: str
    class_id: str
    title: str
    task_type: TaskType
    knowledge_point: str
    instructions: str
    questions: list[TaskQuestion] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PUBLISHED
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SubmissionAnswer(BaseModel):
    question_id: str
    answer: str | list[str]


class Submission(BaseModel):
    submission_id: str
    task_id: str
    student_id: str
    class_id: str
    answers: list[SubmissionAnswer]
    status: SubmissionStatus = SubmissionStatus.SUBMITTED
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class Result(BaseModel):
    result_id: str
    task_id: str
    submission_id: str
    student_id: str
    score: float
    max_score: float
    passed: bool
    feedback: str
    graded_at: datetime = Field(default_factory=datetime.utcnow)

