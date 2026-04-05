# EduClaw Teaching OS（K12 ToB）架构升级方案

> 目标：在保持 OpenMAIC / EduClaw 现有实现兼容的前提下，增量升级为“AI 驱动的 K12 课堂教学操作系统（Teaching OS）”。

## 1) 系统定位升级

### 1.1 从“课堂生成工具”到“Teaching OS”

- **旧定位**：输入主题/资料后生成课堂内容（课件、测验、互动场景）。
- **新定位**：围绕“备课-授课-作业-评估-复盘”的完整教学闭环，提供可运营、可追踪、可优化的教学操作系统。

### 1.2 K12 ToB 产品目标

- 面向学校/机构的私有化部署（多班级、多教师、多学段）。
- 支持课堂调度、任务布置、学习画像、过程性评价、教学分析。
- 以现有多 Agent 教学能力为核心，向“教学管理 + 学情分析”延展。

---

## 2) 当前代码仓库结构识别（As-Is）

### 2.1 前端结构（Next.js / React）

- 主页面与课堂页面：
  - `app/page.tsx`（课程创建与最近课堂入口）
  - `app/classroom/[id]/page.tsx`（课堂加载、恢复、续跑）
- 关键 UI 组件：
  - `components/stage.tsx`（课堂主舞台 + 播放/互动状态）
  - `components/chat/*`、`components/roundtable/*`（实时对话与多 Agent 展示）
  - `components/scene-renderers/*`（slides/quiz/interactive/pbl 场景渲染）
  - `components/settings/*`（多 provider 配置）
- 前端状态与存储：
  - Zustand：`lib/store/*`
  - IndexedDB（Dexie）：`lib/utils/database.ts`

### 2.2 后端结构（当前实际实现）

当前仓库后端是 **Next.js Route Handlers（Node/TS）**，并非 Python/FastAPI 主体：

- API 入口：`app/api/**/route.ts`
- 生成任务：`/api/generate-classroom` + job poll
- 聊天编排：`/api/chat`
- 能力服务：`/api/parse-pdf`、`/api/web-search`、`/api/generate/image`、`/api/generate/video`、`/api/generate/tts` 等
- 健康检查：`/api/health`

> 结论：当前可直接落地增量改造；若未来要引入 FastAPI，可作为“分析/评估微服务”分拆而非重写主系统。

### 2.3 多 Agent 系统

- 编排核心：`lib/orchestration/director-graph.ts`（Director 决策 + Agent 轮转）
- 编排适配：`lib/orchestration/ai-sdk-adapter.ts`、`prompt-builder.ts`、`tool-schemas.ts`
- 代理注册：`lib/orchestration/registry/*`
- 场景联动：`components/stage.tsx` + `components/chat/*`

### 2.4 内容生成流程

- 流程中枢：`lib/server/classroom-generation.ts`
- 两阶段流水线：`lib/generation/outline-generator.ts` -> `scene-generator.ts`（含 actions）
- 异步任务机制：`lib/server/classroom-job-runner.ts` + `classroom-job-store.ts`
- 媒体与语音增强：`lib/server/classroom-media-generation.ts`、`lib/media/*`、`lib/audio/*`

---

## 3) 架构升级设计（To-Be，增量改造）

### 3.1 新增核心模块（必须）

#### A. Classroom Orchestrator（课堂调度引擎）【新增】

**职责**
- 统一管理“课堂会话生命周期”：开始/暂停/切换活动/结束。
- 按课时目标动态调度 Teaching Agents（讲授、提问、练习、点评）。
- 接入班级节奏（例如：讲授 8 分钟 -> 练习 5 分钟 -> 反馈 3 分钟）。

**落地建议**
- 新增服务层：`lib/teaching-orchestrator/*`
- 对接现有 `director-graph`，把“对话轮次决策”提升为“课堂流程决策”。

#### B. Task Engine（任务系统）【新增】

**职责**
- 管理课堂任务（题目、实验步骤、分组任务、课后作业）。
- 跟踪任务状态（assigned/in-progress/submitted/reviewed）。
- 任务与场景绑定（scene-level task）、与学生绑定（student-level task）。

**落地建议**
- 新增：`lib/task-engine/*`
- API：`app/api/tasks/*`
- 持久化：Dexie 新表（本地）+ 可选服务端持久化接口。

#### C. Student Model（学生画像）【新增】

**职责**
- 建立学生画像：知识掌握度、能力维度、学习偏好、注意力与参与度 proxy。
- 支持个体与群体（班级）两层聚合。
- 为 Orchestrator 和 Task Engine 提供个性化依据。

**落地建议**
- 新增：`lib/student-model/*`
- API：`app/api/student-model/*`
- 数据来源：互动记录、答题结果、任务完成情况、对话行为特征。

#### D. Evaluation Engine（评估系统）【新增+改造】

