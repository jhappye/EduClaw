-- EduClaw Student Model (PostgreSQL)
-- 目标：记录学生画像、知识点掌握度、错题、趋势与能力标签，并支持个性化 RAG 注入。

create table if not exists student_profile (
  student_id           varchar(64) primary key,
  class_id             varchar(64) not null,
  display_name         varchar(128),
  grade_level          varchar(32),
  learning_goal        text,
  mastery_overall      numeric(5,2) not null default 0.00, -- 0~100
  trend_7d             numeric(6,3) not null default 0.000, -- 最近7天趋势斜率
  trend_30d            numeric(6,3) not null default 0.000,
  ability_understand   numeric(5,2) not null default 0.00, -- 理解
  ability_apply        numeric(5,2) not null default 0.00, -- 应用
  ability_analyze      numeric(5,2) not null default 0.00, -- 分析
  last_active_at       timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

create index if not exists idx_student_profile_class_id on student_profile(class_id);


create table if not exists student_knowledge_mastery (
  student_id           varchar(64) not null,
  knowledge_point      varchar(256) not null,
  mastery_score        numeric(5,2) not null default 0.00, -- 0~100
  evidence_count       integer not null default 0,
  correct_count        integer not null default 0,
  wrong_count          integer not null default 0,
  last_result_score    numeric(5,2),
  last_seen_at         timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  primary key (student_id, knowledge_point),
  constraint fk_skm_student foreign key (student_id) references student_profile(student_id) on delete cascade
);

create index if not exists idx_skm_student on student_knowledge_mastery(student_id);
create index if not exists idx_skm_knowledge on student_knowledge_mastery(knowledge_point);


create table if not exists student_wrong_question (
  wrong_id             varchar(64) primary key,
  student_id           varchar(64) not null,
  task_id              varchar(64) not null,
  question_id          varchar(64) not null,
  knowledge_point      varchar(256) not null,
  error_category       varchar(64) not null, -- 概念混淆/计算错误/审题偏差/表达不完整...
  student_answer       text,
  standard_answer      text,
  error_reason         text,
  remediation_tip      text,
  occurred_at          timestamptz not null default now(),
  resolved             boolean not null default false,
  resolved_at          timestamptz,
  constraint fk_swq_student foreign key (student_id) references student_profile(student_id) on delete cascade
);

create index if not exists idx_swq_student_time on student_wrong_question(student_id, occurred_at desc);
create index if not exists idx_swq_knowledge on student_wrong_question(student_id, knowledge_point);


create table if not exists student_learning_event (
  event_id             varchar(64) primary key,
  student_id           varchar(64) not null,
  class_id             varchar(64) not null,
  task_id              varchar(64),
  event_type           varchar(64) not null, -- task_submitted/task_graded/hint_used/review_done...
  score                numeric(5,2),
  max_score            numeric(5,2),
  payload_json         jsonb not null default '{}'::jsonb,
  occurred_at          timestamptz not null default now(),
  constraint fk_sle_student foreign key (student_id) references student_profile(student_id) on delete cascade
);

create index if not exists idx_sle_student_time on student_learning_event(student_id, occurred_at desc);


create table if not exists student_rag_context (
  student_id           varchar(64) primary key,
  context_text         text not null,      -- 直接注入 RAG prompt 的画像摘要
  weak_knowledge_json  jsonb not null default '[]'::jsonb,
  strong_knowledge_json jsonb not null default '[]'::jsonb,
  recommendation_json  jsonb not null default '[]'::jsonb,
  updated_at           timestamptz not null default now(),
  constraint fk_src_student foreign key (student_id) references student_profile(student_id) on delete cascade
);

