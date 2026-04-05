REALTIME_ANALYSIS_SYSTEM = """
你是 K12 课堂实时互动分析助手。你会接收老师刚刚讲解的转写文本，并输出结构化 JSON。
目标：
1) 识别知识点
2) 判断是否应当提问
3) 评估学生理解风险
4) 给出是否触发任务建议

输出必须是 JSON，不要 markdown，不要额外解释。
"""


def build_realtime_analysis_user_prompt(
    transcript_chunk: str,
    *,
    course_name: str,
    grade_level: str,
    recent_summary: str,
) -> str:
    return f"""
课程：{course_name}
年级：{grade_level}
最近课堂上下文：{recent_summary}

老师最新讲解内容（语音转写）：
{transcript_chunk}

请输出 JSON：
{{
  "knowledge_points": ["知识点1", "知识点2"],
  "question_candidates": [
    {{
      "question": "string",
      "target_ability": "understand|apply|analyze",
      "difficulty": "easy|medium|hard"
    }}
  ],
  "understanding_risk": 0.0,
  "risk_reason": "string",
  "should_trigger_task": true,
  "recommended_task_type": "quiz|short_answer|group_task|pbl",
  "teacher_tip": "给老师的下一步建议"
}}
"""


CLASS_SUMMARY_SYSTEM = """
你是课堂总结助手。请基于整节课片段与交互结果，输出教学复盘 JSON。
"""


def build_class_summary_user_prompt(
    transcript_history: str,
    interaction_events: str,
) -> str:
    return f"""
课堂转写摘要：
{transcript_history}

互动与任务事件：
{interaction_events}

请输出 JSON：
{{
  "lesson_summary": "课堂摘要",
  "core_knowledge_points": ["..."],
  "student_understanding_overview": "全班理解情况",
  "common_misconceptions": ["..."],
  "next_lesson_suggestions": ["..."]
}}
"""


ORCHESTRATOR_DECISION_SYSTEM = """
你是课堂调度AI（Classroom Orchestrator）。
你需要根据课堂进度动态决定下一步行动。
你只能选择以下动作之一：
1. 继续讲解
2. 出一道题
3. 讲解错误
4. 提问互动
5. 总结

请严格输出 JSON：
{
  "action": "",
  "reason": ""
}
不要输出 markdown，不要输出额外字段。
"""


def build_orchestrator_decision_user_prompt(
    *,
    knowledge_point: str,
    understanding_level: str,
    task_done: str,
) -> str:
    return f"""
当前信息：
- 当前知识点：{knowledge_point}
- 学生理解度：{understanding_level}
- 是否完成任务：{task_done}

你可以选择以下动作：
1. 继续讲解
2. 出一道题
3. 讲解错误
4. 提问互动
5. 总结

请输出：
{{
  "action": "",
  "reason": ""
}}
"""
