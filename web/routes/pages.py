"""页面路由 — 知识库阅读"""

from pathlib import Path

import markdown
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from engine.config import get_project_root, load_config
from web.core import templates

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """知识库主页。"""
    config = load_config()
    categories = config["knowledge_base"]["categories"]

    wiki_dir = get_project_root() / "wiki"
    category_counts = {}
    for cat in categories:
        cat_dir = wiki_dir / cat
        if cat_dir.exists():
            category_counts[cat] = len(list(cat_dir.glob("*.md")))
        else:
            category_counts[cat] = 0

    return templates.TemplateResponse(request, "index.html", {
        "config": config,
        "categories": categories,
        "category_counts": category_counts,
    })


@router.get("/kb/{category}/{kb_id}", response_class=HTMLResponse)
async def view_knowledge(request: Request, category: str, kb_id: str):
    """单条知识页面。"""
    wiki_dir = get_project_root() / "wiki"
    html_path = wiki_dir / category / f"{kb_id}.html"
    md_path = wiki_dir / category / f"{kb_id}.md"

    if html_path.exists():
        html_content = html_path.read_text(encoding="utf-8")
        return templates.TemplateResponse(request, "knowledge.html", {
            "kb_id": kb_id,
            "category": category,
            "content": html_content,
            "is_raw_html": True,
        })

    if md_path.exists():
        import frontmatter
        post = frontmatter.load(str(md_path))
        md_html = markdown.markdown(
            post.content,
            extensions=["fenced_code", "codehilite", "tables"],
        )
        diagram = post.metadata.get("diagram", "")
        meta_html = "<dl>"
        for key in ["id", "title", "category", "version", "status", "author", "updated"]:
            val = post.metadata.get(key, "")
            meta_html += f"<dt>{key}</dt><dd>{val}</dd>"
        meta_html += "</dl>"

        full_html = f"""
        <div class="knowledge-meta">{meta_html}</div>
        <div class="knowledge-body">{md_html}</div>
        """
        if diagram:
            full_html += f"""
            <div class="mermaid">{diagram}</div>
            <script>mermaid.initialize({{startOnLoad:true}});</script>
            """

        return templates.TemplateResponse(request, "knowledge.html", {
            "kb_id": kb_id,
            "category": category,
            "content": full_html,
            "is_raw_html": False,
        })

    return HTMLResponse("<h1>知识条目不存在</h1>", status_code=404)


@router.get("/kb/{category}", response_class=HTMLResponse)
async def view_category(request: Request, category: str):
    """分类页面。"""
    wiki_dir = get_project_root() / "wiki" / category
    entries = []
    if wiki_dir.exists():
        for md_file in sorted(wiki_dir.glob("*.md")):
            import frontmatter
            try:
                post = frontmatter.load(str(md_file))
                entries.append({
                    "id": post.metadata.get("id", md_file.stem),
                    "title": post.metadata.get("title", md_file.stem),
                    "version": post.metadata.get("version", 1),
                    "status": post.metadata.get("status", "draft"),
                    "updated": post.metadata.get("updated", ""),
                })
            except Exception:
                pass

    return templates.TemplateResponse(request, "index.html", {
        "category": category,
        "entries": entries,
        "categories": load_config()["knowledge_base"]["categories"],
        "category_counts": {},
    })
