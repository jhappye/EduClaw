# EduClaw 课堂实时互动系统（Real-time Interaction）

## 1) 系统流程图（文本）

```text
[Teacher Speech]
   -> [ASR/STT (模拟文本输入)]
   -> [实时片段缓存]
   -> [LLM实时分析]
        |- 提取知识点
        |- 生成提问候选
        |- 评估理解风险
        |- 给出是否触发任务建议
   -> [理解评估融合]
        |- LLM风险分
        |- 快答/投票错误率(可选)
   -> [Task Trigger Decision]
        |- 若风险高或建议触发 -> 调用 Task Engine
        |- 生成 quiz / short_answer / group_task / pbl
   -> [Teacher实时提示]
        |- 下一步讲解建议
        |- 建议提问语句
   -> [课后总结]
        |- 课堂知识点总结
        |- 学生理解概览
        |- 共性误区
        |- 下节课建议
```

## 2) 核心函数设计

见 `core.py`：

- `analyze_teaching_chunk(...)`
  - 输入：本次 STT 文本片段 + 课程上下文
  - 输出：知识点、问题候选、风险评分、任务触发建议
- `estimate_student_understanding(...)`
  - 输入：LLM分析 + 快答统计（可选）
  - 输出：理解风险等级（low/medium/high）
- `handle_live_chunk(...)`
  - 输入：课堂上下文 + STT片段
  - 输出：本轮互动事件（含是否触发任务）
- `trigger_task_engine(...)`
  - 输入：知识点、任务类型、teacher/class 上下文
  - 行为：调用 `POST /v1/agent-events/knowledge-taught`
- `summarize_class(...)`
  - 输入：整节课转写与互动事件
  - 输出：课后结构化总结

## 3) 示例 Prompt（用于实时分析课堂内容）

系统提示词（摘要）：

```text
你是 K12 课堂实时互动分析助手。识别知识点、判断提问时机、评估理解风险、
给出任务触发建议。输出严格 JSON。
```

用户提示词模板关键字段：

- 课程名、年级
- 最近课堂上下文
- 老师最新讲解片段（STT）
- 固定 JSON schema：
  - `knowledge_points`
  - `question_candidates`
  - `understanding_risk`
  - `should_trigger_task`
  - `recommended_task_type`
  - `teacher_tip`

完整模板见 `prompts.py`。

## 4) 运行与集成

该模块是可嵌入服务层的 Python 组件，不限制 HTTP 框架。可在现有 FastAPI 服务中直接调用：

```python
event = await handle_live_chunk(
    context,
    transcript_chunk="今天我们讲一元二次方程求根公式...",
    scene_id="scene_02",
    task_engine_base_url="http://localhost:8100",
)
```

> 说明：ASR 由 EduClaw 现有语音链路提供；这里以“模拟输入文本片段”完成实时互动闭环。

