from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from schemas import (
    ErrorPattern,
    GenerateTaskRequest,
    GradeRequest,
    Result,
    Submission,
    SubmissionStatus,
    Task,
    TaskQuestion,
    TaskType,
)

app = FastAPI(title="EduClaw Task Engine", version="0.1.0")

# In-memory store demo (建议落地替换为 Postgres/Redis)
TASKS: dict[str, Task] = {}
SUBMISSIONS: dict[str, Submission] = {}
RESULTS: dict[str, Result] = {}
TASK_BY_CLASS: dict[str, list[str]] = defaultdict(list)


def _model_name() -> str:
    return os.getenv("TASK_ENGINE_MODEL", "gpt-4o-mini")


def _openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM generation/grading.")
    return OpenAI(api_key=api_key, base_url=base_url)


def generate_task_with_llm(payload: GenerateTaskRequest) -> list[Task]:
    """
    基于知识点自动生成课堂任务（支持 quiz/short answer/group/pbl）。
    可被 EduClaw 的 classroom orchestrator 在“讲完知识点”后触发。
    """
    system_prompt = (
        "You are an expert K12 instructional designer. "
        "Generate classroom tasks in strict JSON only."
    )
    user_prompt = f"""
请基于以下教学信息生成任务（只返回 JSON 数组，不要 markdown）：
- class_id: {payload.class_id}
- scene_id: {payload.scene_id}
- knowledge_point: {payload.knowledge_point}
- task_type: {payload.task_type.value}
- lesson_objective: {payload.lesson_objective}
- difficulty: {payload.difficulty.value}
- language: {payload.language}
- count: {payload.count}

JSON schema:
[
  {{
    "title": "string",
    "instructions": "string",
    "difficulty": "easy|medium|hard",
    "group_size": 4,
    "questions": [
      {{
        "question_id": "q1",
        "prompt": "string",
        "answer_type": "single_choice|multiple_choice|fill_blank|short_text",
        "options": [{{"key":"A","text":"..."}}],
        "standard_answer": "A 或文本",
        "score": 5,
        "rubric": "评分标准"
      }}
    ],
    "metadata": {{
      "knowledge_tags": ["..."],
      "estimated_minutes": 8
    }}
  }}
]
"""
    client = _openai_client()
    response = client.chat.completions.create(
        model=_model_name(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    text = response.choices[0].message.content or "[]"
    generated = json.loads(text)

    tasks: list[Task] = []
    for item in generated:
        task = Task(
            task_id=f"task_{uuid4().hex[:10]}",
            class_id=payload.class_id,
            scene_id=payload.scene_id,
            knowledge_point=payload.knowledge_point,
            type=payload.task_type,
            title=item.get("title", f"{payload.knowledge_point} - {payload.task_type.value}"),
            instructions=item.get("instructions", ""),
            difficulty=item.get("difficulty", payload.difficulty),
            group_size=item.get("group_size"),
            questions=[TaskQuestion(**q) for q in item.get("questions", [])],
            metadata=item.get("metadata", {}),
            due_at=datetime.utcnow() + timedelta(minutes=20),
            created_by=payload.teacher_id,
        )
        TASKS[task.task_id] = task
        TASK_BY_CLASS[payload.class_id].append(task.task_id)
        tasks.append(task)
    return tasks


def _rule_based_grade(task: Task, submission: Submission) -> tuple[float, dict[str, float], float]:
    question_map = {q.question_id: q for q in task.questions}
    answer_map = {a.question_id: a.answer for a in submission.answers}
    per_question: dict[str, float] = {}
    max_score = 0.0
    earned = 0.0

    for qid, q in question_map.items():
        max_score += q.score
        student_answer = answer_map.get(qid)
        score = 0.0
        if q.answer_type in {"single_choice", "fill_blank"}:
            if student_answer is not None and q.standard_answer is not None:
                if str(student_answer).strip().lower() == str(q.standard_answer).strip().lower():
                    score = q.score
        elif q.answer_type == "multiple_choice":
            if isinstance(student_answer, list) and isinstance(q.standard_answer, list):
                if sorted(student_answer) == sorted(q.standard_answer):
                    score = q.score
        else:
            # short_text / group / pbl 的文本题由 LLM 评分补充
            score = 0.0

        per_question[qid] = score
        earned += score
    return earned, per_question, max_score


def llm_grade_and_analyze(task: Task, submission: Submission, current_score: float) -> dict[str, Any]:
    """
    对简答题/探究题做 AI 补充评分 + 错因分析。
    """
    system_prompt = (
        "You are a strict but constructive K12 grader. "
        "Return strict JSON only."
    )
    user_prompt = f"""
任务信息:
{task.model_dump_json(indent=2, ensure_ascii=False)}

学生提交:
{submission.model_dump_json(indent=2, ensure_ascii=False)}

当前规则分:
{current_score}

请输出 JSON:
{{
  "score_delta": 0.0,
  "feedback": "整体反馈",
  "per_question_delta": {{"q1": 1.5}},
  "wrong_analysis": [
    {{
      "category": "概念混淆|计算错误|表达不完整|审题偏差",
      "reason": "原因",
      "advice": "改进建议",
      "related_knowledge_points": ["知识点1"]
    }}
  ]
}}
"""
    client = _openai_client()
    response = client.chat.completions.create(
        model=_model_name(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content or "{}")


@app.get("/v1/tasks")
def list_tasks(class_id: str) -> list[Task]:
    task_ids = TASK_BY_CLASS.get(class_id, [])
    return [TASKS[tid] for tid in task_ids]


@app.post("/v1/tasks:generate")
def generate_tasks(payload: GenerateTaskRequest) -> list[Task]:
    try:
        return generate_task_with_llm(payload)
    except Exception as exc:  # noqa: BLE001 - API boundary
        raise HTTPException(status_code=500, detail=f"Task generation failed: {exc}") from exc


@app.get("/v1/tasks/{task_id}")
def get_task(task_id: str) -> Task:
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/v1/tasks/{task_id}/submissions")
def submit_task(task_id: str, payload: Submission) -> Submission:
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    if payload.task_id != task_id:
        raise HTTPException(status_code=400, detail="task_id mismatch")
    SUBMISSIONS[payload.submission_id] = payload
    return payload


@app.post("/v1/results:grade")
def grade_submission(payload: GradeRequest) -> Result:
    task = TASKS.get(payload.task_id)
    submission = SUBMISSIONS.get(payload.submission_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    rule_score, per_question, max_score = _rule_based_grade(task, submission)
    feedback = "规则评分完成。"
    wrong_analysis: list[ErrorPattern] = []

    if payload.use_llm:
        try:
            llm_result = llm_grade_and_analyze(task, submission, rule_score)
            score_delta = float(llm_result.get("score_delta", 0.0))
            for qid, delta in llm_result.get("per_question_delta", {}).items():
                per_question[qid] = max(0.0, per_question.get(qid, 0.0) + float(delta))
            rule_score = max(0.0, min(max_score, rule_score + score_delta))
            feedback = llm_result.get("feedback", feedback)
            wrong_analysis = [ErrorPattern(**i) for i in llm_result.get("wrong_analysis", [])]
        except Exception:
            feedback = "规则评分完成；AI评分失败，已回退规则结果。"

    score_ratio = (rule_score / max_score) if max_score > 0 else 0.0
    result = Result(
        result_id=f"res_{uuid4().hex[:10]}",
        submission_id=submission.submission_id,
        task_id=task.task_id,
        student_id=submission.student_id,
        score=round(rule_score, 2),
        max_score=max_score,
        passed=score_ratio >= 0.6,
        feedback=feedback,
        per_question=per_question,
        wrong_analysis=wrong_analysis,
    )
    RESULTS[result.result_id] = result

    submission.status = SubmissionStatus.GRADED
    SUBMISSIONS[submission.submission_id] = submission
    return result


class AgentEvent(BaseModel):
    class_id: str
    scene_id: str | None = None
    knowledge_point: str
    teacher_id: str
    event_type: str = "knowledge_taught"
    task_type: TaskType = TaskType.QUIZ


@app.post("/v1/agent-events/knowledge-taught")
def on_knowledge_taught(payload: AgentEvent) -> dict[str, Any]:
    """
    与 Agent Engine 交互入口：
    当 teacher agent 完成知识点讲授时，直接触发任务生成。
    """
    req = GenerateTaskRequest(
        class_id=payload.class_id,
        scene_id=payload.scene_id,
        teacher_id=payload.teacher_id,
        knowledge_point=payload.knowledge_point,
        task_type=payload.task_type,
        count=1,
    )
    tasks = generate_task_with_llm(req)
    return {"generated_task_ids": [t.task_id for t in tasks], "count": len(tasks)}


@app.get("/v1/results/{result_id}")
def get_result(result_id: str) -> Result:
    result = RESULTS.get(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result
