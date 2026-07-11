"""FastAPI 核心 — app 实例和 templates，避免循环导入。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(
    title="DevOps & Infra 知识库",
    version="0.1.0",
)

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

wiki_dir = Path(__file__).resolve().parent.parent / "wiki"
wiki_dir.mkdir(parents=True, exist_ok=True)
app.mount("/wiki-files", StaticFiles(directory=str(wiki_dir)), name="wiki-files")
