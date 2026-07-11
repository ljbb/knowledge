"""测试 search 模块"""

import pytest
import json
from engine.search import search, search_as_json


class TestSearch:
    def test_search_returns_results(self, tmp_path, monkeypatch):
        import engine.search as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        wiki_dir = tmp_path / "wiki" / "infra-daily"
        wiki_dir.mkdir(parents=True)

        entry = """---
id: kb-2026-0711-001
title: "重启 Nginx 服务"
category: infra-daily
tags: [nginx, restart]
---

# 重启 Nginx 服务

在 Nginx 配置更新后需要安全重启服务。
"""
        (wiki_dir / "kb-2026-0711-001.md").write_text(entry, encoding="utf-8")

        results = search("nginx")
        assert len(results) > 0
        assert "重启 Nginx" in results[0]["title"]

    def test_search_filter_by_category(self, tmp_path, monkeypatch):
        import engine.search as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        (tmp_path / "wiki" / "infra-daily").mkdir(parents=True)
        (tmp_path / "wiki" / "automation").mkdir(parents=True)

        base = """---
id: {id}
title: "{title}"
category: {cat}
tags: []
---
# {title}
摘要内容。
"""
        (tmp_path / "wiki" / "infra-daily" / "kb-001.md").write_text(
            base.format(id="kb-001", title="Nginx 相关", cat="infra-daily"), encoding="utf-8"
        )
        (tmp_path / "wiki" / "automation" / "kb-002.md").write_text(
            base.format(id="kb-002", title="自动化脚本", cat="automation"), encoding="utf-8"
        )

        results = search("nginx", category="infra-daily")
        assert len(results) == 1
        assert results[0]["category"] == "infra-daily"

    def test_search_no_results(self, tmp_path, monkeypatch):
        import engine.search as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        (tmp_path / "wiki" / "infra-daily").mkdir(parents=True)

        results = search("不存在的内容")
        assert results == []

    def test_search_as_json_returns_valid_json(self, tmp_path, monkeypatch):
        import engine.search as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        (tmp_path / "wiki" / "infra-daily").mkdir(parents=True)

        json_str = search_as_json("test")
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert isinstance(data, list)

    def test_search_score_higher_for_title_match(self, tmp_path, monkeypatch):
        import engine.search as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        (tmp_path / "wiki" / "infra-daily").mkdir(parents=True)
        (tmp_path / "wiki" / "automation").mkdir(parents=True)

        base = """---
id: {id}
title: "{title}"
category: {cat}
tags: {tags}
---
# {title}
摘要。
"""
        (tmp_path / "wiki" / "infra-daily" / "kb-001.md").write_text(
            base.format(id="kb-001", title="磁盘清理操作", cat="infra-daily", tags="['disk']"),
            encoding="utf-8"
        )
        (tmp_path / "wiki" / "automation" / "kb-002.md").write_text(
            base.format(id="kb-002", title="各种自动化操作", cat="automation", tags="['disk', 'automation']"),
            encoding="utf-8"
        )

        results = search("磁盘清理")
        assert results[0]["title"] == "磁盘清理操作"
