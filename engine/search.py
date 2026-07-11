"""搜索模块 — 在知识库中检索匹配条目"""

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import frontmatter

from engine.config import get_project_root, load_config


def search(
    query: str,
    category: str | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """搜索知识库，返回匹配结果。

    Args:
        query: 搜索关键词
        category: 可选，限定分类
        top_n: 返回前 N 个结果

    Returns:
        [
            {
                "id": "kb-xxx",
                "title": "...",
                "category": "...",
                "file": "wiki/infra-daily/kb-xxx.md",
                "skill_path": "skills/infra-daily/kb-xxx.md",
                "summary": "...",
                "score": 0.95
            },
            ...
        ]
    """
    wiki_dir = get_project_root() / "wiki"
    categories = [category] if category else load_config()["knowledge_base"]["categories"]

    candidates = _collect_candidates(wiki_dir, categories)
    scored = _score_candidates(query, candidates)
    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[:top_n]


def _collect_candidates(
    wiki_dir: Path, categories: list[str]
) -> list[dict[str, Any]]:
    """收集所有候选知识条目。"""
    candidates = []
    for cat in categories:
        cat_dir = wiki_dir / cat
        if not cat_dir.exists():
            continue
        for md_file in cat_dir.glob("*.md"):
            try:
                post = frontmatter.load(str(md_file))
                metadata = post.metadata
                content = post.content

                summary = ""
                for line in content.split("\n"):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        summary = stripped[:200]
                        break

                candidates.append({
                    "id": metadata.get("id", md_file.stem),
                    "title": metadata.get("title", md_file.stem),
                    "category": metadata.get("category", cat),
                    "file": str(md_file.relative_to(get_project_root())),
                    "skill_path": f"skills/{cat}/{md_file.name}",
                    "summary": summary,
                    "tags": metadata.get("tags", []),
                })
            except Exception:
                continue

    return candidates


def _score_candidates(
    query: str, candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """对候选条目进行相关性评分。"""
    query_lower = query.lower()
    scored = []

    for c in candidates:
        score = 0.0

        title_lower = c["title"].lower()
        if query_lower in title_lower:
            score += 0.5
        else:
            score += 0.3 * SequenceMatcher(None, query_lower, title_lower).ratio()

        summary_lower = c["summary"].lower()
        if query_lower in summary_lower:
            score += 0.3
        else:
            score += 0.1 * SequenceMatcher(None, query_lower, summary_lower).ratio()

        tag_match = 0.0
        for tag in c["tags"]:
            if query_lower in tag.lower() or tag.lower() in query_lower:
                tag_match = 0.2
                break
        score += tag_match

        c["score"] = round(min(score, 1.0), 2)
        scored.append(c)

    return scored


def search_as_json(query: str, category: str | None = None, top_n: int = 5) -> str:
    """搜索并返回 JSON 字符串，供 CLI 调用。"""
    results = search(query, category, top_n)
    return json.dumps(results, ensure_ascii=False, indent=2)
