"""端到端集成测试 — 完整 Pipeline"""

import json
from pathlib import Path


SAMPLE_LLM_OUTPUT = """---
title: "磁盘空间清理"
category: infra-daily
tags: [disk, cleanup, maintenance]
author: "管理员"
---

# 磁盘空间清理

在服务器磁盘使用率超过 80% 时执行清理操作。

## 背景/场景
当监控告警磁盘使用率超过 80%，或日常巡检发现磁盘空间不足时。

## 操作步骤
1. 检查磁盘使用率：`df -h`
2. 清理临时文件：`rm -rf /tmp/*.tmp`
3. 清理旧日志：`find /var/log -name "*.log.*" -mtime +30 -delete`
4. 验证释放空间：`df -h`

## 验证证据
- [ ] 清理后磁盘使用率低于 70%
- [ ] 所有服务运行正常
- [ ] 无错误日志产生

## 回滚方案
1. 从备份恢复 /tmp 文件
2. 从日志归档恢复日志文件

## 关联知识
- [[disk-monitoring-setup]]
"""


def _setup_config(tmp_path):
    """Create a minimal config.yaml so load_config() works inside tmp_path."""
    config_dir = tmp_path / "schema"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text("""\
knowledge_base:
  name: "测试知识库"
  version: "0.1.0"
  categories:
    - infra-daily
    - infra-violation
    - automation
    - harbor

llm:
  default: claude
  providers:
    claude:
      type: anthropic
      api_key_env: ANTHROPIC_API_KEY
      default_model: claude-sonnet-4-6

harbor:
  mcp:
    enabled: false
  cli:
    enabled: false

quality:
  freshness_warn_days: 40

web:
  host: "0.0.0.0"
  port: 8000
""", encoding="utf-8")


def _setup_cross_ref_target(tmp_path):
    """Create a stub wiki file that serves as a cross-reference target."""
    from engine.indexer import init_index, init_log

    wiki_dir = tmp_path / "wiki" / "infra-daily"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # Use English title so it does not pollute Chinese search results.
    stub = wiki_dir / "disk-monitoring-setup.md"
    stub.write_text(
        "---\n"
        "id: kb-2026-0101-001\n"
        "title: Disk Monitoring Setup\n"
        "category: infra-daily\n"
        "tags: [disk, monitoring]\n"
        "author: stub\n"
        "created: 2026-01-01\n"
        "updated: 2026-07-10\n"
        "version: 1\n"
        "status: published\n"
        "source_file: raw/stub.md\n"
        "source_hash: sha256:abc123\n"
        "---\n\n"
        "# Disk Monitoring Setup\n\n"
        "Configure disk usage monitoring alerts on servers.\n\n"
        "## 背景/场景\n"
        "When disk usage monitoring is needed.\n\n"
        "## 操作步骤\n"
        "1. Install monitoring: `apt install smartmontools`\n"
        "2. Configure thresholds\n\n"
        "## 验证证据\n"
        "- [ ] Monitoring installed\n"
        "- [ ] Thresholds configured\n\n"
        "## 回滚方案\n"
        "1. Remove monitoring tools\n\n"
        "## 关联知识\n"
        "- [[disk-cleanup]]\n",
        encoding="utf-8",
    )

    init_index()
    init_log()


class TestEndToEnd:
    """端到端测试：init -> ingest -> search -> check"""

    def test_full_pipeline(self, tmp_path, monkeypatch):
        """完整的知识加工流程测试。"""
        _setup_config(tmp_path)

        # Patch get_project_root on every module that imports it.
        import engine.config as cmod
        import engine.ingest as imod
        import engine.filter as fmod
        import engine.quality as qmod
        import engine.indexer as xmod
        import engine.skill_gen as smod
        import engine.search as semod

        monkeypatch.setattr(cmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(imod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(fmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(qmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(xmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(smod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(semod, "get_project_root", lambda: tmp_path)

        # Also patch PROJECT_ROOT in config so load_config() reads from tmp_path.
        monkeypatch.setattr(cmod, "PROJECT_ROOT", tmp_path)

        _setup_cross_ref_target(tmp_path)

        # Step 1: Create raw file
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir(parents=True)
        raw_file = raw_dir / "disk-cleanup.md"
        raw_file.write_text("# 磁盘清理操作\n\n原始文档内容。", encoding="utf-8")

        # Step 2: Ingest
        from engine.ingest import ingest
        result = ingest(raw_file, SAMPLE_LLM_OUTPUT)

        assert result["success"], f"Ingest failed: {result['errors']}"
        assert result["id"].startswith("kb-")
        assert result["file"].endswith(".md")
        assert result["skill_file"].endswith(".md")

        # Step 3: Verify wiki files exist
        assert (tmp_path / result["file"]).exists()
        assert (tmp_path / result["html_file"]).exists()
        assert (tmp_path / result["skill_file"]).exists()

        # Step 4: Search for the knowledge
        from engine.search import search as search_fn
        results = search_fn("磁盘")
        assert len(results) > 0
        assert any("磁盘" in r["title"] for r in results)

        # Step 5: Search by category (more specific query to isolate ingested file)
        results = search_fn("磁盘空间清理", category="infra-daily")
        assert len(results) >= 1
        assert results[0]["category"] == "infra-daily"

        # Step 6: Search JSON output
        from engine.search import search_as_json
        json_str = search_as_json("磁盘")
        data = json.loads(json_str)
        assert len(data) > 0

        # Step 7: Quality check on all entries
        from engine.quality import check_all, check_summary
        check_results = check_all()
        assert len(check_results) > 0
        summary = check_summary(check_results)
        assert "知识库健康检查" in summary

        # Step 8: Verify index
        from engine.indexer import read_index
        entries = read_index()
        assert len(entries) >= 1

    def test_pipeline_with_incomplete_content(self, tmp_path, monkeypatch):
        """测试不完整内容被拒。"""
        _setup_config(tmp_path)

        import engine.config as cmod
        import engine.ingest as imod
        import engine.filter as fmod
        import engine.indexer as xmod

        monkeypatch.setattr(cmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(imod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(fmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(xmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(cmod, "PROJECT_ROOT", tmp_path)

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir(parents=True)
        raw_file = raw_dir / "bad.md"
        raw_file.write_text("bad", encoding="utf-8")

        bad_output = """---
title: "不完整知识"
---

# 缺少所有必要内容
"""

        from engine.ingest import ingest
        result = ingest(raw_file, bad_output)
        assert result["success"] is False
        assert len(result["errors"]) > 0

    def test_generate_meta_skills_integration(self, tmp_path, monkeypatch):
        """测试元 Skill 生成集成。"""
        _setup_config(tmp_path)

        import engine.skill_gen as smod
        import engine.config as cmod
        monkeypatch.setattr(smod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(cmod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(cmod, "PROJECT_ROOT", tmp_path)

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir(parents=True)

        from engine.skill_gen import generate_meta_skills
        paths = generate_meta_skills()

        assert len(paths) == 3
        for p in paths:
            assert p.exists()
            content = p.read_text(encoding="utf-8")
            assert "---" in content  # Has YAML frontmatter
            assert "name:" in content
