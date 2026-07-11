# DevOps & Infra 知识库系统 — 设计文档

> 基于 llm-wiki.md 框架，面向 DevOps 和 Infra 维护的知识库系统。
> LLM 写入，人类阅读，Skill 驱动。

---

## 1. 项目概述

### 1.1 目标

构建一个 LLM 驱动的知识库，覆盖 Infra 日常操作、Infra violation 修复、自动化、Harbor 平台四个领域。知识库同时服务于 LLM（通过 Skill）和人类（通过 Web 界面）。

### 1.2 核心原则

- **LLM 是写作者**：所有知识整理、格式化、流程图生成、去重判断由 LLM 完成
- **Engine 是编排者**：Python Engine 负责编排 LLM 调用、管理文件、执行索引
- **Skill 是接口**：所有操作通过 agentskill.io 标准 Skill 暴露，跨 Claude Code / OpenCode / Copilot 使用
- **Markdown 是真相**：知识本体是 Markdown 文件（git 管理），LLM 和人类都能直接阅读
- **Raw 不可变**：原始文件 add-only，知识更新通过版本升级，完整可追溯

---

## 2. 架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────┐
│                   接入层                          │
│   ┌──────┐    ┌──────────┐    ┌──────────────┐  │
│   │ CLI  │    │   Web    │    │   Skills     │  │
│   │kb.py │    │ Flask    │    │ agentskill   │  │
│   └──┬───┘    └────┬─────┘    │ .io 标准      │  │
│      │             │          └──────┬───────┘  │
│      └─────────────┼────────────────┘           │
│                    │                             │
├────────────────────┼─────────────────────────────┤
│               Engine 层                           │
│   ┌────────────────┴──────────────────────────┐  │
│   │  ingest │ filter │ quality │ index │ skill │  │
│   └────────────────┬──────────────────────────┘  │
│                    │                             │
├────────────────────┼─────────────────────────────┤
│               存储层                              │
│   ┌────────┐  ┌─────────┐  ┌──────────────────┐ │
│   │ raw/   │  │  wiki/  │  │  schema/         │ │
│   │ 原始文件│  │ 知识本体 │  │  配置 + 模板     │ │
│   └────────┘  └─────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────┘
```

三层对应 llm-wiki 的核心理念：
- **Raw sources**（raw/）：策展的原始文档集合，add-only
- **The wiki**（wiki/）：LLM 生成和维护的 Markdown 知识库
- **The schema**（schema/）：告诉 LLM 如何结构化、如何维护知识的配置

### 2.2 技术选型

| 组件 | 技术 | 理由 |
|---|---|---|
| 核心语言 | Python 3.12+ | 跨平台，LLM SDK 齐全 |
| Web 框架 | FastAPI | 异步支持，自动 OpenAPI，适合 API + 静态服务 |
| LLM SDK | anthropic + openai + google-genai | 覆盖 Claude / DeepSeek / Gemini |
| 前端渲染 | Jinja2 + Markdown → HTML | 服务端渲染，无前端构建 |
| 流程图 | Mermaid.js | 浏览器端渲染，无服务端依赖 |
| 存储 | Markdown 文件 + Git | 文本即数据库，版本控制天然支持 |
| 搜索 | Engine 内置 Python 搜索 | LLM 给范围 → Engine 执行 → 返回结果 |
| 测试 | pytest | 标准 Python 测试框架 |
| 进程安全 | 文件锁（msvcrt / fcntl） | 防止并发写入冲突 |

---

## 3. 目录结构

```
knowledge-base/
├── raw/                          # 原始文件（add-only，不可变）
│   └── .gitkeep
├── wiki/                         # 知识本体（LLM 写入）
│   ├── infra-daily/              # Infra 日常操作
│   ├── infra-violation/          # Infra violation 修复
│   ├── automation/               # 自动化
│   ├── harbor/                   # Harbor 平台
│   ├── index.md                  # 知识索引（Engine 维护）
│   └── log.md                    # 操作日志（Engine 追加）
├── schema/                       # 配置 & 模板
│   ├── CLAUDE.md                 # LLM 行为规范（llm-wiki 的 schema 层）
│   ├── knowledge-template.md     # 知识条目标准模板
│   └── config.yaml               # 项目配置
├── engine/                       # Python 知识处理引擎
│   ├── __init__.py
│   ├── ingest.py                 # 导入入口（编排 LLM）
│   ├── filter.py                 # 内容过滤（调 LLM 判断）
│   ├── quality.py                # 三级质量检查
│   ├── indexer.py                # index.md + log.md 维护
│   ├── skill_gen.py              # Skill 文件生成
│   ├── search.py                 # 搜索模块
│   ├── llm_client.py             # LLM 统一调用接口
│   └── file_lock.py              # 文件锁
├── skills/                       # agentskill.io 标准 Skill
│   ├── kb-search.md              # 元 Skill：搜索知识
│   ├── kb-ingest.md              # 元 Skill：导入知识
│   ├── kb-status.md              # 元 Skill：健康检查
│   └── infra-daily/              # 知识 Skill（按分类组织）
│       ├── kb-nginx-restart.md
│       └── ...
├── web/                          # Web 应用
│   ├── __init__.py
│   ├── app.py                    # FastAPI 入口
│   ├── routes/
│   │   ├── pages.py              # 页面路由（阅读）
│   │   ├── admin.py              # 管理路由（上传、导入）
│   │   └── api.py                # API 路由（搜索、问答）
│   ├── templates/                # Jinja2 模板
│   └── static/                   # 静态资源
├── tests/                        # 测试
│   ├── test_ingest.py
│   ├── test_filter.py
│   ├── test_quality.py
│   ├── test_search.py
│   └── test_skills.py
├── kb.py                         # CLI 入口
├── requirements.txt
└── README.md
```

---

## 4. 知识条目标准结构

每条知识入库后统一转换为以下格式（YAML frontmatter + Markdown）：

```markdown
---
id: kb-2026-0711-001
title: "重启生产环境 Nginx 服务"
category: infra-daily
tags: [nginx, restart, production]
author: "张三"
created: 2026-07-11
updated: 2026-07-11
version: 1
status: verified
source_file: raw/nginx-restart.md
source_hash: sha256:abc123...
diagram: |
  flowchart TD
    A[检查配置语法] --> B{语法正确?}
    B -->|是| C[优雅重启]
    B -->|否| D[修正配置]
    D --> A
    C --> E[验证服务状态]
    E --> F[检查错误日志]
