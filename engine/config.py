"""配置加载模块 — 读取 schema/config.yaml"""

from pathlib import Path
from typing import Any

import yaml

# 项目根目录（kb.py 所在目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_project_root() -> Path:
    """返回项目根目录的绝对路径。"""
    return PROJECT_ROOT


def load_config() -> dict[str, Any]:
    """加载 schema/config.yaml 并返回配置字典。"""
    config_path = PROJECT_ROOT / "schema" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n请先运行 python kb.py init"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_llm_config(provider: str | None = None) -> dict[str, Any]:
    """获取指定 LLM provider 的配置，默认返回 default provider。"""
    config = load_config()
    llm = config["llm"]
    if provider is None:
        provider = llm["default"]
    if provider not in llm["providers"]:
        raise ValueError(
            f"未知的 LLM provider: {provider}，可用: {list(llm['providers'].keys())}"
        )
    return llm["providers"][provider]


def get_categories() -> list[str]:
    """返回所有知识分类列表。"""
    return load_config()["knowledge_base"]["categories"]


def get_web_config() -> dict[str, Any]:
    """返回 Web 服务配置。"""
    return load_config()["web"]
