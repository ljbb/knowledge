"""质量检查模块 — A/B/C 三级检查"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
import markdown

from engine.config import get_project_root, load_config


def check_entry(file_path: Path) -> dict[str, Any]:
    """对单个知识条目执行三级质量检查。

    Args:
        file_path: 知识条目 .md 文件路径

    Returns:
        {
            "id": "kb-xxx",
            "file": "wiki/infra-daily/kb-xxx.md",
            "level_a": {"passed": bool, "issues": [...]},
            "level_b": {"passed": bool, "issues": [...]},
            "level_c": {"passed": bool, "issues": [...]},
            "overall": bool
        }
    """
    result = {
        "id": file_path.stem,
        "file": str(file_path.relative_to(get_project_root())),
        "level_a": {"passed": True, "issues": []},
        "level_b": {"passed": True, "issues": []},
        "level_c": {"passed": True, "issues": []},
    }

    try:
        post = frontmatter.load(str(file_path))
    except Exception as e:
        result["level_a"]["passed"] = False
        result["level_a"]["issues"].append(f"文件无法解析: {e}")
        result["overall"] = False
        return result

    _check_level_a(result, post, file_path)
    _check_level_b(result, post)
    _check_level_c(result, post)

    result["overall"] = (
        result["level_a"]["passed"]
        and result["level_b"]["passed"]
        and result["level_c"]["passed"]
    )
    return result


def _check_level_a(result: dict, post, file_path: Path) -> None:
    """A 级检查：必填字段、死链接、Markdown 语法。"""
    required_fields = [
        "id", "title", "category", "tags", "author",
        "created", "updated", "version", "status",
        "source_file", "source_hash",
    ]
    metadata = post.metadata

    for field in required_fields:
        if field not in metadata or metadata[field] in (None, "", []):
            result["level_a"]["passed"] = False
            result["level_a"]["issues"].append(f"缺少必填字段: {field}")

    valid_categories = load_config()["knowledge_base"]["categories"]
    if metadata.get("category") not in valid_categories:
        result["level_a"]["passed"] = False
        result["level_a"]["issues"].append(
            f"无效分类 '{metadata.get('category')}'，有效值: {valid_categories}"
        )

    kb_id = metadata.get("id", "")
    if not re.match(r"^kb-\d{4}-\d{4}-\d{3}$", kb_id):
        result["level_a"]["passed"] = False
        result["level_a"]["issues"].append(f"ID 格式不正确: {kb_id}，应为 kb-YYYY-MMDD-NNN")

    content = post.content
    wiki_links = re.findall(r"\[\[([^\]]+)\]\]", content)
    for link in wiki_links:
        found = False
        wiki_dir = get_project_root() / "wiki"
        for cat in valid_categories:
            if (wiki_dir / cat / f"{link}.md").exists():
                found = True
                break
        if not found:
            result["level_a"]["passed"] = False
            result["level_a"]["issues"].append(f"死链接: [[{link}]] — 目标知识不存在")

    try:
        markdown.markdown(content)
    except Exception as e:
        result["level_a"]["passed"] = False
        result["level_a"]["issues"].append(f"Markdown 语法错误: {e}")


def _check_level_b(result: dict, post) -> None:
    """B 级检查：步骤可操作性、验证证据、回滚方案。"""
    content = post.content

    if "## 操作步骤" not in content and "## 步骤" not in content:
        result["level_b"]["passed"] = False
        result["level_b"]["issues"].append("缺少操作步骤")
    else:
        section_key = "## 操作步骤" if "## 操作步骤" in content else "## 步骤"
        steps_section = content.split(section_key)[-1]
        steps_section = steps_section.split("## ")[0] if "## " in steps_section else steps_section
        if "`" not in steps_section and "1." not in steps_section:
            result["level_b"]["passed"] = False
            result["level_b"]["issues"].append("操作步骤缺少可执行命令或编号步骤")

    if "## 验证证据" not in content and "## 验证" not in content:
        result["level_b"]["passed"] = False
        result["level_b"]["issues"].append("缺少验证证据")
    else:
        section_key = "## 验证证据" if "## 验证证据" in content else "## 验证"
        verify_section = content.split(section_key)[-1]
        verify_section = verify_section.split("## ")[0] if "## " in verify_section else verify_section
        if "- [ ]" not in verify_section and "- [x]" not in verify_section:
            result["level_b"]["passed"] = False
            result["level_b"]["issues"].append("验证证据缺少检查清单 (- [ ] 格式)")

    if "## 回滚" not in content:
        result["level_b"]["passed"] = False
        result["level_b"]["issues"].append("缺少回滚方案")


def _check_level_c(result: dict, post) -> None:
    """C 级检查：新鲜度、交叉引用、孤立检测。"""
    metadata = post.metadata
    content = post.content
    config = load_config()
    freshness_days = config.get("quality", {}).get("freshness_warn_days", 40)

    updated_str = metadata.get("updated", "")
    try:
        updated = datetime.strptime(str(updated_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_old = (now - updated).days
        if days_old > freshness_days:
            result["level_c"]["passed"] = False
            result["level_c"]["issues"].append(f"知识已 {days_old} 天未更新（阈值: {freshness_days} 天）")
    except (ValueError, TypeError):
        result["level_c"]["passed"] = False
        result["level_c"]["issues"].append(f"无法解析更新日期: {updated_str}")

    wiki_links = re.findall(r"\[\[([^\]]+)\]\]", content)
    if not wiki_links:
        result["level_c"]["passed"] = False
        result["level_c"]["issues"].append("无交叉引用 — 知识孤立（缺少 [[关联知识]]）")


def check_all(category: str | None = None) -> list[dict[str, Any]]:
    """对所有知识条目执行质量检查。"""
    results = []
    wiki_dir = get_project_root() / "wiki"
    categories = [category] if category else load_config()["knowledge_base"]["categories"]

    for cat in categories:
        cat_dir = wiki_dir / cat
        if not cat_dir.exists():
            continue
        for md_file in sorted(cat_dir.glob("*.md")):
            results.append(check_entry(md_file))

    return results


def check_summary(results: list[dict[str, Any]]) -> str:
    """生成可读的检查摘要。"""
    total = len(results)
    passed = sum(1 for r in results if r["overall"])
    level_a_issues = sum(len(r["level_a"]["issues"]) for r in results)
    level_b_issues = sum(len(r["level_b"]["issues"]) for r in results)
    level_c_issues = sum(len(r["level_c"]["issues"]) for r in results)

    lines = [
        "=== 知识库健康检查 ===",
        f"时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"总知识条目: {total}",
        f"通过: {passed} / 失败: {total - passed}",
        "",
        f"A 级（基础）: {'PASS' if level_a_issues == 0 else f'{level_a_issues} 个问题'}",
        f"B 级（内容）: {'PASS' if level_b_issues == 0 else f'{level_b_issues} 个问题'}",
        f"C 级（全面）: {'PASS' if level_c_issues == 0 else f'{level_c_issues} 个问题'}",
    ]

    for r in results:
        all_issues = (
            r["level_a"]["issues"] +
            r["level_b"]["issues"] +
            r["level_c"]["issues"]
        )
        if all_issues:
            lines.append(f"\n[{r['id']}] {r['file']}:")
            for issue in all_issues:
                lines.append(f"  - {issue}")

    return "\n".join(lines)