---

# 重启生产环境 Nginx 服务

## 背景/场景
当生产环境 Nginx 配置更新后，需要安全重启服务而不中断连接。

## 前置条件
- 已登录到目标服务器
- 拥有 sudo 权限
- 已备份当前 nginx.conf

## 操作步骤
1. 检查配置语法：`nginx -t`
2. 优雅重启：`nginx -s reload`
3. 验证服务状态：`systemctl status nginx`
4. 检查错误日志：`tail -f /var/log/nginx/error.log`

## 验证证据
- [ ] `nginx -t` 返回 "syntax is ok"
- [ ] `systemctl status nginx` 显示 active (running)
- [ ] 错误日志无新异常

## 回滚方案
1. 恢复备份配置
2. 执行 `nginx -s reload`

## 关联知识
- [[nginx-config-best-practices]]
- [[production-deploy-checklist]]

## 执行接口
- type: python_script | jenkins_pipeline | github_action | harbor_job | harbor_cli
- harbor_job: https://harbor.example.com/jobs/nginx-restart
- harbor_cli: `harbor job run nginx-restart --env prod`
```

### 4.1 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✓ | 唯一标识，格式 `kb-YYYY-MMDD-NNN` |
| title | ✓ | 知识标题 |
| category | ✓ | 分类：infra-daily / infra-violation / automation / harbor |
| tags | ✓ | 标签列表 |
| author | ✓ | 作者信息 |
| created | ✓ | 创建日期 |
| updated | ✓ | 最后更新日期 |
| version | ✓ | 版本号，整数递增 |
| status | ✓ | verified / draft / outdated |
| source_file | ✓ | 对应的 raw 文件路径 |
| source_hash | ✓ | raw 文件内容哈希，用于版本追踪 |
| diagram | 可选 | LLM 生成的 Mermaid 流程图 |

---

## 5. 知识导入 Pipeline

### 5.1 流程概述

```
原始文件 (任意格式)
    │
    ▼
