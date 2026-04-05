# EduClaw Student Model（学生画像系统）

该模块用于记录学生学习行为并支持个性化推荐，满足以下能力：

- 知识点掌握度
- 错题记录
- 学习趋势（7/30 天）
- 能力标签（理解 / 应用 / 分析）
- RAG 个性化上下文构建

## 1. 数据结构

- SQL 表结构：`schema.sql`
- Python 领域模型：`models.py`
- 更新逻辑：`update_logic.py`
- FastAPI 接口：`api.py`

## 2. 接口（RESTful）

- `GET /v1/student-model/{student_id}`：获取学生画像 + RAG context
- `POST /v1/student-model`：创建/更新学生基础画像
- `POST /v1/student-model/{student_id}:update-from-task`：任务后更新画像

## 3. 更新机制（每次任务后）

`update_student_profile_after_task(...)` 会执行：

1. 更新知识点掌握度（EMA）
2. 更新能力标签（按权重映射到理解/应用/分析）
3. 写入错题模式
4. 更新总体掌握度与趋势

## 4. 与 RAG 结合

`build_student_rag_context(profile)` 输出可直接拼接到 prompt 的画像文本，包含：

- 弱项知识点（优先补救）
- 强项知识点（可加速推进）
- 最近错题模式（针对性讲解）
- 能力标签（控制任务难度与反馈粒度）

## 5. 运行示例

```bash
cd services/student_model
uvicorn api:app --host 0.0.0.0 --port 8200 --reload
```

> 说明：当前是 demo 内存存储，生产环境请将 `STUDENTS` 替换为数据库仓储层并对接 `schema.sql`。

