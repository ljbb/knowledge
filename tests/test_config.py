"""测试 config 模块"""

import pytest
import yaml
from pathlib import Path
from engine.config import load_config, get_llm_config, get_categories, get_project_root


class TestConfig:
    def test_project_root_is_knowledge_base_dir(self):
        root = get_project_root()
        assert (root / "schema" / "config.yaml").exists()

    def test_load_config_returns_dict(self):
        config = load_config()
        assert isinstance(config, dict)
        assert "knowledge_base" in config
        assert "llm" in config

    def test_load_config_has_four_categories(self):
        config = load_config()
        categories = config["knowledge_base"]["categories"]
        assert len(categories) == 4
        assert "infra-daily" in categories
        assert "infra-violation" in categories
        assert "automation" in categories
        assert "harbor" in categories

    def test_get_llm_config_default(self):
        llm_cfg = get_llm_config()
        assert "type" in llm_cfg
        assert "api_key_env" in llm_cfg

    def test_get_llm_config_specific_provider(self):
        llm_cfg = get_llm_config("claude")
        assert llm_cfg["type"] == "anthropic"

    def test_get_llm_config_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="未知的 LLM provider"):
            get_llm_config("nonexistent")

    def test_get_categories(self):
        cats = get_categories()
        assert isinstance(cats, list)
        assert "infra-daily" in cats

    def test_load_config_missing_file_raises(self, tmp_path, monkeypatch):
        import engine.config as mod
        monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            load_config()
