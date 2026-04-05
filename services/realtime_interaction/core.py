from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
from openai import OpenAI

from prompts import (
    CLASS_SUMMARY_SYSTEM,
    REALTIME_ANALYSIS_SYSTEM,
    build_class_summary_user_prompt,
    build_realtime_analysis_user_prompt,
)


@dataclass
class LiveClassContext:
    class_id: str
    teacher_id: str
    course_name: str
    grade_level: str
    transcript_buffer: list[str] = field(default_factory=list)
    interaction_events: list[dict[str, Any]] = field(default_factory=list)
    latest_summary: str = ""


def _openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return OpenAI(api_key=api_key, base_url=base_url)


def _model_name() -> str:
    return os.getenv("REALTIME_MODEL", "gpt-4o-mini")


async def trigger_task_engine(
    *,
    task_engine_base_url: str,
    class_id: str,
    scene_id: str | None,
    teacher_id: str,
    knowledge_point: str,
    task_type: str,
) -> dict[str, Any]:
    """
    调用 Task Engine：讲完知识点后自动触发任务。
    对接 endpoint: POST /v1/agent-events/knowledge-taught
    """
    payload = {
        "class_id": class_id,
        "scene_id": scene_id,
        "knowledge_point": knowledge_point,
        "teacher_id": teacher_id,
        "event_type": "knowledge_taught",
        "task_type": task_type,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{task_engine_base_url.rstrip('/')}/v1/agent-events/knowledge-taught",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


def analyze_teaching_chunk(
    transcript_chunk: str,
    *,
    course_name: str,
    grade_level: str,
    recent_summary: str,
) -> dict[str, Any]:
    """
    核心函数1：实时生成问题 + 理解风险分析 + 任务触发建议。
    """
    client = _openai_client()
    user_prompt = build_realtime_analysis_user_prompt(
        transcript_chunk,
        course_name=course_name,
        grade_level=grade_level,
        recent_summary=recent_summary,
    )
    response = client.chat.completions.create(
        model=_model_name(),
        messages=[
            {"role": "system", "content": REALTIME_ANALYSIS_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content or "{}")


def estimate_student_understanding(
    analysis: dict[str, Any],
    quick_poll_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    核心函数2：融合 LLM 风险评分与学生快答反馈，判断理解情况。
    """
    llm_risk = float(analysis.get("understanding_risk", 0.0))
    poll_wrong_rate = float((quick_poll_result or {}).get("wrong_rate", 0.0))
    final_risk = min(1.0, max(0.0, llm_risk * 0.7 + poll_wrong_rate * 0.3))

    level = "low"
    if final_risk >= 0.7:
        level = "high"
    elif final_risk >= 0.4:
        level = "medium"

    return {
        "risk_level": level,
        "risk_score": round(final_risk, 3),
        "reason": analysis.get("risk_reason", ""),
    }


async def handle_live_chunk(
    context: LiveClassContext,
    transcript_chunk: str,
    *,
    scene_id: str | None,
    task_engine_base_url: str,
    quick_poll_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    核心函数3：单个实时片段处理总控。
    流程：STT文本 -> LLM分析 -> 理解评估 -> 条件触发Task Engine -> 返回老师提示。
    """
    context.transcript_buffer.append(transcript_chunk)
    analysis = analyze_teaching_chunk(
        transcript_chunk,
        course_name=context.course_name,
        grade_level=context.grade_level,
        recent_summary=context.latest_summary,
    )
    understanding = estimate_student_understanding(analysis, quick_poll_result)

    task_trigger_result: dict[str, Any] | None = None
    should_trigger = bool(analysis.get("should_trigger_task", False)) or (
        understanding["risk_level"] in {"medium", "high"}
    )
    if should_trigger:
        knowledge_points = analysis.get("knowledge_points", [])
        knowledge_point = knowledge_points[0] if knowledge_points else "课堂关键知识点"
        task_type = analysis.get("recommended_task_type", "quiz")
        try:
            task_trigger_result = await trigger_task_engine(
                task_engine_base_url=task_engine_base_url,
                class_id=context.class_id,
                scene_id=scene_id,
                teacher_id=context.teacher_id,
                knowledge_point=knowledge_point,
                task_type=task_type,
            )
        except Exception as exc:  # noqa: BLE001 - runtime integration boundary
            task_trigger_result = {"error": str(exc)}

    event = {
        "ts": datetime.utcnow().isoformat(),
        "analysis": analysis,
        "understanding": understanding,
        "task_trigger_result": task_trigger_result,
    }
    context.interaction_events.append(event)
    context.latest_summary = analysis.get("teacher_tip", context.latest_summary)
    return event


def summarize_class(context: LiveClassContext) -> dict[str, Any]:
    """
    核心函数4：课后自动生成课堂总结（知识点、理解情况、误区、下节建议）。
    """
    transcript_history = "\n".join(context.transcript_buffer[-80:])
    interaction_events = json.dumps(context.interaction_events[-50:], ensure_ascii=False)
    user_prompt = build_class_summary_user_prompt(transcript_history, interaction_events)
    client = _openai_client()
    response = client.chat.completions.create(
        model=_model_name(),
        messages=[
            {"role": "system", "content": CLASS_SUMMARY_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content or "{}")

