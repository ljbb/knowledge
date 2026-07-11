"""测试 ingest 模块"""

import pytest
from pathlib import Path
from engine.ingest import ingest, generate_knowledge_id, _build_markdown


SAMPLE_LLM_OUTPUT = """---
title: "重启 Nginx 服务"
category: infra-daily
tags: [nginx, restart]
author: "测试者"
---

# 重启 Nginx 服务

在生产环境中安全重启 Nginx 服务。

## 背景/场景
当 Nginx 配置更新后需要重启服务而不中断连接时使用。

## 操作步骤
1. 检查配置语法：`nginx -t`
2. 优雅重启：`nginx -s reload`
3. 验证服务状态：`systemctl status nginx`

## 验证证据
- [ ] nginx -t 返回 syntax is ok
- [ ] 服务状态显示 active

## 回滚方案
1. 恢复备份配置
2. 执行 nginx -s reload

## 关联知识
- [[nginx-config-best-practices]]
"""


def _setup_cross_ref_target(tmp_path):
    """Create a stub wiki file that can be used as a cross-reference target."""
    from engine.indexer import init_index, init_log

    wiki_dir = tmp_path / "wiki" / "infra-daily"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    stub = wiki_dir / "nginx-config-best-practices.md"
    stub.write_text(
        "---\nid: kb-ref-001\ntitle: Nginx Config Best Practices\n"
        "category: infra-daily\ntags: [nginx]\nauthor: stub\n"
        "created: 2026-01-01\nupdated: 2026-01-01\nversion: 1\n"
        "status: published\nsource_file: raw/stub.md\n"
        "source_hash: sha256:abc123\n---\n\n# Nginx Config Best Practices\n",
        encoding="utf-8",
    )

    init_index()
    init_log()


class TestIngest:
    def test_ingest_complete_flow(self, tmp_path, monkeypatch):
        import engine.ingest as mod
        import engine.quality as qmod
        import engine.indexer as imod
        import engine.skill_gen as smod
        import engine.filter as fmod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(qmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(imod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(smod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(fmod, "get_project_root", lambda: tmp_path)

        _setup_cross_ref_target(tmp_path)

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir(parents=True)
        raw_file = raw_dir / "nginx-restart.md"
        raw_file.write_text("# Nginx 重启操作文档\n\n原始内容。", encoding="utf-8")

        result = ingest(raw_file, SAMPLE_LLM_OUTPUT)

        assert result["success"] is True, f"Errors: {result['errors']}"
        assert result["id"].startswith("kb-")
        assert result["file"].endswith(".md")
        assert result["skill_file"].endswith(".md")

        wiki_file = tmp_path / result["file"]
        assert wiki_file.exists()

        html_file = tmp_path / result["html_file"]
        assert html_file.exists()

        skill_file = tmp_path / result["skill_file"]
        assert skill_file.exists()

        index_file = tmp_path / "wiki" / "index.md"
        assert index_file.exists()
        assert "Nginx" in index_file.read_text(encoding="utf-8")

        log_file = tmp_path / "wiki" / "log.md"
        assert log_file.exists()
        assert "ingest" in log_file.read_text(encoding="utf-8")

    def test_ingest_incomplete_content_rejected(self, tmp_path, monkeypatch):
        import engine.ingest as mod
        import engine.indexer as imod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(imod, "get_project_root", lambda: tmp_path)

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir(parents=True)
        raw_file = raw_dir / "incomplete.md"
        raw_file.write_text("不完整的内容。", encoding="utf-8")

        incomplete_output = """---
title: "不完整的知识"
category: infra-daily
---

# 不完整的知识

没有步骤，没有验证，没有回滚。
"""

        result = ingest(raw_file, incomplete_output)
        assert result["success"] is False
        assert len(result["errors"]) > 0

    def test_ingest_detects_duplicate(self, tmp_path, monkeypatch):
        import engine.ingest as mod
        import engine.quality as qmod
        import engine.indexer as imod
        import engine.skill_gen as smod
        import engine.filter as fmod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(qmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(imod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(smod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(fmod, "get_project_root", lambda: tmp_path)

        _setup_cross_ref_target(tmp_path)

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir(parents=True)

        raw_file1 = raw_dir / "first.md"
        raw_file1.write_text("first", encoding="utf-8")
        raw_file2 = raw_dir / "second.md"
        raw_file2.write_text("second", encoding="utf-8")

        r1 = ingest(raw_file1, SAMPLE_LLM_OUTPUT)
        assert r1["success"] is True

        r2 = ingest(raw_file2, SAMPLE_LLM_OUTPUT)
        if r2["success"]:
            assert r2["version"] > 1

    def test_generate_knowledge_id_format(self, tmp_path, monkeypatch):
        import engine.ingest as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        kb_id = generate_knowledge_id()
        import re
        assert re.match(r"^kb-\d{4}-\d{4}-\d{3}$", kb_id), f"Invalid ID format: {kb_id}"

    def test_build_markdown(self):
        metadata = {
            "id": "kb-001",
            "title": "测试",
            "category": "infra-daily",
        }
        body = "# 测试\n\n正文内容。"
        md = _build_markdown(metadata, body)
        assert md.startswith("---")
        assert "id: kb-001" in md
        assert "正文内容" in md

    # === 回归测试 ===

    def test_regression_ingest_with_relative_path(self, tmp_path, monkeypatch):
        """回归测试: ingest 接受相对路径的 raw_file_path。

        Bug: raw_file_path.relative_to(get_project_root()) 在 raw_file_path
        为相对路径而 get_project_root() 返回绝对路径时抛出 ValueError。
        修复: resolve() raw_file_path 为绝对路径后再 relative_to，失败时回退。
        """
        import engine.ingest as mod
        import engine.quality as qmod
        import engine.indexer as imod
        import engine.skill_gen as smod
        import engine.filter as fmod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(qmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(imod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(smod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(fmod, "get_project_root", lambda: tmp_path)

        _setup_cross_ref_target(tmp_path)

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir(parents=True)
        raw_file = raw_dir / "relative-test.md"
        raw_file.write_text("# Test content", encoding="utf-8")

        # 关键: 使用相对路径调用 ingest
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            relative_path = Path("raw") / "relative-test.md"
            assert not relative_path.is_absolute(), "必须是相对路径才能触发 bug"

            result = ingest(relative_path, SAMPLE_LLM_OUTPUT)
            assert result["success"], f"相对路径应正常工作, errors: {result['errors']}"
            assert result["id"].startswith("kb-")
        finally:
            os.chdir(original_cwd)

    def test_regression_template_response_signature(self):
        """回归测试: TemplateResponse 签名验证。

        Bug: FastAPI 0.139+/Starlette 1.0+ 的 Jinja2Templates.TemplateResponse
        第一个参数必须是 request。旧代码传递 (name, context) 导致 Jinja2 缓存
        TypeError: unhashable type: 'dict'。
        修复: 所有路由使用 TemplateResponse(request, name, context)。
        """
        import inspect
        from starlette.templating import Jinja2Templates

        sig = inspect.signature(Jinja2Templates.TemplateResponse)
        params = list(sig.parameters.keys())
        # 验证签名是 (self, request, name, context, ...)
        assert params[0] == "self"
        assert params[1] == "request", (
            f"TemplateResponse 第一个参数应为 'request', 实际: {params[1]}。"
            f"路由调用必须使用 templates.TemplateResponse(request, name, context)"
        )
        assert params[2] == "name"
