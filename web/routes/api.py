"""API 路由 — 搜索、知识获取、分类"""

from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from engine.search import search
from engine.config import get_project_root, load_config

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/search")
async def api_search(
    q: str = Query(..., description="搜索关键词"),
    category: str | None = Query(None, description="限定分类"),
    top_n: int = Query(5, description="返回结果数"),
):
    """搜索知识库。"""
    results = search(q, category, top_n)
    return JSONResponse({"results": results, "query": q, "count": len(results)})


@router.get("/kb/{kb_id}")
async def api_get_knowledge(kb_id: str):
    """获取单条知识（JSON 格式）。"""
    import frontmatter

    wiki_dir = get_project_root() / "wiki"
    for cat_dir in wiki_dir.iterdir():
        if cat_dir.is_dir():
            md_path = cat_dir / f"{kb_id}.md"
            if md_path.exists():
                post = frontmatter.load(str(md_path))
                return JSONResponse({
                    "metadata": dict(post.metadata),
                    "content": post.content,
                })

    return JSONResponse({"error": "not found"}, status_code=404)


@router.get("/categories")
async def api_categories():
    """获取所有分类。"""
    return JSONResponse(load_config()["knowledge_base"]["categories"])