┌─────────────────────────────────────────────┐
│ STEP 1: 内容提取（LLM 驱动）                  │
│  - LLM 读取原始文件                           │
│  - 理解内容，提取关键信息                       │
│  - 按知识模板整理结构                          │
│  - 生成 .md 和 .html 文件                     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ STEP 2: 内容过滤（LLM 驱动）                  │
│  - 是否有背景/场景描述？                       │
│  - 是否有明确操作步骤？                        │
│  - 是否有验证证据？                            │
│  - 是否有作者信息？                            │
│  - 缺失项 → 提示用户补充                       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ STEP 3: 去重检测（LLM 驱动）                  │
│  - LLM 对比新内容与现有相关条目                 │
│  - 判定：重复（建议更新版本）/ 实质不同（新建）   │
│  - 新建：继续下一步                            │
│  - 更新：生成新版本号，保留旧版本               │
│  - LLM 不可用时回退 difflib 标题比对           │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ STEP 4: 质量检查（Engine 执行）               │
│  A 级：死链接、必填字段、Markdown 语法          │
│  B 级：步骤可操作性、验证证据、回滚方案          │
│  C 级：新鲜度、交叉引用、孤立检测               │
│  不通过 → 退回，附修复指引                      │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ STEP 5: 流程图生成（LLM 驱动）                │
│  - 检测操作步骤                                │
│  - LLM 分析步骤语义，生成 Mermaid flowchart    │
│  - 写入 frontmatter diagram 字段              │
│  - LLM 不可用时跳过                            │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ STEP 6: 入库                                 │
│  - 写入 wiki/{category}/{id}.md              │
│  - 写入 wiki/{category}/{id}.html            │
│  - 更新 index.md                             │
│  - 追加 log.md                               │
│  - 生成 skill 文件 → skills/{category}/      │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
                    入库完成
```

### 5.2 原始文件处理规则

- `raw/` 目录：add-only，文件写入后不可修改
- 知识更新：上传新版 raw 文件 → Pipeline 生成 `version: N+1` 的新 wiki 条目
- 旧版本保留在 wiki 中，通过 `id` 关联
- `log.md` 记录完整链路：raw 文件 → wiki 条目 → 版本历史

### 5.3 质量检查三级体系

| 级别 | 检查内容 | 行为 |
|---|---|---|
| **A 基础** | 死链接检测、必填字段完整性、Markdown 语法校验、index.md 一致性 | 阻止入库 |
| **B 内容** | 步骤是否可执行、验证证据存在性、回滚方案完整性、知识矛盾检测 | 阻止入库 |
| **C 全面** | 知识新鲜度（N 天未更新标记）、交叉引用覆盖率、分类覆盖度统计、孤立知识检测 | 阻止入库 |

所有检查始终执行，无开关、无跳过模式。不通过即退回，附具体修复指引。

---

## 6. Skill 系统

### 6.1 两层 Skill 架构

```
skills/
├── kb-search.md              # 元 Skill：路由壳
├── kb-ingest.md              # 元 Skill：导入
├── kb-status.md              # 元 Skill：健康检查
└── {category}/
    ├── kb-nginx-restart.md   # 知识 Skill
    ├── kb-disk-cleanup.md    # 知识 Skill
    └── ...
