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

