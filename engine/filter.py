"""内容过滤模块 — 检查知识内容完整性，去重检测"""

import hashlib
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import frontmatter

from engine.config import get_project_root


def check_completeness(content: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """检查知识内容的完整性。

    Args:
        content: Markdown 正文内容
        metadata: frontmatter 元数据

    Returns:
        {
            "passed": bool,
            "missing": ["背景/场景", "操作步骤", ...],
            "suggestions": ["建议补充...", ...]
        }
    """
    missing = []
    suggestions = []

    if "## 背景/场景" not in content and "## 背景" not in content:
        missing.append("背景/场景描述")
        suggestions.append("请添加 ## 背景/场景 段落，说明在什么情况下使用该知识")

    if "## 操作步骤" not in content and "## 步骤" not in content:
        missing.append("操作步骤")
        suggestions.append("请添加 ## 操作步骤 段落，列出具体执行步骤")

    if "## 验证证据" not in content and "## 验证" not in content:
        missing.append("验证证据")
        suggestions.append("请添加 ## 验证证据 段落，描述如何验证操作成功")

    if not metadata.get("author"):
        missing.append("作者信息")
        suggestions.append("请在 frontmatter 中添加 author 字段")

    if "## 回滚" not in content:
        missing.append("回滚方案")
        suggestions.append("请添加 ## 回滚方案 段落，描述操作失败时的回滚步骤")

    return {
        "passed": len(missing) == 0,
        "missing": missing,
        "suggestions": suggestions,
    }


def check_duplicate(
    new_content: str,
    new_title: str,
    category: str | None = None,
) -> dict[str, Any]:
    """检测是否与现有知识重复。

    Args:
        new_content: 新知识正文
        new_title: 新知识标题
        category: 限定检查的分类

    Returns:
        {
            "is_duplicate": bool,
            "matched_id": str | None,
            "matched_title": str | None,
            "similarity": float,
            "action": "create_new" | "update_version" | "reject"
        }
    """
    wiki_dir = get_project_root() / "wiki"
    categories = [category] if category else ["infra-daily", "infra-violation", "automation", "harbor"]

    best_match = None
    best_score = 0.0

    for cat in categories:
        cat_dir = wiki_dir / cat
        if not cat_dir.exists():
            continue
        for md_file in cat_dir.glob("*.md"):
            try:
                post = frontmatter.load(str(md_file))
                existing_title = post.metadata.get("title", "")
                existing_content = post.content

                title_score = SequenceMatcher(
                    None, new_title.lower(), existing_title.lower()
                ).ratio()

                content_score = SequenceMatcher(
                    None, new_content.lower()[:2000], existing_content.lower()[:2000]
                ).ratio()

                combined = title_score * 0.4 + content_score * 0.6

                if combined > best_score:
                    best_score = combined
                    best_match = {
                        "id": post.metadata.get("id", md_file.stem),
                        "title": existing_title,
                        "file": str(md_file.relative_to(get_project_root())),
                        "version": post.metadata.get("version", 1),
                    }
            except Exception:
                continue

    if best_score < 0.4:
        return {
            "is_duplicate": False,
            "matched_id": None,
            "matched_title": None,
            "similarity": round(best_score, 2),
            "action": "create_new",
        }
    elif best_score < 0.75:
        return {
            "is_duplicate": False,
            "matched_id": best_match["id"] if best_match else None,
            "matched_title": best_match["title"] if best_match else None,
            "similarity": round(best_score, 2),
            "action": "create_new",
        }
    else:
        return {
            "is_duplicate": True,
            "matched_id": best_match["id"] if best_match else None,
            "matched_title": best_match["title"] if best_match else None,
            "similarity": round(best_score, 2),
            "action": "update_version"
            if best_match and best_match.get("version")
            else "reject",
        }


def compute_source_hash(file_path: Path) -> str:
    """计算原始文件的 SHA256 哈希。"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()[:16]}"
