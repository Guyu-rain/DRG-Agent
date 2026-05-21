"""Loguru 日志配置。"""

import sys

from loguru import logger

from app.core.config import settings

_LOG_DIR = settings.repo_root / "logs"
_configured = False


def setup_logging() -> None:
    """初始化 Loguru：控制台 + 文件输出。幂等。"""
    global _configured
    if _configured:
        return

    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> - <level>{message}</level>"
        ),
    )

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(
            _LOG_DIR / "drg-agent_{time:YYYY-MM-DD}.log",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
        )
    except OSError:  # 文件系统不可写时仅保留控制台输出
        pass

    _configured = True


__all__ = ["logger", "setup_logging"]
