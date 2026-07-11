"""测试 indexer 模块"""

import pytest
from engine.indexer import (
    init_index,
    init_log,
    add_to_index,
    append_log,
    read_index,
    index_path,
    log_path,
)


class TestIndexer:
    def test_init_index_creates_file(self, tmp_path, monkeypatch):
        import engine.indexer as mod
        wiki = tmp_path / "wiki"
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(mod, "index_path", lambda: wiki / "index.md")

        wiki.mkdir(exist_ok=True)
        init_index()
        assert (wiki / "index.md").exists()
        content = (wiki / "index.md").read_text(encoding="utf-8")
        assert "知识索引" in content

    def test_init_log_creates_file(self, tmp_path, monkeypatch):
        import engine.indexer as mod
        wiki = tmp_path / "wiki"
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(mod, "log_path", lambda: wiki / "log.md")

        wiki.mkdir(exist_ok=True)
        init_log()
        assert (wiki / "log.md").exists()
        content = (wiki / "log.md").read_text(encoding="utf-8")
        assert "操作日志" in content

    def test_add_to_index_new_entry(self, tmp_path, monkeypatch):
        import engine.indexer as mod
        wiki = tmp_path / "wiki"
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(mod, "index_path", lambda: wiki / "index.md")

        wiki.mkdir(exist_ok=True)
        init_index()

        entry = {
            "id": "kb-2026-0711-001",
            "title": "测试条目",
            "category": "infra-daily",
            "version": 1,
            "status": "verified",
            "updated": "2026-07-11",
        }
        add_to_index(entry)

        content = (wiki / "index.md").read_text(encoding="utf-8")
        assert "测试条目" in content
        assert "infra-daily" in content

    def test_add_to_index_update_existing(self, tmp_path, monkeypatch):
        import engine.indexer as mod
        wiki = tmp_path / "wiki"
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(mod, "index_path", lambda: wiki / "index.md")

        wiki.mkdir(exist_ok=True)
        init_index()

        entry = {
            "id": "kb-2026-0711-001",
            "title": "测试条目",
            "category": "infra-daily",
            "version": 1,
            "status": "draft",
            "updated": "2026-07-11",
        }
        add_to_index(entry)

        # 更新版本
        entry["version"] = 2
        entry["status"] = "verified"
        add_to_index(entry)

        content = (wiki / "index.md").read_text(encoding="utf-8")
        assert "v2" in content
        assert "verified" in content

    def test_append_log_writes_entry(self, tmp_path, monkeypatch):
        import engine.indexer as mod
        wiki = tmp_path / "wiki"
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(mod, "log_path", lambda: wiki / "log.md")

        wiki.mkdir(exist_ok=True)
        init_log()

        append_log("ingest", "导入测试知识")

        content = (wiki / "log.md").read_text(encoding="utf-8")
        assert "ingest" in content
        assert "导入测试知识" in content

    def test_read_index_returns_entries(self, tmp_path, monkeypatch):
        import engine.indexer as mod
        wiki = tmp_path / "wiki"
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(mod, "index_path", lambda: wiki / "index.md")

        wiki.mkdir(exist_ok=True)
        init_index()

        add_to_index({
            "id": "kb-2026-0711-001",
            "title": "条目A",
            "category": "infra-daily",
            "version": 1,
            "status": "verified",
            "updated": "2026-07-11",
        })
        add_to_index({
            "id": "kb-2026-0711-002",
            "title": "条目B",
            "category": "automation",
            "version": 3,
            "status": "verified",
            "updated": "2026-07-10",
        })

        entries = read_index()
        assert len(entries) >= 1

    def test_read_index_empty_file(self, tmp_path, monkeypatch):
        import engine.indexer as mod
        wiki = tmp_path / "wiki"
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)
        monkeypatch.setattr(mod, "index_path", lambda: wiki / "index.md")

        wiki.mkdir(exist_ok=True)
        init_index()

        entries = read_index()
        assert entries == []
