from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AbilityTag(str, Enum):
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"


@dataclass
class KnowledgeMastery:
    knowledge_point: str
    mastery_score: float = 0.0  # 0~100
    evidence_count: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    last_result_score: float | None = None
    last_seen_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WrongQuestionRecord:
    wrong_id: str
    task_id: str
    question_id: str
    knowledge_point: str
    error_category: str
    student_answer: str
    standard_answer: str
    error_reason: str
    remediation_tip: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False


@dataclass
class AbilityVector:
    understand: float = 0.0
    apply: float = 0.0
    analyze: float = 0.0


@dataclass
class StudentProfile:
    student_id: str
    class_id: str
    display_name: str
    grade_level: str | None = None
    learning_goal: str | None = None
    mastery_overall: float = 0.0
    trend_7d: float = 0.0
    trend_30d: float = 0.0
    ability: AbilityVector = field(default_factory=AbilityVector)
    knowledge_mastery: dict[str, KnowledgeMastery] = field(default_factory=dict)
    wrong_questions: list[WrongQuestionRecord] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskResultEvent:
    event_id: str
    student_id: str
    class_id: str
    task_id: str
    knowledge_point: str
    score: float
    max_score: float
    error_categories: list[str]
    ability_weight: dict[AbilityTag, float]  # e.g. {UNDERSTAND:0.6, APPLY:0.3, ANALYZE:0.1}
    occurred_at: datetime = field(default_factory=datetime.utcnow)

