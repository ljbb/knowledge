"""测试 skill_gen 模块"""

import pytest
from pathlib import Path
from engine.skill_gen import (
    generate_knowledge_skill,
    generate_meta_skills,
    _title_to_skill_name,
    _extract_summary,
    _extract_section,
)


class TestSkillGen:
    def test_generate_knowledge_skill(self, tmp_path, monkeypatch):
        import engine.skill_gen as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        wiki_dir = tmp_path / "wiki" / "infra-daily"
        wiki_dir.mkdir(parents=True)
        entry_path = wiki_dir / "kb-2026-0711-001.md"
        entry_path.write_text("""---
id: kb-2026-0711-001
title: "重启 Nginx 服务"
category: infra-daily
tags: [nginx, restart]
---

# 重启 Nginx 服务

在生产环境中安全重启 Nginx 服务的标准流程。

## 背景/场景
当 Nginx 配置更新后需要重启服务而不中断连接时使用。

## 操作步骤
1. 检查配置语法：`nginx -t`
2. 优雅重启：`nginx -s reload`
3. 验证服务状态

## 验证证据
- [ ] nginx -t 通过
- [ ] 服务状态 active

## 回滚方案
1. 恢复备份配置

## 执行接口
- harbor_cli: `harbor job run nginx-restart`
""", encoding="utf-8")

        skill_path = generate_knowledge_skill(entry_path)

        assert skill_path.exists()
        content = skill_path.read_text(encoding="utf-8")
        assert "nginx" in str(skill_path.name)
        assert "重启 Nginx 服务" in content
        assert "nginx -t" in content
        assert "nginx-restart" in content

    def test_generate_meta_skills(self, tmp_path, monkeypatch):
        import engine.skill_gen as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        paths = generate_meta_skills()

        assert len(paths) == 3
        names = {p.stem for p in paths}
        assert names == {"kb-search", "kb-ingest", "kb-status"}

        search_content = (skills_dir / "kb-search.md").read_text(encoding="utf-8")
        assert "name: kb-search" in search_content
        assert "type: meta" in search_content
        assert "python kb.py search" in search_content

    def test_title_to_skill_name(self):
        assert "kb-" in _title_to_skill_name("重启 Nginx 服务")
        assert _title_to_skill_name("磁盘清理 v2.0") == "kb-磁盘清理-v20"

    def test_extract_summary(self):
        content = """# 标题

在生产环境中安全重启 Nginx 服务的标准流程。

## 背景
"""
        summary = _extract_summary(content)
        assert "生产环境" in summary

    def test_extract_section(self):
        content = """# 标题

## 背景/场景
这是场景描述。

## 操作步骤
1. 步骤一
2. 步骤二

## 验证证据
- [ ] 通过
"""
        scenario = _extract_section(content, "背景/场景")
        assert "场景描述" in scenario

        steps = _extract_section(content, "操作步骤")
        assert "步骤一" in steps

    def test_extract_section_not_found(self):
        result = _extract_section("# No sections here", "不存在的段落")
        assert result == ""
