from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from statistics import mean
from uuid import uuid4

from models import (
    AbilityTag,
    StudentProfile,
    TaskResultEvent,
    WrongQuestionRecord,
)


def _clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min_value, min(max_value, value))


def _ema(old_score: float, new_ratio_100: float, alpha: float = 0.35) -> float:
    """指数滑动平均：任务后更新知识点掌握度。"""
    return _clamp((1 - alpha) * old_score + alpha * new_ratio_100)


def _build_trend(recent_scores: list[float]) -> float:
    """
    简化趋势：后半段均值 - 前半段均值。
    > 0 表示上升，< 0 表示下降。
    """
    if len(recent_scores) < 4:
        return 0.0
    mid = len(recent_scores) // 2
    return mean(recent_scores[mid:]) - mean(recent_scores[:mid])


def update_student_profile_after_task(
    profile: StudentProfile,
    event: TaskResultEvent,
    *,
    recent_7d_scores: list[float],
    recent_30d_scores: list[float],
) -> StudentProfile:
    """
    每次任务评分后调用：
    1) 更新知识点掌握度
    2) 更新能力标签（理解/应用/分析）
    3) 更新错题记录
    4) 更新学习趋势
    """
    ratio_100 = (event.score / event.max_score * 100.0) if event.max_score > 0 else 0.0
    kp = event.knowledge_point

    if kp not in profile.knowledge_mastery:
        from models import KnowledgeMastery

        profile.knowledge_mastery[kp] = KnowledgeMastery(knowledge_point=kp)

    mastery = profile.knowledge_mastery[kp]
    mastery.mastery_score = _ema(mastery.mastery_score, ratio_100)
    mastery.evidence_count += 1
    mastery.last_result_score = ratio_100
    mastery.last_seen_at = event.occurred_at
    if ratio_100 >= 60:
        mastery.correct_count += 1
    else:
        mastery.wrong_count += 1

    # 能力标签更新（按题型/任务定义的权重加权）
    delta = (ratio_100 - 50.0) / 50.0 * 5.0  # 映射为[-5,+5]
    profile.ability.understand = _clamp(
        profile.ability.understand
        + delta * float(event.ability_weight.get(AbilityTag.UNDERSTAND, 0.0))
    )
    profile.ability.apply = _clamp(
        profile.ability.apply + delta * float(event.ability_weight.get(AbilityTag.APPLY, 0.0))
    )
    profile.ability.analyze = _clamp(
        profile.ability.analyze
        + delta * float(event.ability_weight.get(AbilityTag.ANALYZE, 0.0))
    )

    # 错题记录（如果存在错因分类）
    for category in event.error_categories:
        profile.wrong_questions.append(
            WrongQuestionRecord(
                wrong_id=f"wq_{uuid4().hex[:10]}",
                task_id=event.task_id,
                question_id="unknown",
                knowledge_point=kp,
                error_category=category,
                student_answer="",
                standard_answer="",
                error_reason=f"{category}: 自动聚合自评分结果",
                remediation_tip="建议复习对应知识点并完成1道同类变式题。",
            )
        )

    profile.mastery_overall = mean([m.mastery_score for m in profile.knowledge_mastery.values()])
    profile.trend_7d = _build_trend(recent_7d_scores)
    profile.trend_30d = _build_trend(recent_30d_scores)
    profile.updated_at = datetime.utcnow()
    return profile


def build_student_rag_context(profile: StudentProfile) -> str:
    """
    画像 -> RAG 上下文文本：
    用于注入 EduClaw 的生成/对话 prompt，实现个性化教学推荐。
    """
    weak_points = sorted(
        profile.knowledge_mastery.values(), key=lambda x: x.mastery_score
    )[:5]
    strong_points = sorted(
        profile.knowledge_mastery.values(), key=lambda x: x.mastery_score, reverse=True
    )[:3]

    weak_text = ", ".join([f"{k.knowledge_point}({k.mastery_score:.1f})" for k in weak_points]) or "暂无"
    strong_text = ", ".join([f"{k.knowledge_point}({k.mastery_score:.1f})" for k in strong_points]) or "暂无"

    recent_wrong = deque(profile.wrong_questions, maxlen=5)
    wrong_text = "; ".join([f"{w.knowledge_point}/{w.error_category}" for w in recent_wrong]) or "暂无"

    return (
        f"学生画像: 学生ID={profile.student_id}, 班级={profile.class_id}, 总体掌握={profile.mastery_overall:.1f}; "
        f"能力标签[理解={profile.ability.understand:.1f}, 应用={profile.ability.apply:.1f}, 分析={profile.ability.analyze:.1f}]。"
        f"弱项知识点: {weak_text}。强项知识点: {strong_text}。最近错题模式: {wrong_text}。"
        f"请优先讲解弱项并给出分层练习，保持一题一反馈。"
    )


def default_recent_scores(days: int, base: float = 60.0) -> list[float]:
    """示例辅助函数：用于本地 demo 生成趋势计算输入。"""
    now = datetime.utcnow()
    return [
        max(0.0, min(100.0, base + ((i % 5) - 2) * 2.5))
        for i in range(max(4, min(days, 30)))
        if now - timedelta(days=i) <= now
    ]