**职责**
- 对课堂内外任务进行过程性评价（形成性评估）与阶段性评价。
- 支持规则评分 + LLM 评分（含 rubric）。
- 输出结构化评估结果，回写 Student Model。

**落地建议**
- 新增：`lib/evaluation/*`
- 改造：复用并扩展现有 `app/api/quiz-grade/route.ts`。

#### E. Analytics Dashboard（教学分析）【新增】

**职责**
- 面向教师与校方输出教学 KPI：
  - 课堂参与度、任务完成率、错题主题、知识点掌握热力图
  - 课堂节奏建议与下节课干预建议
- 提供班级与个体分析视图。

**落地建议**
- 新增页面：`app/analytics/page.tsx`、`app/analytics/[classId]/page.tsx`
- 新增数据聚合层：`lib/analytics/*`

---

### 3.2 模块调用关系（文本架构图）

```text
[Teacher UI / Admin UI]
   |  (create class / start class / assign tasks / view analytics)
   v
[Next.js App Router + API Layer]
   |
   +--> [Classroom Orchestrator] -----------------------------+
   |            |                                             |
   |            +--> [Multi-Agent Director Graph]             |
   |            |         (existing orchestration core)       |
   |            +--> [Task Engine] -------------------+       |
   |            |                                      |       |
   |            +--> [Evaluation Engine] <-------------+       |
   |            |             ^                                |
   |            v             |                                |
   |        [Student Model] --+                                |
   |            |                                              |
   |            +------------------> [Analytics Engine] -------+
   |
   +--> [Generation Pipeline]
   |       outline -> scenes -> media -> tts (existing)
   |
   +--> [Storage]
           - Local IndexedDB (existing)
           - Server classroom/job store (existing)
           - New task/student/evaluation/analytics datasets
```

---

### 3.3 新增 / 改造清单

#### 新增模块（New）

- `lib/teaching-orchestrator/`
  - `engine.ts`：课堂流程状态机（lesson phases）
  - `types.ts`：课堂调度实体定义
  - `policies.ts`：K12 分学段教学策略模板
- `lib/task-engine/`
  - `task-types.ts`、`task-store.ts`、`task-service.ts`
- `lib/student-model/`
  - `model-types.ts`、`profile-store.ts`、`inference.ts`
- `lib/evaluation/`
  - `rubric.ts`、`scoring.ts`、`feedback.ts`
- `lib/analytics/`
  - `aggregator.ts`、`metrics.ts`、`recommendation.ts`
- `app/api/tasks/*`
- `app/api/student-model/*`
- `app/api/evaluation/*`
- `app/api/analytics/*`
- `app/analytics/*`

#### 改造模块（Refactor / Extend）

- `lib/orchestration/director-graph.ts`
  - 接收 orchestrator phase/context（不仅是对话轮次）
- `components/stage.tsx`
  - 新增课堂 phase UI（讲授/练习/点评）与任务面板入口
- `components/chat/*`
  - 承载任务事件（task assigned/submitted/reviewed）消息类型
- `lib/utils/database.ts`
  - 新增数据表：tasks / studentProfiles / evaluations / analyticsSnapshots
- `app/api/quiz-grade/route.ts`
  - 并入 Evaluation Engine 的评分链路
- `lib/server/classroom-generation.ts`
  - 生成结果里嵌入 task seeds（用于课中任务自动化）

---

## 4) 增量实施路径（建议）

### Phase 1：最小可用 Teaching OS（2~4 周）

- 上线 Classroom Orchestrator + Task Engine（基础版）
- 前端先加“课堂任务面板 + 任务状态流”
- 复用现有 quiz-grade 做 Evaluation MVP

### Phase 2：学情与评估闭环（4~8 周）

- Student Model（掌握度 + 参与度）
- Evaluation Engine 完整化（rubric + 多任务类型）
- 任务-评估-画像回写闭环跑通

### Phase 3：管理与运营（8~12 周）

- Analytics Dashboard（教师视图 + 管理视图）
- 学校维度报表导出（班级、学段、学科）
- 多租户/组织架构（校区/年级/班级）

---

## 5) 与现有架构兼容性说明

- 保留现有 `generation pipeline`、`director-graph`、`stage/chat` 主链路。
- 新模块通过“服务层 + API 扩展 + UI 扩展”接入，不推翻原有组件。
- 先以 Next.js Route + TypeScript 增量实现；后续可将 analytics/evaluation 拆分为 Python/FastAPI 微服务。

---

## 6) 交付物建议（给 ToB 项目管理）

- 《Teaching OS 领域模型文档》（Classroom/Task/Student/Evaluation）
- 《K12 任务模板规范》（按学段/学科）
- 《学校私有化部署手册》（含健康检查与依赖检查）
- 《教学数据合规说明》（采集字段、脱敏、保留策略）

