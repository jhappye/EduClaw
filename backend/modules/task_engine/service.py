from __future__ import annotations

from uuid import uuid4

from models import Result, Submission, SubmissionStatus, Task, TaskQuestion, TaskType

# demo in-memory stores
TASK_STORE: dict[str, Task] = {}
SUBMISSION_STORE: dict[str, Submission] = {}
RESULT_STORE: dict[str, Result] = {}


def generate_task(
    *,
    class_id: str,
    knowledge_point: str,
    task_type: TaskType,
    title: str | None = None,
) -> Task:
    """
    任务生成函数（可替换为 LLM 生成）。
    """
    task_id = f"task_{uuid4().hex[:10]}"
    task_title = title or f"{knowledge_point} - {task_type.value}"

    if task_type == TaskType.QUIZ:
        questions = [
            TaskQuestion(
                question_id="q1",
                prompt=f"{knowledge_point} 的核心定义是什么？",
                answer_type="short_text",
                standard_answer="（示例）",
                score=5,
            )
        ]
    elif task_type == TaskType.SHORT_ANSWER:
        questions = [
            TaskQuestion(
                question_id="q1",
                prompt=f"请解释 {knowledge_point} 的应用场景。",
                answer_type="short_text",
                standard_answer="（示例）",
                score=10,
            )
        ]
    elif task_type == TaskType.GROUP_TASK:
        questions = [
            TaskQuestion(
                question_id="q1",
                prompt=f"小组合作完成：围绕 {knowledge_point} 设计一个课堂案例。",
                answer_type="short_text",
                score=20,
            )
        ]
    else:  # TaskType.PBL
        questions = [
            TaskQuestion(
                question_id="q1",
                prompt=f"PBL任务：基于 {knowledge_point} 设计一个可验证的探究实验。",
                answer_type="short_text",
                score=20,
            )
        ]

    task = Task(
        task_id=task_id,
        class_id=class_id,
        title=task_title,
        task_type=task_type,
        knowledge_point=knowledge_point,
        instructions="请在规定时间内完成并提交。",
        questions=questions,
    )
    TASK_STORE[task_id] = task
    return task


def evaluate_submission(submission: Submission) -> Result:
    """
    提交评估函数（规则版，可扩展为规则 + LLM）。
    """
    task = TASK_STORE.get(submission.task_id)
    if not task:
        raise ValueError("Task not found")

    question_map = {q.question_id: q for q in task.questions}
    answer_map = {a.question_id: a.answer for a in submission.answers}

    max_score = sum(q.score for q in task.questions)
    score = 0.0
    for qid, q in question_map.items():
        student_answer = answer_map.get(qid)
        if q.answer_type in {"single_choice", "fill_blank", "short_text"}:
            if (
                student_answer is not None
                and q.standard_answer is not None
                and str(student_answer).strip().lower()
                == str(q.standard_answer).strip().lower()
            ):
                score += q.score
        elif q.answer_type == "multiple_choice":
            if isinstance(student_answer, list) and isinstance(q.standard_answer, list):
                if sorted(student_answer) == sorted(q.standard_answer):
                    score += q.score

    passed = (score / max_score) >= 0.6 if max_score > 0 else False
    feedback = "通过" if passed else "未通过，请复习后重试。"

    result = Result(
        result_id=f"res_{uuid4().hex[:10]}",
        task_id=task.task_id,
        submission_id=submission.submission_id,
        student_id=submission.student_id,
        score=score,
        max_score=max_score,
        passed=passed,
        feedback=feedback,
    )

    submission.status = SubmissionStatus.GRADED
    SUBMISSION_STORE[submission.submission_id] = submission
    RESULT_STORE[result.result_id] = result
    return result
