"""测试 quality 模块"""

import pytest
from pathlib import Path
from engine.quality import check_entry, check_all, check_summary


VALID_ENTRY = """---
id: kb-2026-0711-001
title: "测试知识条目"
category: infra-daily
tags: [test, demo]
author: "测试者"
created: 2026-07-11
updated: 2026-07-11
version: 1
status: verified
source_file: raw/test.md
source_hash: sha256:abc123
---

# 测试知识条目

## 背景/场景
测试场景描述。

## 操作步骤
1. 运行测试命令：`python test.py`
2. 检查输出

## 验证证据
- [ ] 测试通过
- [ ] 无错误日志

## 回滚方案
1. 撤销更改

## 关联知识
- [[other-knowledge]]
"""


class TestQuality:
    def test_check_valid_entry_passes_all_levels(self, tmp_path, monkeypatch):
        import engine.quality as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        wiki_dir = tmp_path / "wiki" / "infra-daily"
        wiki_dir.mkdir(parents=True)
        entry_file = wiki_dir / "kb-2026-0711-001.md"
        entry_file.write_text(VALID_ENTRY, encoding="utf-8")

        # Create the referenced wiki link target so dead-link check passes
        (wiki_dir / "other-knowledge.md").write_text("", encoding="utf-8")

        result = check_entry(entry_file)
        assert result["overall"] is True

    def test_check_entry_missing_required_field_fails_level_a(self, tmp_path, monkeypatch):
        import engine.quality as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        wiki_dir = tmp_path / "wiki" / "infra-daily"
        wiki_dir.mkdir(parents=True)
        entry_file = wiki_dir / "kb-2026-0711-001.md"
        entry_file.write_text("""---
id: kb-2026-0711-001
title: "测试"
---
# 无必填字段
""", encoding="utf-8")

        result = check_entry(entry_file)
        assert result["level_a"]["passed"] is False
        assert any("category" in i for i in result["level_a"]["issues"])

    def test_check_entry_no_steps_fails_level_b(self, tmp_path, monkeypatch):
        import engine.quality as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        wiki_dir = tmp_path / "wiki" / "infra-daily"
        wiki_dir.mkdir(parents=True)
        entry_file = wiki_dir / "kb-2026-0711-001.md"
        entry_file.write_text("""---
id: kb-2026-0711-001
title: "测试"
category: infra-daily
tags: [test]
author: "人"
created: 2026-07-11
updated: 2026-07-11
version: 1
status: verified
source_file: raw/t.md
source_hash: sha256:abc
---

# 无步骤条目

## 背景
无步骤的知识条目。
""", encoding="utf-8")

        result = check_entry(entry_file)
        assert result["level_b"]["passed"] is False
        assert any("操作步骤" in i for i in result["level_b"]["issues"])

    def test_check_entry_no_cross_ref_fails_level_c(self, tmp_path, monkeypatch):
        import engine.quality as mod
        monkeypatch.setattr(mod, "get_project_root", lambda: tmp_path)

        wiki_dir = tmp_path / "wiki" / "infra-daily"
        wiki_dir.mkdir(parents=True)
        entry_file = wiki_dir / "kb-2026-0711-001.md"
        entry_file.write_text("""---
id: kb-2026-0711-001
title: "测试"
category: infra-daily
tags: [test]
author: "人"
created: 2026-07-11
updated: 2026-07-11
version: 1
status: verified
source_file: raw/t.md
source_hash: sha256:abc
---

# 孤立条目

## 背景/场景
无交叉引用。

## 操作步骤
1. 做某事

## 验证证据
- [ ] 检查

## 回滚方案
1. 回滚
""", encoding="utf-8")

        result = check_entry(entry_file)
        assert result["level_c"]["passed"] is False
        assert any("交叉引用" in i or "孤立" in i for i in result["level_c"]["issues"])

    def test_check_summary_formats_correctly(self):
        results = [
            {
                "id": "kb-test-001",
                "file": "wiki/infra-daily/kb-test-001.md",
                "level_a": {"passed": True, "issues": []},
                "level_b": {"passed": True, "issues": []},
                "level_c": {"passed": True, "issues": []},
                "overall": True,
            },
            {
                "id": "kb-test-002",
                "file": "wiki/automation/kb-test-002.md",
                "level_a": {"passed": False, "issues": ["缺少字段: title"]},
                "level_b": {"passed": False, "issues": ["缺少回滚方案"]},
                "level_c": {"passed": False, "issues": ["无交叉引用"]},
                "overall": False,
            },
        ]
        summary = check_summary(results)
        assert "总知识条目: 2" in summary
        assert "通过: 1" in summary
        assert "失败: 1" in summary
        assert "kb-test-002" in summary
