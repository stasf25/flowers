"""
Сервис для парсинга веб-страниц.
Режимы (в порядке приоритета):
1. Browserless REST (BROWSERLESS_URL, напр. http://browser:3000) — для docker-compose
2. Selenium Remote (SELENIUM_REMOTE_URL) — для selenium/standalone-chrome
3. Локальный Chrome через Selenium + ChromeDriverManager — для dev без docker
"""
import base64
import asyncio
import time
import logging
import os
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import httpx
from bs4 import BeautifulSoup

from backend.config import settings

# Логгер для сервиса
logger = logging.getLogger("competitor_monitor.parser")


class ParserService:
    """Парсинг веб-страниц через Chrome с созданием скриншота"""
    
    def __init__(self):
        logger.info("=" * 50)
        logger.info("Инициализация Parser сервиса")
        logger.info(f"  Timeout: {settings.parser_timeout} сек")
        logger.info(f"  User-Agent: {settings.parser_user_agent[:50]}...")
        
        self.timeout = settings.parser_timeout
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info("Parser сервис инициализирован ✓")
        logger.info("=" * 50)
    
    def _create_driver(self):
        """Создать новый экземпляр Chrome драйвера (только для локального/Selenium-remote режимов)"""
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        logger.info("  🌐 Создание Chrome драйвера...")
        start_time = time.time()
        
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={settings.parser_user_agent}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        logger.debug("  Опции Chrome настроены")

        # Удаленный браузер (docker-compose: browserless/chromium или selenium/standalone-chrome)
        remote_url = getattr(settings, "selenium_remote_url", "") or ""
        if remote_url:
            logger.info(f"  🔗 Remote WebDriver: {remote_url}")
            driver = webdriver.Remote(command_executor=remote_url, options=options)

            elapsed = time.time() - start_time
            logger.info(f"  ✓ Remote драйвер создан за {elapsed:.2f} сек")

            return driver

        logger.info("  📥 Загрузка ChromeDriver...")
        
        # Автоматическая установка ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        elapsed = time.time() - start_time
        logger.info(f"  ✓ Chrome драйвер создан за {elapsed:.2f} сек")
        
        return driver
    
    def _browserless_base(self) -> str:
        """Базовый URL Browserless REST (без токена). Пусто — REST недоступен."""
        base = (getattr(settings, "browserless_url", "") or "").rstrip("/")
        # Обратная совместимость: если в SELENIUM_REMOTE_URL по ошибке лежит browserless-URL
        if not base:
            remote = (getattr(settings, "selenium_remote_url", "") or "")
            if ":3000" in remote:
                base = remote.split("/webdriver")[0].rstrip("/")
        return base

    _ESC_DISMISS_JS = """export default async ({page, context}) => {
  await page.goto(context.url, {waitUntil: 'domcontentloaded', timeout: 25000});
  await new Promise(r => setTimeout(r, 2000));
  // Закрываем поп-апы/оверлеи: на всех наших сайтах это безопасно (ESC ни к чему не привязан)
  try { await page.keyboard.press('Escape'); } catch (e) {}
  await new Promise(r => setTimeout(r, 500));
  const html = await page.content();
  const title = await page.title();
  const screenshot = await page.screenshot({encoding: 'base64', fullPage: false, type: 'png'});
  return {data: {html, title, screenshot}, type: 'application/json'};
};"""

    def _parse_via_browserless_rest(
        self, url: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes], Optional[str]]:
        """
        Парсинг через Browserless REST API (без Selenium-протокола).
        Основной путь — POST /function: один заход (goto -> ESC -> html + скриншот).
        Fallback — POST /content + POST /screenshot.
        См. https://docs.browserless.io/enterprise/open-source (раздел REST APIs).
        """
        from backend.config import settings as _s

        base = self._browserless_base()
        token = (getattr(_s, "browserless_token", "") or "").strip()
        params = {"token": token} if token else None
        timeout = httpx.Timeout(self.timeout + 20.0)

        logger.info(f"  🌐 Browserless REST: {base}")

        html = ""
        screenshot_bytes: Optional[bytes] = None

        # --- Путь 1: /function (goto + ESC + html + screenshot за один заход) ---
        try:
            r = httpx.post(
                f"{base}/function",
                json={"code": self._ESC_DISMISS_JS, "context": {"url": url}},
                params=params,
                timeout=httpx.Timeout(self.timeout + 40.0),
            )
            r.raise_for_status()
            payload = r.json().get("data", {}) if "application/json" in r.headers.get("content-type", "") else {}
            html = payload.get("html", "") or ""
            b64 = payload.get("screenshot", "") or ""
            if b64:
                screenshot_bytes = base64.b64decode(b64.split(",")[-1])
            logger.info(f"  ✓ /function: HTML {len(html)} символов"
                        + (f", скриншот {len(screenshot_bytes) / 1024:.1f} KB" if screenshot_bytes else ", без скриншота"))
        except Exception as e:
            logger.warning(f"  ⚠ /function ошибка, fallback на /content+/screenshot: {str(e)[:200]}")
            html, screenshot_bytes = "", None

        # --- Путь 2 (fallback): /content + /screenshot по отдельности ---
        if not html:
            try:
                r = httpx.post(f"{base}/content", json={"url": url}, params=params, timeout=timeout)
                r.raise_for_status()
                ctype = r.headers.get("content-type", "")
                if "application/json" in ctype:
                    try:
                        data = r.json()
                        html = data if isinstance(data, str) else (
                            data.get("content") or data.get("html") or data.get("data") or ""
                        )
                    except Exception:
                        html = r.text
                else:
                    html = r.text
                logger.info(f"  ✓ HTML получен ({len(html)} символов)")
            except Exception as e:
                logger.error(f"  ✗ /content ошибка: {str(e)[:200]}")
                return None, None, None, None, f"Browserless /content: {str(e)[:200]}"

        title, h1, first_paragraph = None, None, None
        try:
            soup = BeautifulSoup(html, "lxml")
            if soup.title and soup.title.string:
                title = soup.title.string.strip() or None
            h1_tag = soup.find("h1")
            if h1_tag and h1_tag.get_text(strip=True):
                h1 = h1_tag.get_text(strip=True)
            for p in soup.find_all("p"):
                text = p.get_text(" ", strip=True)
                if len(text) > 50:
                    first_paragraph = text[:500]
                    break
            logger.info(f"  📌 Title: {title[:60] if title else 'N/A'}...")
        except Exception as e:
            logger.warning(f"  HTML-парсинг: {str(e)[:150]}")

        if screenshot_bytes is None:
            try:
                r = httpx.post(
                    f"{base}/screenshot",
                    json={"url": url, "options": {"fullPage": False, "type": "png"}},
                    params=params,
                    timeout=timeout,
                )
                r.raise_for_status()
                ctype = r.headers.get("content-type", "")
                if "image" in ctype:
                    screenshot_bytes = r.content
                else:
                    try:
                        data = r.json()
                        b64 = data.get("screenshot") or data.get("data") or ""
                        if b64:
                            screenshot_bytes = base64.b64decode(b64.split(",")[-1])
                    except Exception:
                        pass
                if screenshot_bytes:
                    logger.info(f"  ✓ Скриншот ({len(screenshot_bytes) / 1024:.1f} KB)")
                else:
                    logger.warning("  ⚠ Скриншот пустой, продолжаем без него")
            except Exception as e:
                logger.warning(f"  ⚠ /screenshot ошибка (продолжаем без скриншота): {str(e)[:200]}")

        return title, h1, first_paragraph, screenshot_bytes, None

    def _parse_sync(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes], Optional[str]]:
        """
        Синхронный парсинг URL (выполняется в отдельном потоке)
        """
        logger.info("=" * 50)
        logger.info(f"🔍 ПАРСИНГ САЙТА: {url}")

        # Приоритет 1: Browserless REST (docker-compose). Selenium-протокол
        # ghcr.io/browserless/chromium НЕ поддерживает (/webdriver -> 404),
        # поэтому идем через /content + /screenshot.
        if self._browserless_base():
            return self._parse_via_browserless_rest(url)

        # Приоритет 2-3: Selenium Remote / локальный Chrome
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException, WebDriverException

        driver = None
        total_start = time.time()
        
        try:
            driver = self._create_driver()
            driver.set_page_load_timeout(self.timeout)
            
            # Переходим на страницу
            logger.info(f"  📄 Загрузка страницы...")
            page_start = time.time()
            driver.get(url)
            page_elapsed = time.time() - page_start
            logger.info(f"  ✓ Страница загружена за {page_elapsed:.2f} сек")
            
            # Ждём загрузки body
            logger.info("  ⏳ Ожидание body элемента...")
            WebDriverWait(driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logger.info("  ✓ Body элемент найден")
            
            # Даём странице время на загрузку динамического контента
            logger.info("  ⏳ Ожидание динамического контента (2 сек)...")
            time.sleep(2)
            
            # Извлекаем title
            title = driver.title
            logger.info(f"  📌 Title: {title[:60] if title else 'N/A'}...")
            
            # Извлекаем h1
            h1 = None
            try:
                h1_element = driver.find_element(By.TAG_NAME, 'h1')
                h1 = h1_element.text.strip() if h1_element.text else None
                logger.info(f"  📌 H1: {h1[:60] if h1 else 'N/A'}...")
            except Exception as e:
                logger.debug(f"  H1 не найден: {e}")
            
            # Извлекаем первый абзац
            first_paragraph = None
            try:
                paragraphs = driver.find_elements(By.TAG_NAME, 'p')
                logger.debug(f"  Найдено абзацев: {len(paragraphs)}")
                for i, p in enumerate(paragraphs):
                    text = p.text.strip() if p.text else ""
                    if len(text) > 50:
                        first_paragraph = text[:500]
                        logger.info(f"  📌 Первый абзац (p[{i}]): {first_paragraph[:60]}...")
                        break
            except Exception as e:
                logger.debug(f"  Абзацы не найдены: {e}")
            
            # Делаем скриншот
            logger.info("  📸 Создание скриншота...")
            screenshot_start = time.time()
            screenshot_bytes = driver.get_screenshot_as_png()
            screenshot_elapsed = time.time() - screenshot_start
            screenshot_size_kb = len(screenshot_bytes) / 1024
            logger.info(f"  ✓ Скриншот создан за {screenshot_elapsed:.2f} сек ({screenshot_size_kb:.1f} KB)")
            
            total_elapsed = time.time() - total_start
            logger.info(f"  ✅ ПАРСИНГ ЗАВЕРШЁН за {total_elapsed:.2f} сек")
            logger.info("=" * 50)
            
            return title, h1, first_paragraph, screenshot_bytes, None
            
        except TimeoutException:
            total_elapsed = time.time() - total_start
            logger.error(f"  ✗ TIMEOUT за {total_elapsed:.2f} сек")
            logger.error("=" * 50)
            return None, None, None, None, "Превышено время ожидания загрузки страницы"
            
        except WebDriverException as e:
            total_elapsed = time.time() - total_start
            error_msg = str(e)
            logger.error(f"  ✗ WebDriver ошибка за {total_elapsed:.2f} сек")
            logger.error(f"  Детали: {error_msg[:200]}")
            logger.error("=" * 50)
            
            if 'net::ERR_NAME_NOT_RESOLVED' in error_msg:
                return None, None, None, None, "Не удалось найти сайт по указанному адресу"
            elif 'net::ERR_CONNECTION_REFUSED' in error_msg:
                return None, None, None, None, "Соединение отклонено сервером"
            elif 'net::ERR_CONNECTION_TIMED_OUT' in error_msg:
                return None, None, None, None, "Превышено время ожидания соединения"
            else:
                return None, None, None, None, f"Ошибка браузера: {error_msg[:200]}"
                
        except Exception as e:
            total_elapsed = time.time() - total_start
            logger.error(f"  ✗ Неизвестная ошибка за {total_elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            return None, None, None, None, f"Ошибка при загрузке страницы: {str(e)[:200]}"
            
        finally:
            if driver:
                try:
                    logger.debug("  Закрытие драйвера...")
                    driver.quit()
                    logger.debug("  ✓ Драйвер закрыт")
                except Exception as e:
                    logger.warning(f"  Ошибка при закрытии драйвера: {e}")
    
    async def parse_url(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes], Optional[str]]:
        """
        Асинхронный парсинг URL через Chrome
        """
        # Добавляем протокол если его нет
        original_url = url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            logger.info(f"  URL дополнен протоколом: {original_url} -> {url}")
        
        logger.info(f"🚀 Запуск асинхронного парсинга: {url}")
        
        # Запускаем синхронный парсинг в отдельном потоке
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            self._parse_sync,
            url
        )
        
        return result
    
    def screenshot_to_base64(self, screenshot_bytes: bytes) -> str:
        """Конвертировать скриншот в base64"""
        base64_str = base64.b64encode(screenshot_bytes).decode('utf-8')
        logger.debug(f"Скриншот конвертирован в base64: {len(base64_str)} символов")
        return base64_str
    
    async def close(self):
        """Закрыть executor"""
        logger.info("Закрытие Parser сервиса...")
        self._executor.shutdown(wait=False)
        logger.info("Parser сервис закрыт ✓")


# Глобальный экземпляр
logger.info("Создание глобального экземпляра Parser сервиса...")
parser_service = ParserService()
