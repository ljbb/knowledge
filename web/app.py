"""FastAPI 应用入口 — 注册路由。"""

from web.core import app
from web.routes import pages, admin, api

app.include_router(pages.router)
app.include_router(admin.router)
app.include_router(api.router)
