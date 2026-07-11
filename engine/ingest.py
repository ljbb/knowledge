"""导入 Pipeline — 编排完成知识入库全流程"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from engine.config import get_project_root
from engine.filter import check_completeness, check_duplicate, compute_source_hash
from engine.quality import check_entry
from engine.indexer import add_to_index, append_log
from engine.skill_gen import generate_knowledge_skill


def generate_knowledge_id() -> str:
    """生成知识 ID，格式 kb-YYYY-MMDD-NNN。"""
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y-%m%d")
    wiki_dir = get_project_root() / "wiki"
    count = 0
    if wiki_dir.exists():
        for cat_dir in wiki_dir.iterdir():
            if cat_dir.is_dir():
                for f in cat_dir.glob(f"kb-{date_part}-*.md"):
                    count += 1
    seq = str(count + 1).zfill(3)
    return f"kb-{date_part}-{seq}"


def ingest(
    raw_file_path: Path,
    llm_organized_content: str,
    llm_html_content: str = "",
    metadata_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """执行完整的知识导入 Pipeline。

    Pipeline 步骤：
    1. 内容已由 LLM 整理（传入 llm_organized_content）
    2. 分离 frontmatter 和正文
    3. 应用元数据覆盖
    4. 生成 ID
    5. 记录来源信息
    6. 内容完整性检查
    7. 去重检测
    8. 写入 wiki .md 和 .html
    9. 质量检查（Engine A/B/C）
    10. 更新索引 + 日志
    11. 生成 Skill

    Args:
        raw_file_path: 原始文件路径（raw/ 下）
        llm_organized_content: LLM 按模板整理好的 Markdown（含 frontmatter）
        llm_html_content: LLM 生成的 HTML 版本
        metadata_overrides: 覆盖 frontmatter 的字段

    Returns:
        {
            "success": bool,
            "id": "kb-xxx",
            "file": "wiki/category/kb-xxx.md",
            "html_file": "wiki/category/kb-xxx.html",
            "skill_file": "skills/category/kb-xxx.md",
            "version": 1,
            "errors": [...],
            "warnings": [...]
        }
    """
    result = {
        "success": False,
        "id": "",
        "file": "",
        "html_file": "",
        "skill_file": "",
        "version": 1,
        "errors": [],
        "warnings": [],
    }

    # Step 1: 分离 frontmatter 和正文
    try:
        metadata, body = _parse_llm_output(llm_organized_content)
    except Exception as e:
        result["errors"].append(f"内容解析失败: {e}")
        return result

    # Step 2: 应用元数据覆盖
    if metadata_overrides:
        metadata.update(metadata_overrides)

    # Step 3: 生成 ID（如果没有）
    if not metadata.get("id"):
        metadata["id"] = generate_knowledge_id()

    # Step 4: 记录来源信息
    raw_abs = raw_file_path.resolve()
    try:
        metadata["source_file"] = str(raw_abs.relative_to(get_project_root()))
    except ValueError:
        metadata["source_file"] = str(raw_file_path)
    metadata["source_hash"] = compute_source_hash(raw_file_path)
    metadata["created"] = metadata.get("created", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    metadata["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    metadata["version"] = metadata.get("version", 1)
    metadata["status"] = metadata.get("status", "draft")

    kb_id = metadata["id"]
    category = metadata.get("category", "infra-daily")
    result["id"] = kb_id
    result["version"] = metadata["version"]

    # Step 5: 内容完整性检查
    completeness = check_completeness(body, metadata)
    if not completeness["passed"]:
        result["errors"].append(
            f"内容不完整，缺少: {', '.join(completeness['missing'])}"
        )
        for suggestion in completeness["suggestions"]:
            result["warnings"].append(suggestion)
        return result

    # Step 6: 去重检测
    dup_check = check_duplicate(body, metadata.get("title", ""), category)
    if dup_check["action"] == "update_version":
        if dup_check.get("matched_id"):
            # Find existing version from the matched entry
            matched_version = _get_existing_version(dup_check["matched_id"])
            metadata["version"] = matched_version + 1
            result["version"] = metadata["version"]
            result["warnings"].append(
                f"检测到相似知识 [{dup_check['matched_id']}] {dup_check['matched_title']}，"
                f"相似度: {dup_check['similarity']}，作为新版本入库 (v{metadata['version']})"
            )
    elif dup_check["action"] == "reject":
        result["errors"].append(
            f"知识重复 — 匹配到 [{dup_check['matched_id']}] {dup_check['matched_title']}，"
            f"相似度: {dup_check['similarity']}"
        )
        return result

    # Step 7: 重建完整 Markdown 并写入
    final_md = _build_markdown(metadata, body)

    wiki_dir = get_project_root() / "wiki" / category
    wiki_dir.mkdir(parents=True, exist_ok=True)

    md_path = wiki_dir / f"{kb_id}.md"
    md_path.write_text(final_md, encoding="utf-8")
    result["file"] = str(md_path.relative_to(get_project_root()))

    # Step 8: 写入 HTML
    html_path = wiki_dir / f"{kb_id}.html"
    if llm_html_content:
        html_path.write_text(llm_html_content, encoding="utf-8")
    else:
        html_path.write_text(
            f"<p>HTML 版本待生成。请通过 LLM 对 {kb_id}.md 生成 HTML。</p>",
            encoding="utf-8",
        )
    result["html_file"] = str(html_path.relative_to(get_project_root()))

    # Step 9: 质量检查（Engine 端 A/B/C）
    quality_result = check_entry(md_path)
    if not quality_result["overall"]:
        for level in ["level_a", "level_b", "level_c"]:
            for issue in quality_result[level]["issues"]:
                result["errors"].append(f"[{level}] {issue}")
        return result

    # Step 10: 更新索引
    add_to_index({
        "id": kb_id,
        "title": metadata["title"],
        "category": category,
        "version": metadata["version"],
        "status": metadata["status"],
        "updated": metadata["updated"],
    })

    # Step 11: 追加日志
    append_log(
        "ingest",
        f"ID: {kb_id}\n"
        f"标题: {metadata['title']}\n"
        f"分类: {category}\n"
        f"版本: v{metadata['version']}\n"
        f"来源: {metadata['source_file']}\n"
        f"来源哈希: {metadata['source_hash']}",
    )

    # Step 12: 生成 Skill
    skill_path = generate_knowledge_skill(md_path)
    result["skill_file"] = str(skill_path.relative_to(get_project_root()))

    result["success"] = True
    return result


def _parse_llm_output(content: str) -> tuple[dict[str, Any], str]:
    """解析 LLM 输出的 Markdown，分离 frontmatter 和正文。"""
    import frontmatter as fm
    post = fm.loads(content)
    return dict(post.metadata), post.content


def _build_markdown(metadata: dict[str, Any], body: str) -> str:
    """将 metadata 和 body 组合为完整的 Markdown 文件。"""
    frontmatter_str = yaml.dump(
        metadata,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).strip()

    return f"---\n{frontmatter_str}\n---\n\n{body}"


def _get_existing_version(kb_id: str) -> int:
    """从已存在的知识条目获取版本号。"""
    wiki_dir = get_project_root() / "wiki"
    for cat_dir in wiki_dir.iterdir():
        if cat_dir.is_dir():
            candidate = cat_dir / f"{kb_id}.md"
            if candidate.exists():
                import frontmatter as fm
                post = fm.load(str(candidate))
                return post.metadata.get("version", 1)
    return 1