```

**元 Skill** 负责路由和编排：
- `kb-search`：接收用户问题 → 调 `python kb.py search "<query>"` → Engine 返回匹配的知识 Skill 列表 → LLM 加载对应 Skill
- `kb-ingest`：接收文本/文件 → 调 Engine Pipeline → 返回入库结果
- `kb-status`：调 `python kb.py check` → 返回健康报告

**知识 Skill** 按知识条目自动生成，定义具体操作流程。

### 6.2 Skill 文件格式（agentskill.io 标准）

#### 元 Skill 示例：kb-search

```markdown
---
name: kb-search
description: 在 DevOps & Infra 知识库中搜索知识
type: meta
---

# 知识库搜索

## 触发条件
当用户询问 DevOps、Infra、运维、自动化、Harbor 相关问题时。

## 执行流程
1. 分析用户意图，提取搜索关键词
2. 调用搜索：`python kb.py search "<关键词>" --category <可选分类>`
3. Engine 返回匹配结果列表（id、title、摘要、匹配度）
4. 向用户展示候选项，确认需要的知识
5. 加载对应知识 Skill，展开完整操作指引
```

#### 知识 Skill 示例：kb-nginx-restart

```markdown
---
name: kb-nginx-restart
description: 安全重启生产环境 Nginx 服务
category: infra-daily
tags: [nginx, restart, production]
knowledge_id: kb-2026-0711-001
---

# 重启生产环境 Nginx 服务

## 摘要（~50 tokens）
重启 Nginx 标准流程：检查配置语法 → 优雅重启 → 验证服务状态 → 检查错误日志。

## 场景匹配
当用户提到 Nginx 重启、配置更新后重启、Nginx 服务异常需重启时使用。

## 操作指引
按以下步骤执行：

1. 检查配置语法
   ```bash
   nginx -t
   ```
   > 期望：syntax is ok

2. 执行优雅重启
   ```bash
   nginx -s reload
   ```

3. 验证服务状态
   ```bash
   systemctl status nginx
   ```
   > 期望：active (running)

4. 检查错误日志
   ```bash
   tail -f /var/log/nginx/error.log
   ```

## 验证清单
- [ ] nginx -t 返回 syntax is ok
- [ ] systemctl status 显示 active
- [ ] 错误日志无新异常

## 回滚步骤
恢复备份配置 → nginx -s reload

