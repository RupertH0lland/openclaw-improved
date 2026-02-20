"""Configuration loader - reads from config/*.yaml. No .env required (CLI stores secrets in config)."""
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class Settings:
    """API keys and secrets - from config file first, then env."""

    def __init__(self, project_root: Path | None = None):
        root = project_root or Path(__file__).parent.parent
        config_path = root / "config" / "settings.yaml"
        secrets = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            secrets = data.get("secrets", {})
        self.openai_api_key = secrets.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")
        self.anthropic_api_key = (
            secrets.get("claude_code_token")
            or secrets.get("anthropic_api_key")
            or os.getenv("ANTHROPIC_API_KEY", "")
        )
        self.telegram_bot_token = secrets.get("telegram_bot_token") or os.getenv("TELEGRAM_BOT_TOKEN", "")


class DashboardConfig(BaseModel):
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    password_hash: str = ""


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""


class ResourceLimits(BaseModel):
    enabled: bool = False
    max_concurrent_agents: int = 10
    max_tokens_per_request: int = 4096
    max_file_size_mb: int = 50


class BudgetConfig(BaseModel):
    enabled: bool = False
    daily_usd: float = 10.0
    monthly_usd: float = 100.0


class SettingsYaml(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data_dir: str = "./data"
    use_subagents: bool = False
    output_dir: str = "./data/output"
    dashboard: DashboardConfig = DashboardConfig()
    telegram: TelegramConfig = TelegramConfig()
    resource_limits: ResourceLimits = ResourceLimits()
    budget: BudgetConfig = BudgetConfig()


class OllamaConfig(BaseModel):
    enabled: bool = False
    base_url: str = "http://localhost:11434"
    models: list[str] = []


class ModelsConfig(BaseModel):
    routing: dict[str, str] = {}
    ollama: OllamaConfig = OllamaConfig()


def load_config(project_root: Path | None = None) -> tuple[SettingsYaml, ModelsConfig]:
    """Load settings and models config from YAML files."""
    root = project_root or Path(__file__).parent.parent
    config_dir = root / "config"
    data_dir = root / "data"

    settings_path = config_dir / "settings.yaml"
    models_path = config_dir / "models.yaml"

    settings_data: dict = {}
    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as f:
            settings_data = yaml.safe_load(f) or {}

    models_data: dict = {"routing": {}, "ollama": {"enabled": False}}
    if models_path.exists():
        with open(models_path, encoding="utf-8") as f:
            models_data = yaml.safe_load(f) or models_data

    settings = SettingsYaml(**{**settings_data})
    models = ModelsConfig(**models_data)

    return settings, models


def get_env(project_root: Path | None = None) -> Settings:
    """Load API keys from config file (written by CLI) or env."""
    return Settings(project_root)
