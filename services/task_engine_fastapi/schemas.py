from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    QUIZ = "quiz"  # 选择/填空
    SHORT_ANSWER = "short_answer"  # 简答题
    GROUP_TASK = "group_task"  # 小组任务
    PBL = "pbl"  # 探究任务


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SubmissionStatus(str, Enum):
    SUBMITTED = "submitted"
    GRADED = "graded"


class TaskOption(BaseModel):
    key: str
    text: str


class TaskQuestion(BaseModel):
    question_id: str
    prompt: str
    answer_type: str = Field(
        description="single_choice | multiple_choice | fill_blank | short_text"
    )
    options: list[TaskOption] = Field(default_factory=list)
    standard_answer: str | list[str] | None = None
    score: float = 1.0
    rubric: str | None = None


class Task(BaseModel):
    task_id: str
    class_id: str
    scene_id: str | None = None
    knowledge_point: str
    type: TaskType
    title: str
    instructions: str
    difficulty: Difficulty = Difficulty.MEDIUM
    questions: list[TaskQuestion] = Field(default_factory=list)
    group_size: int | None = None
    due_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "teacher-agent"


class SubmissionAnswer(BaseModel):
    question_id: str
    answer: str | list[str]


class Submission(BaseModel):
    submission_id: str
    task_id: str
    student_id: str
    class_id: str
    answers: list[SubmissionAnswer] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    status: SubmissionStatus = SubmissionStatus.SUBMITTED
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class ErrorPattern(BaseModel):
    category: str
    reason: str
    advice: str
    related_knowledge_points: list[str] = Field(default_factory=list)


class Result(BaseModel):
    result_id: str
    submission_id: str
    task_id: str
    student_id: str
    score: float
    max_score: float
    pass_threshold: float = 0.6
    passed: bool
    feedback: str
    per_question: dict[str, float] = Field(default_factory=dict)
    wrong_analysis: list[ErrorPattern] = Field(default_factory=list)
    grader: str = "hybrid-rule-llm"
    graded_at: datetime = Field(default_factory=datetime.utcnow)


class GenerateTaskRequest(BaseModel):
    class_id: str
    scene_id: str | None = None
    teacher_id: str
    knowledge_point: str
    task_type: TaskType
    lesson_objective: str | None = None
    difficulty: Difficulty = Difficulty.MEDIUM
    language: str = "zh-CN"
    count: int = 1


class GradeRequest(BaseModel):
    task_id: str
    submission_id: str
    use_llm: bool = True
    language: str = "zh-CN"

