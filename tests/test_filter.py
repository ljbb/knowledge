"""测试 filter 模块"""

import pytest
from pathlib import Path
from engine.filter import check_completeness, check_duplicate, compute_source_hash


class TestCheckCompleteness:
    def test_complete_content_passes(self):
        content = """# 标题

## 背景/场景
需要时使用。

## 操作步骤
1. 执行命令
2. 检查结果

## 验证证据
- [ ] 验证通过

## 回滚方案
1. 撤销操作
"""
        metadata = {"author": "测试者"}
        result = check_completeness(content, metadata)
        assert result["passed"] is True
        assert result["missing"] == []

    def test_missing_background(self):
        content = """# 标题

## 操作步骤
1. 做事
"""
        metadata = {"author": "测试者"}
        result = check_completeness(content, metadata)
        assert result["passed"] is False
        assert "背景/场景描述" in result["missing"]

    def test_missing_author(self):
        content = """# 标题

## 背景/场景
测试。

## 操作步骤
1. 做事

## 验证证据
- [ ] 通过

## 回滚方案
1. 撤销
"""
        metadata = {}
        result = check_completeness(content, metadata)
        assert result["passed"] is False
        assert "作者信息" in result["missing"]

    def test_missing_rollback(self):
        content = """# 标题

## 背景/场景
测试。

## 操作步骤
1. 做事

## 验证证据
- [ ] 通过
"""
        metadata = {"author": "测试者"}
        result = check_completeness(content, metadata)
        assert result["passed"] is False
        assert "回滚方案" in result["missing"]


class TestCheckDuplicate:
    def test_no_existing_entries_returns_create_new(self, tmp_path, monkeypatch):
        import engine.filter as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        (tmp_path / "wiki").mkdir(exist_ok=True)

        result = check_duplicate("新内容", "新标题")
        assert result["action"] == "create_new"
        assert result["is_duplicate"] is False

    def test_similar_title_detected(self, tmp_path, monkeypatch):
        import engine.filter as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        wiki_dir = tmp_path / "wiki" / "infra-daily"
        wiki_dir.mkdir(parents=True)

        existing = """---
id: kb-001
title: "重启 Nginx 服务"
category: infra-daily
---
# 重启 Nginx 服务

如何安全重启 Nginx 服务的完整操作流程。
"""
        (wiki_dir / "kb-001.md").write_text(existing, encoding="utf-8")

        result = check_duplicate(
            "如何安全重启 Nginx 服务的完整操作流程。",
            "重启 Nginx 服务",
        )
        assert result["similarity"] > 0.8

    def test_different_content_returns_create_new(self, tmp_path, monkeypatch):
        import engine.filter as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        wiki_dir = tmp_path / "wiki" / "infra-daily"
        wiki_dir.mkdir(parents=True)

        existing = """---
id: kb-001
title: "重启 Nginx 服务"
category: infra-daily
---
# 重启 Nginx 服务

Web 服务器重启操作流程。
"""
        (wiki_dir / "kb-001.md").write_text(existing, encoding="utf-8")

        result = check_duplicate(
            "磁盘空间不足时需要清理临时文件和日志",
            "磁盘清理操作",
        )
        assert result["action"] == "create_new"
        assert result["is_duplicate"] is False


class TestComputeSourceHash:
    def test_hash_consistent(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h1 = compute_source_hash(f)
        h2 = compute_source_hash(f)
        assert h1 == h2
        assert h1.startswith("sha256:")
