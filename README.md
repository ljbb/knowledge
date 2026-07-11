# DevOps & Infra 知识库

基于 [llm-wiki](https://github.com/tobi/llm-wiki) 框架的 DevOps 和 Infra 维护知识库系统。

## 特性

- **LLM 驱动**：知识由 LLM 整理、去重、生成流程图
- **四类知识**：Infra 日常操作、Infra violation 修复、自动化、Harbor 平台
- **Web 界面**：快速搜索、阅读、上传原始文件
- **Skill 集成**：支持 Claude Code / OpenCode / Copilot 通过 agentskill.io 标准 Skill 使用
- **三级质检**：A/B/C 三级质量检查确保知识可靠性
- **版本追溯**：原始文件 add-only，知识更新通过版本升级

## 快速开始

### 环境要求

- Python 3.12+
- pip

### 安装

```bash
git clone <repo-url>
cd knowledge-base
pip install -r requirements.txt
```

### 初始化

```bash
python kb.py init
```

### 配置 LLM

编辑 `.env` 文件，设置至少一个 LLM API Key：

```bash
ANTHROPIC_API_KEY=sk-ant-...
# 或者
DEEPSEEK_API_KEY=sk-...
# 或者
GEMINI_API_KEY=...
```

### 导入知识

**方式一：通过 Skill（推荐）**

在 Claude Code / OpenCode / Copilot 中加载 `skills/` 目录，然后：
```
使用 kb-ingest 导入 raw/ 中的文件
```

**方式二：通过 CLI**

```bash
python kb.py ingest raw/your-document.md
```

### 启动 Web 服务

```bash
python kb.py serve
```

访问 http://localhost:8000

### 搜索知识

```bash
python kb.py search "nginx 重启"
```

### 健康检查

```bash
python kb.py check
```

## 目录结构

```
knowledge-base/
├── raw/              # 原始文件（add-only）
├── wiki/             # 知识本体（.md + .html）
│   ├── infra-daily/
│   ├── infra-violation/
│   ├── automation/
│   ├── harbor/
│   ├── index.md      # 知识索引
│   └── log.md        # 操作日志
├── schema/           # 配置 & 模板
├── engine/           # Python 处理引擎
├── skills/           # agentskill.io 标准 Skill
├── web/              # FastAPI Web 应用
└── tests/            # 测试
```

## 分类说明

| 分类 | 内容 |
|---|---|
| infra-daily | Infra 日常操作：重启、部署、监控、巡检 |
| infra-violation | Infra violation 修复：安全漏洞、配置违规、性能问题 |
| automation | 自动化：CI/CD、脚本、定时任务、告警规则 |
| harbor | Harbor 平台：任务管理、执行接口、平台操作 |

## LLM 支持

| Provider | 配置方式 | 说明 |
|---|---|---|
| Claude | `ANTHROPIC_API_KEY` | Anthropic SDK |
| DeepSeek | `DEEPSEEK_API_KEY` | OpenAI 兼容接口 |
| Gemini | `GEMINI_API_KEY` | Google Generative AI SDK |

## 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 含覆盖率报告
pytest tests/ --cov=engine --cov-report=term-missing
```

## Skill 系统

知识库通过 agentskill.io 标准 Skill 与 LLM 交互：

| Skill | 类型 | 功能 |
|---|---|---|
| kb-search | 元 Skill | 搜索知识库，找到匹配的知识条目 |
| kb-ingest | 元 Skill | 导入新知识，执行完整 Pipeline |
| kb-status | 元 Skill | 健康检查，报告知识库状态 |
| kb-* | 知识 Skill | 自动生成，每条知识对应一个 Skill |

LLM 通过 `kb-search` 找到知识 → 加载对应知识 Skill → 获取完整操作指引。

## License

MIT
