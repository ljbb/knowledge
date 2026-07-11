"""Skill 生成模块 — 从知识条目生成 agentskill.io 标准 Skill 文件"""

import re
from pathlib import Path
from typing import Any

import frontmatter

from engine.config import get_project_root


def generate_knowledge_skill(knowledge_md_path: Path) -> Path:
    """从知识条目 .md 生成对应的知识 Skill。

    Args:
        knowledge_md_path: wiki/{category}/{id}.md 路径

    Returns:
        生成的 Skill 文件路径 skills/{category}/{skill_name}.md
    """
    post = frontmatter.load(str(knowledge_md_path))
    metadata = post.metadata
    content = post.content

    title = metadata.get("title", knowledge_md_path.stem)
    skill_name = _title_to_skill_name(title)
    category = metadata.get("category", "general")
    tags = metadata.get("tags", [])
    kb_id = metadata.get("id", knowledge_md_path.stem)

    summary = _extract_summary(content)
    scenario = _extract_section(content, "背景/场景")
    steps = _extract_section(content, "操作步骤")
    verification = _extract_section(content, "验证证据")
    rollback = _extract_section(content, "回滚方案")
    execution = _extract_section(content, "执行接口")

    skill_content = f"""---
name: {skill_name}
description: {summary[:100]}
category: {category}
tags: {tags}
knowledge_id: {kb_id}
---

# {title}

## 摘要（~50 tokens）
{summary}

## 场景匹配
{scenario or '当用户询问 ' + title + ' 相关问题时使用。'}

## 操作指引
{steps or '参见完整知识条目。'}

## 验证清单
{verification or '参见完整知识条目。'}

## 回滚步骤
{rollback or '参见完整知识条目。'}

## 执行接口
{execution or '参见完整知识条目。'}
"""

    skills_dir = get_project_root() / "skills" / category
    skills_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skills_dir / f"{skill_name}.md"
    skill_path.write_text(skill_content, encoding="utf-8")

    return skill_path


def generate_meta_skills() -> list[Path]:
    """生成三个元 Skill 文件：kb-search, kb-ingest, kb-status。

    Returns:
        生成的 Skill 文件路径列表
    """
    skills_dir = get_project_root() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    meta_skills = [
        {
            "name": "kb-search",
            "description": "在 DevOps & Infra 知识库中搜索知识",
            "content": """---
name: kb-search
description: 在 DevOps & Infra 知识库中搜索知识
type: meta
---

# 知识库搜索

## 触发条件
当用户询问 DevOps、Infra、运维、自动化、Harbor 相关问题时。

## 执行流程
1. 分析用户意图，提取搜索关键词
2. 调用搜索：
   ```bash
   python kb.py search "<关键词>" --category <可选分类>
   ```
3. Engine 返回匹配结果列表（id、title、摘要、匹配度）
4. 向用户展示候选项，确认需要的知识
5. 加载对应知识 Skill，展开完整操作指引

## 可用分类
- infra-daily: Infra 日常操作
- infra-violation: Infra violation 修复
- automation: 自动化
- harbor: Harbor 平台
""",
        },
        {
            "name": "kb-ingest",
            "description": "将知识导入 DevOps & Infra 知识库",
            "content": """---
name: kb-ingest
description: 将知识导入 DevOps & Infra 知识库
type: meta
---

# 知识导入

## 触发条件
当用户要求导入知识、添加知识、入库，或提供一段需要保存的操作文档时。

## 执行流程
1. 收集用户提供的知识内容（文本或文件路径）
2. 如果用户提供的是文件，先复制到 `raw/` 目录
3. 按知识模板整理内容：
   - 提取背景/场景
   - 整理操作步骤（每步可独立执行）
   - 列出验证证据
   - 记录作者信息
   - 添加回滚方案
4. 调用导入命令：
   ```bash
   python kb.py ingest raw/<文件名>
   ```
5. 如果内容不完整，提示用户补充缺失项
6. 返回入库结果和知识 ID

## 知识模板要求
- 背景/场景描述（必须）
- 操作步骤（必须，每步需可执行）
- 验证证据（必须，检查清单格式）
- 回滚方案（必须）
- 作者信息（必须）
- 执行接口（可选：Jenkins/GitHub/Harbor 链接）
""",
        },
        {
            "name": "kb-status",
            "description": "检查 DevOps & Infra 知识库的健康状态",
            "content": """---
name: kb-status
description: 检查 DevOps & Infra 知识库的健康状态
type: meta
---

# 知识库状态检查

## 触发条件
当用户询问知识库状态、知识库健康、知识库有什么问题时。

## 执行流程
1. 调用健康检查：
   ```bash
   python kb.py check
   ```
2. 分析检查报告：
   - A 级（基础）：必填字段、死链接、Markdown 语法
   - B 级（内容）：步骤可操作性、验证证据、回滚方案
   - C 级（全面）：新鲜度、交叉引用、孤立检测
3. 汇总问题并按优先级排列
4. 对每个问题给出修复建议
""",
        },
    ]

    paths = []
    for skill_def in meta_skills:
        skill_path = skills_dir / f"{skill_def['name']}.md"
        skill_path.write_text(skill_def["content"], encoding="utf-8")
        paths.append(skill_path)

    return paths


def _title_to_skill_name(title: str) -> str:
    """将标题转换为 kebab-case skill 名称，加 kb- 前缀。"""
    name = title.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"-+", "-", name)
    return f"kb-{name[:50]}"


def _extract_summary(content: str) -> str:
    """从正文提取第一段非标题行作为摘要。"""
    lines = content.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and len(stripped) > 10:
            return stripped[:200]
    return ""


def _extract_section(content: str, section_name: str) -> str:
    """从正文提取指定段落内容。"""
    patterns = [
        f"## {section_name}",
        f"## {section_name}：",
        f"### {section_name}",
    ]
    for pattern in patterns:
        if pattern in content:
            section = content.split(pattern, 1)[-1]
            next_section = section.find("\n## ")
            if next_section != -1:
                section = section[:next_section]
            return section.strip()
    return ""
