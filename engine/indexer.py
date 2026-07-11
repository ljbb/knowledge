"""索引模块 — 维护 wiki/index.md 和 wiki/log.md"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.config import get_project_root
from engine.file_lock import file_lock


def index_path() -> Path:
    return get_project_root() / "wiki" / "index.md"


def log_path() -> Path:
    return get_project_root() / "wiki" / "log.md"


def init_index() -> None:
    """初始化空的 index.md 文件。"""
    idx = index_path()
    idx.parent.mkdir(parents=True, exist_ok=True)
    if not idx.exists():
        idx.write_text(
            "# 知识索引\n\n"
            "| ID | 标题 | 分类 | 版本 | 状态 | 更新日期 |\n"
            "|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )


def init_log() -> None:
    """初始化空的 log.md 文件。"""
    lg = log_path()
    lg.parent.mkdir(parents=True, exist_ok=True)
    if not lg.exists():
        lg.write_text(
            "# 操作日志\n\n",
            encoding="utf-8",
        )


def add_to_index(entry: dict[str, Any]) -> None:
    """将知识条目添加到 index.md。

    Args:
        entry: 包含 id, title, category, version, status, updated 的字典
    """
    idx = index_path()
    lock = idx.parent / ".index.lock"

    with file_lock(lock):
        line = (
            f"| [{entry['title']}]({entry['category']}/{entry['id']}.md) "
            f"| {entry['category']} "
            f"| v{entry['version']} "
            f"| {entry['status']} "
            f"| {entry['updated']} |\n"
        )

        content = idx.read_text(encoding="utf-8")
        marker = f"({entry['category']}/{entry['id']}.md)"
        if marker in content:
            # 更新现有行
            lines = content.split("\n")
            new_lines = []
            for line_content in lines:
                if marker in line_content:
                    new_lines.append(line.rstrip("\n"))
                else:
                    new_lines.append(line_content)
            idx.write_text("\n".join(new_lines), encoding="utf-8")
        else:
            # 追加新行
            with open(idx, "a", encoding="utf-8") as f:
                f.write(line)


def append_log(action: str, detail: str = "") -> None:
    """追加一条操作日志到 log.md。

    Args:
        action: 操作类型 (ingest, check, update)
        detail: 操作详情
    """
    lg = log_path()
    lock = lg.parent / ".log.lock"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"## [{now}] {action}\n\n{detail}\n\n"

    with file_lock(lock):
        with open(lg, "a", encoding="utf-8") as f:
            f.write(entry)


def read_index() -> list[dict[str, str]]:
    """解析 index.md 返回条目列表。

    Returns:
        [{"title": "...", "category": "...", "version": "...", "status": "...", "updated": "..."}, ...]
    """
    idx = index_path()
    if not idx.exists():
        return []

    entries = []
    for line in idx.read_text(encoding="utf-8").split("\n"):
        if not line.startswith("| [") or line.startswith("| ID"):
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 5:
            title_link = parts[0]
            title = title_link.split("](")[0].lstrip("[")
            entries.append({
                "title": title,
                "category": parts[1],
                "version": parts[2],
                "status": parts[3],
                "updated": parts[4],
            })
    return entries
