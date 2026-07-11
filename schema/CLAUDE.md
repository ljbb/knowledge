# CLAUDE.md — DevOps & Infra 知识库

你是 DevOps & Infra 知识库的维护者。你的职责是根据 llm-wiki 模式管理这个知识库。

## 核心规则

1. **raw/ 不可变**：raw/ 目录中的原始文件是 add-only 的。永远不要修改已存在的 raw 文件。
2. **wiki/ 由你维护**：所有 wiki/ 下的 .md 和 .html 文件由你生成和维护。
3. **按模板输出**：所有知识条目必须符合 schema/knowledge-template.md 定义的格式。
4. **始终自检**：每次操作后运行 `python kb.py check` 验证知识库完整性。

## 工作流

### 导入知识 (ingest)
1. 读取 raw/ 中的源文件
2. 按模板提取和整理内容
3. 检查内容完整性（背景、步骤、验证、作者）
4. 与已有知识去重对比
5. 生成 .md 和 .html 文件
6. 更新 index.md 和 log.md
7. 生成对应 Skill 文件

### 搜索知识 (search)
1. 理解用户意图
2. 调用 `python kb.py search "<query>"`
3. 返回最匹配的知识条目

### 健康检查 (check)
1. 运行 `python kb.py check`
2. 根据报告修复问题

## 可用命令

- `python kb.py init` — 初始化知识库
- `python kb.py ingest <file>` — 导入知识
- `python kb.py search "<query>"` — 搜索知识
- `python kb.py check` — 健康检查
- `python kb.py serve` — 启动 Web 服务
