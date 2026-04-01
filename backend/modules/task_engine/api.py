from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from models import Result, Submission, SubmissionAnswer, Task, TaskType
from service import SUBMISSION_STORE, evaluate_submission, generate_task

app = FastAPI(title="EduClaw Task Engine API", version="0.1.0")


class GenerateTaskRequest(BaseModel):
    class_id: str
    knowledge_point: str
    task_type: TaskType = TaskType.QUIZ
    title: str | None = None


class SubmitTaskRequest(BaseModel):
    task_id: str
    student_id: str
    class_id: str
    answers: list[SubmissionAnswer]


@app.post("/task/generate", response_model=Task)
def create_task(payload: GenerateTaskRequest) -> Task:
    return generate_task(
        class_id=payload.class_id,
        knowledge_point=payload.knowledge_point,
        task_type=payload.task_type,
        title=payload.title,
    )


@app.post("/task/submit", response_model=Result)
def submit_task(payload: SubmitTaskRequest) -> Result:
    submission = Submission(
        submission_id=f"sub_{uuid4().hex[:10]}",
        task_id=payload.task_id,
        student_id=payload.student_id,
        class_id=payload.class_id,
        answers=payload.answers,
    )
    SUBMISSION_STORE[submission.submission_id] = submission
    try:
        return evaluate_submission(submission)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8300, reload=True)
