"""管理路由 — 上传、导入、配置"""

from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from engine.config import get_project_root
from engine.quality import check_all, check_summary
from web.core import templates

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/", response_class=HTMLResponse)
async def admin_index(request: Request):
    """管理后台首页。"""
    raw_dir = get_project_root() / "raw"
    raw_files = [
        {"name": f.name, "size": f.stat().st_size}
        for f in raw_dir.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ]

    return templates.TemplateResponse(request, "admin.html", {
        "section": "index",
        "raw_files": raw_files,
    })


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """上传页面。"""
    return templates.TemplateResponse(request, "admin.html", {
        "section": "upload",
    })


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """处理文件上传。"""
    raw_dir = get_project_root() / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    file_path = raw_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    return JSONResponse({
        "success": True,
        "filename": file.filename,
        "size": len(content),
    })


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request):
    """健康检查报告页面。"""
    results = check_all()
    summary = check_summary(results)

    return templates.TemplateResponse(request, "health.html", {
        "results": results,
        "summary": summary,
    })
