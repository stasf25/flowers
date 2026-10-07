"""
Конфигурация приложения
"""
import os
import logging
import sys
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv, find_dotenv

_PROJECT_ROOT = Path(os.path.dirname(find_dotenv(".env", raise_error_if_not_found=True))).resolve()
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

# === Настройка логирования ===
def setup_logging():
    """Настройка логирования для всего приложения"""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Основной логгер
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Уменьшаем логи от сторонних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("WDM").setLevel(logging.WARNING)
    
    return logging.getLogger("competitor_monitor")

# Инициализация логгера
logger = setup_logging()


class Settings(BaseSettings):
    """Настройки приложения"""

    # Корневая директория проекта (папка, где лежат backend/, frontend/, .env)
    # Поиск вверх от файла-вызывателя, падает быстро при отсутствии .env.
    project_root: str = str(_PROJECT_ROOT)
     
    # ProxyAPI (OpenAI-совместимый)
    proxy_api_key: str = os.getenv("PROXYAPI_KEY", os.getenv("OPENAI_API_KEY", ""))
    proxy_api_base_url: str = os.getenv("PROXYAPI_BASE_URL", "")
    openai_model: str = os.getenv("PROXYAPI_CHAT_MODEL", "gpt-4o-mini")
    openai_vision_model: str = os.getenv("PROXYAPI_VL_MODEL", "gpt-4o-mini")
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Файл с результатами анализов
    store_file: str = str(_PROJECT_ROOT / "data" / "competitors.json")
    
    # История
    history_file: str = str(_PROJECT_ROOT / "data" / "history.json")
    max_history_items: int = 10
    
    # Парсер
    parser_timeout: int = 10
    parser_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    selenium_remote_url: str = os.getenv("SELENIUM_REMOTE_URL", "")
    # Browserless REST (ghcr.io/browserless/chromium): базовый URL без /webdriver,
    # напр. http://browser:3000. Selenium-протокол v2-образ НЕ поддерживает.
    browserless_url: str = os.getenv("BROWSERLESS_URL", "")
    browserless_token: str = os.getenv("BROWSERLESS_TOKEN", "")
    
    class Config:
        env_file = str(_PROJECT_ROOT / ".env")
        extra = "ignore"


settings = Settings()