## 执行接口
- **Harbor MCP**: `harbor.job.run` tool，job: nginx-restart
- **Harbor CLI**: `harbor job run nginx-restart --env prod`
- **Jenkins**: https://jenkins.example.com/job/nginx-restart
```

### 6.3 Token 节省策略

**两层读取模式，LLM 先读摘要再决定是否展开：**

| 阶段 | 读取内容 | Token 估算 |
|---|---|---|
| 搜索阶段 | `kb.py search` CLI 返回的摘要列表（Engine 内部处理，不占 LLM 上下文） | 0 |
| 确认阶段 | Skill frontmatter + 摘要段落 | ~50 tokens/条 |
| 执行阶段 | 完整 Skill 内容 | ~500 tokens/条 |

**搜索路径**：LLM 给搜索范围 → Python Engine 执行搜索 → 返回结构化结果 → LLM 选中最匹配的 Skill → 加载执行

### 6.4 Skill 自动生成

知识入库后（Step 6），Engine 自动生成对应知识 Skill：
- 从知识条目的 frontmatter 提取 name、description、category、tags
- 背景/场景 → 场景匹配段落
- 操作步骤 → 操作指引段落
- 验证证据 → 验证清单
- 执行接口直接复制
- 自动截取前 1-2 句作为摘要

---

## 7. Web 界面

### 7.1 架构

FastAPI 单进程提供全部功能：

```
http://localhost:8000/
├── /                         → 知识库主页（HTML 阅读模式）
├── /kb/{category}/{id}       → 单条知识页面（含流程图）
├── /admin/                   → 管理后台首页
├── /admin/upload             → 原始文件上传
├── /admin/ingest/{file}      → 触发导入 Pipeline
├── /admin/health             → 自检报告仪表盘
├── /api/search?q=&category=  → 搜索 API
├── /api/kb/{id}              → 知识 API（JSON）
└── /api/ask                  → LLM 问答 API
```

### 7.2 页面功能

**阅读页面（/、/kb/**）**
- 左侧：分类目录树
- 中间：知识内容（Markdown 渲染为 HTML）
- 右侧：知识元信息 + 关联知识
- 操作步骤自动渲染为 Mermaid 流程图
- 深色/浅色主题切换
- 全文本搜索框

**管理后台（/admin/*）**
- 上传页面：拖拽上传原始文件到 raw/
- 导入管理：查看 raw/ 文件列表 → 选择 → 触发 Pipeline → 显示处理结果
- 健康仪表盘：三类检查结果可视化、知识统计、最近操作日志
- LLM 配置：管理 API Key（Claude / DeepSeek / Gemini）

### 7.3 HTML 生成

知识入库时 LLM 同时生成 .md 和 .html：
- `.md`：给 LLM 后续使用（Skill 读取、RAG 等）
- `.html`：给 Web 直接展示（服务端渲染，无需前端框架）
- FastAPI 直接 serve 静态 HTML，也支持通过 Jinja2 动态包装

---

## 8. LLM 集成

### 8.1 三层接入方式

| 方式 | 适用场景 | 说明 |
|---|---|---|
| **直接读文件** | Copilot / OpenCode | Skill 直接读取 `wiki/*.md`，零依赖 |
| **MCP Server** | Claude Code / MCP 客户端 | Engine 暴露为 MCP 工具 |
| **REST API** | 外部系统、自定义集成 | `/api/search`, `/api/kb/{id}`, `/api/ask` |

### 8.2 LLM 配置

```yaml
# schema/config.yaml
llm:
  providers:
    claude:
      type: anthropic
      api_key_env: ANTHROPIC_API_KEY
      default_model: claude-sonnet-4-6
    deepseek:
      type: openai_compatible
      api_key_env: DEEPSEEK_API_KEY
      base_url: https://api.deepseek.com
      default_model: deepseek-chat
    gemini:
      type: google
      api_key_env: GEMINI_API_KEY
      default_model: gemini-2.5-pro
  default: claude
```

Web 管理界面可配置和切换，API Key 存储在本地环境变量或 `.env` 文件。

### 8.3 MCP Server（可选）

Engine 可选暴露为 MCP Server，提供 tools：
- `kb_search(query, category?)` → 搜索结果
- `kb_get(id)` → 获取知识条目
- `kb_ingest(source_text)` → 导入知识
- `kb_check()` → 运行自检

Harbor MCP 作为独立 MCP Server 运行，知识 Skill 中记录对应的 tool 名称和调用方式。

---

## 9. Harbor 集成

### 9.1 设计原则

Harbor 是内部自动化平台，集成方式可配置，不在知识库中硬编码：

```yaml
# schema/config.yaml
harbor:
  mcp:
    enabled: false
    server_command: "harbor-mcp"  # 后续配置
  cli:
    enabled: true
    binary: "harbor"
    auth_method: token  # token | oauth | basic
```

### 9.2 知识中的执行接口

每条知识可记录多种执行方式：

```markdown
## 执行接口
- harbor_mcp_tool: job.run
- harbor_mcp_params: {"job": "nginx-restart", "env": "prod"}
- harbor_cli: `harbor job run nginx-restart --env prod`
- jenkins: https://jenkins.example.com/job/nginx-restart
- github_action: owner/repo/.github/workflows/nginx-restart.yml
```

LLM 根据当前环境选择可用方式。无法执行时，至少提供 CLI 命令给用户手动操作。

---

## 10. 搜索系统

### 10.1 工作流程

```
用户: "nginx 怎么重启"
    │
    ▼
LLM 分析意图，提取搜索参数:
  query: "nginx 重启"
  category: infra-daily (推断)
    │
    ▼
python kb.py search "nginx 重启" --category infra-daily
    │
    ▼
Engine 搜索逻辑:
  1. 读 index.md 获得候选范围
  2. 在指定分类中匹配标题 + 标签 + 全文关键词
  3. 排序，返回 top-N 结果
    │
    ▼
返回 JSON:
[
  {
    "id": "kb-2026-0711-001",
    "title": "重启生产环境 Nginx 服务",
    "category": "infra-daily",
    "skill_path": "skills/infra-daily/kb-nginx-restart.md",
    "summary": "重启 Nginx 标准流程...",
    "score": 0.96
  }
]
    │
    ▼
LLM 展示候选项 → 用户确认 → 加载对应 Skill
```

### 10.2 搜索实现

- 阶段 1（当前）：基于 index.md + Python 字符串匹配 + 标签过滤
- 阶段 2（未来）：可接 qmd（BM25 + 向量搜索 + LLM 重排序）或其他搜索引擎

---

## 11. 自测与检查

### 11.1 CLI 命令

```bash
# 全量检查
python kb.py check

# 单条检查
python kb.py check --id kb-2026-0711-001

# 按分类检查
python kb.py check --category infra-daily

# 初始化知识库
python kb.py init

# 搜索
python kb.py search "关键词" --category infra-daily

# 导入
python kb.py ingest raw/some-file.md
```

### 11.2 检查输出

```
=== 知识库健康检查 ===
时间: 2026-07-11 15:30:00
总知识条目: 42
分类分布: infra-daily=12, infra-violation=8, automation=15, harbor=7

A 级（基础） ........................ PASS
  死链接: 0 个失效
  必填字段: 全部完整
  Markdown 语法: 全部正确

B 级（内容） ........................ 3 个警告
  [kb-2026-0709-003] 缺少回滚方案
  [kb-2026-0710-012] 验证证据不够具体
  [kb-2026-0711-018] 步骤 3 不可独立执行

C 级（全面） ........................ 2 条提醒
  [kb-2026-0601-002] 超过 40 天未更新
  [kb-2026-0501-001] 孤立知识（无入链/出链）
```

### 11.3 pytest 测试

```bash
# 运行全部测试
pytest tests/

# 测试覆盖
pytest tests/ --cov=engine
```

---

## 12. 初始化流程

```bash
# 1. 初始化知识库目录
python kb.py init

# 输出:
#   ✓ 目录结构已创建
#   ✓ schema/config.yaml 已生成
#   ✓ schema/CLAUDE.md 已生成
#   ✓ wiki/index.md 已创建（空索引）
#   ✓ wiki/log.md 已创建（空日志）
#   ✓ skills/ 已创建

# 2. 配置 LLM API Key
# 编辑 .env 或通过 Web 管理界面配置

# 3. 上传第一个原始文件
# Web 上传或直接放到 raw/

# 4. 导入
python kb.py ingest raw/first-doc.md

# 5. 启动 Web
python kb.py serve

# 6. 在 Copilot/OpenCode 中加载 skill 目录
```

---

## 13. 关键设计决策汇总

| 决策 | 选择 | 理由 |
|---|---|---|
| 格式解析 | LLM 完成 | 支持任意格式，不需要维护多种解析器 |
| 去重检测 | LLM 判断 | 语义级对比，比算法精度高 |
| 流程图生成 | LLM 生成 Mermaid | 理解步骤语义，非固定模板 |
| 质量检查 | 始终执行，无开关 | 保证知识质量一致性 |
| Raw 文件 | add-only，版本追溯 | llm-wiki 不可变原则 |
| Skill 结构 | 两层（元 + 知识） | 控制 token，元 Skill 路由 + 知识 Skill 执行 |
| 搜索 | LLM 给范围 → Engine 执行 | 利用 LLM 理解 + Engine 效率 |
| Web 服务 | FastAPI 单进程 | 负责静态渲染 + API，不需要双服务 |
| 内容格式 | .md + .html 双产出 | .md 给 LLM，.html 给人 |
| 平台兼容 | Windows + macOS | Python 跨平台 + pip 安装即可 |

---

## 14. 待后续补充

- Harbor MCP 具体接入方式（需 Harbor 团队提供接口文档）
- qmd 或其他搜索引擎集成（知识库规模扩大后）
- 多用户协作机制（当前为单用户设计）
