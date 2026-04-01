from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from models import AbilityTag, StudentProfile, TaskResultEvent
from update_logic import (
    build_student_rag_context,
    default_recent_scores,
    update_student_profile_after_task,
)

app = FastAPI(title="EduClaw Student Model API", version="0.1.0")

# Demo in-memory store（生产请换数据库）
STUDENTS: dict[str, StudentProfile] = {}


class UpsertProfileRequest(BaseModel):
    student_id: str
    class_id: str
    display_name: str
    grade_level: str | None = None
    learning_goal: str | None = None


class UpdateFromTaskRequest(BaseModel):
    student_id: str
    class_id: str
    task_id: str
    knowledge_point: str
    score: float
    max_score: float
    error_categories: list[str] = []
    # 权重：理解/应用/分析
    w_understand: float = 0.6
    w_apply: float = 0.3
    w_analyze: float = 0.1


@app.get("/v1/student-model/{student_id}")
def get_student_profile(student_id: str) -> dict:
    profile = STUDENTS.get(student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return {
        "profile": profile,
        "rag_context": build_student_rag_context(profile),
    }


@app.post("/v1/student-model")
def upsert_student_profile(payload: UpsertProfileRequest) -> StudentProfile:
    profile = STUDENTS.get(payload.student_id)
    if not profile:
        profile = StudentProfile(
            student_id=payload.student_id,
            class_id=payload.class_id,
            display_name=payload.display_name,
            grade_level=payload.grade_level,
            learning_goal=payload.learning_goal,
        )
    else:
        profile.class_id = payload.class_id
        profile.display_name = payload.display_name
        profile.grade_level = payload.grade_level
        profile.learning_goal = payload.learning_goal
        profile.updated_at = datetime.utcnow()

    STUDENTS[payload.student_id] = profile
    return profile


@app.post("/v1/student-model/{student_id}:update-from-task")
def update_profile_from_task(student_id: str, payload: UpdateFromTaskRequest) -> dict:
    profile = STUDENTS.get(student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    event = TaskResultEvent(
        event_id=f"evt_{uuid4().hex[:10]}",
        student_id=student_id,
        class_id=payload.class_id,
        task_id=payload.task_id,
        knowledge_point=payload.knowledge_point,
        score=payload.score,
        max_score=payload.max_score,
        error_categories=payload.error_categories,
        ability_weight={
            AbilityTag.UNDERSTAND: payload.w_understand,
            AbilityTag.APPLY: payload.w_apply,
            AbilityTag.ANALYZE: payload.w_analyze,
        },
    )
    recent_7d_scores = default_recent_scores(7, base=profile.mastery_overall or 60.0)
    recent_30d_scores = default_recent_scores(30, base=profile.mastery_overall or 60.0)
    profile = update_student_profile_after_task(
        profile,
        event,
        recent_7d_scores=recent_7d_scores,
        recent_30d_scores=recent_30d_scores,
    )
    STUDENTS[student_id] = profile

    return {
        "student_id": student_id,
        "mastery_overall": profile.mastery_overall,
        "trend_7d": profile.trend_7d,
        "trend_30d": profile.trend_30d,
        "ability": profile.ability,
        "rag_context": build_student_rag_context(profile),
    }
