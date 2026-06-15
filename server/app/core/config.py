"""Application configuration loaded from environment variables."""

import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 仓库根目录: server/app/core/config.py -> parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_PATH = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    """全局配置。优先从仓库根目录的 .env 读取，其次使用默认值。"""

    # Application
    APP_NAME: str = "DRG-Agent"
    APP_VERSION: str = "0.1.0"
    PYTHON_VERSION: str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LLM (DeepSeek - OpenAI 兼容接口)
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    # None 表示不限制单次 LLM 请求时长。长任务由用户主动取消，而非固定超时中断。
    LLM_TIMEOUT: float | None = None
    LLM_MAX_RETRIES: int = 3

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://drgagent:drgagent_dev@localhost:5432/drg_agent"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    TASKS_EAGER: bool = False

    # Storage —— 所有本地产物统一收纳到仓库根目录 ./documents 下并按内容分类
    DOCUMENT_STORAGE_PATH: str = "./documents"
    RULE_DATA_PATH: str = "./server/data/rules"

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def repo_root(self) -> Path:
        return _REPO_ROOT

    @property
    def document_storage_dir(self) -> Path:
        """本地产物的绝对存储根目录 (默认仓库根 ./documents)。"""
        path = Path(self.DOCUMENT_STORAGE_PATH)
        return path if path.is_absolute() else (_REPO_ROOT / path).resolve()

    @property
    def document_generated_dir(self) -> Path:
        """对话生成的工程文档存储目录 (documents/generated)。"""
        return self.document_storage_dir / "generated"

    @property
    def document_exports_dir(self) -> Path:
        """测试用例等导出文件存储目录 (documents/exports)。"""
        return self.document_storage_dir / "exports"

    @property
    def rule_data_dir(self) -> Path:
        """DRG 规则数据文件的绝对目录。"""
        path = Path(self.RULE_DATA_PATH)
        return path if path.is_absolute() else (_REPO_ROOT / path).resolve()


settings = Settings()
