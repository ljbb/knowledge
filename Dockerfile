# ============================================================
# DevOps & Infra 知识库 — Dockerfile
# ============================================================

FROM python:3.12-slim

LABEL org.opencontainers.image.title="DevOps & Infra Knowledge Base"
LABEL org.opencontainers.image.description="LLM-driven knowledge base for DevOps and Infra maintenance"
LABEL org.opencontainers.image.version="0.1.0"

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# 创建工作目录
WORKDIR /app

# 先复制依赖文件（利用 Docker 缓存层）
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建持久化目录（运行时挂载卷可覆盖）
RUN mkdir -p /app/raw /app/wiki /app/schema /app/skills

# 暴露 Web 服务端口
EXPOSE 8000

# 健康检查 — 每 30 秒检查 Web 服务是否响应
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# 入口：初始化 + 启动 Web 服务
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
