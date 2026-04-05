# EduClaw Task Engine（FastAPI 示例）

这个目录提供一个可直接接入 EduClaw 的 Task Engine 微服务示例，覆盖：

- 任务自动生成（基于知识点 + LLM）
- 学生提交
- 自动评分（规则 + AI）
- 错误分析
- Agent Engine 触发入口（讲完知识点后自动下发任务）

## 1. 快速启动

```bash
cd services/task_engine_fastapi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY=sk-...
# 可选
export OPENAI_BASE_URL=
export TASK_ENGINE_MODEL=gpt-4o-mini

uvicorn main:app --host 0.0.0.0 --port 8100 --reload
```

## 2. 核心数据模型

- `Task`：课堂任务实体（quiz/简答/小组/PBL）
- `Submission`：学生提交
- `Result`：评分结果与错因分析

定义见 `schemas.py`。

## 3. REST API（可直接给前端调用）

- `POST /v1/tasks:generate`：自动生成任务
- `GET /v1/tasks?class_id=...`：按班级列出任务
- `GET /v1/tasks/{task_id}`：查询任务详情
- `POST /v1/tasks/{task_id}/submissions`：学生提交答案
- `POST /v1/results:grade`：评分（规则 + AI）
- `GET /v1/results/{result_id}`：查询评分结果
- `POST /v1/agent-events/knowledge-taught`：Agent 讲完知识点后自动触发任务生成

## 4. 与 EduClaw 集成建议

### 4.1 与 Agent Engine 的交互

当 `director-graph` 决策到“知识点讲授完成”时，向：

`POST /v1/agent-events/knowledge-taught`

发送：

```json
{
  "class_id": "class_001",
  "scene_id": "scene_02",
  "knowledge_point": "一元二次方程求根公式",
  "teacher_id": "agent_teacher_1",
  "event_type": "knowledge_taught",
  "task_type": "quiz"
}
```

### 4.2 与前端交互流程

1. 课堂页监听新任务事件（或轮询 `/v1/tasks`）。
2. 渲染任务卡片并收集作答。
3. 提交到 `/v1/tasks/{task_id}/submissions`。
4. 调用 `/v1/results:grade` 获取分数、反馈和错因分析。
5. 将分析结果回写学情系统（Student Model）。

