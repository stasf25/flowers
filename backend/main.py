"""
Главный модуль FastAPI приложения
Мониторинг конкурентов - MVP ассистент
"""
import base64
import time
import logging
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from backend.config import settings
from backend.models.schemas import (
    TextAnalysisRequest,
    TextAnalysisResponse,
    ImageAnalysisResponse,
    ReviewsAnalysisRequest,
    ReviewsAnalysisResponse,
    CompareRequest,
    CompareResponse,
    ComparisonRow,
    CompetitorCreate,
    CompetitorProfile,
    CompetitorUpdate,
    CompetitorsResponse,
    ParseDemoRequest,
    ParseDemoResponse,
    ParsedContent,
    HistoryResponse
)
from backend.services.openai_service import openai_service
from backend.services.parser_service import parser_service
from backend.services.history_service import history_service
from backend.services.competitors_service import competitors_service

# Логгер для API
logger = logging.getLogger("competitor_monitor.api")

# Инициализация приложения
logger.info("=" * 60)
logger.info("🚀 ЗАПУСК ПРИЛОЖЕНИЯ: Мониторинг конкурентов")
logger.info("=" * 60)

app = FastAPI(
    title="Мониторинг конкурентов",
    description="MVP ассистент для анализа конкурентов с поддержкой текста и изображений",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware добавлен ✓")


# === Middleware для логирования запросов ===

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех HTTP запросов"""
    start_time = time.time()
    
    # Логируем входящий запрос
    logger.info(f"➡️  {request.method} {request.url.path}")
    if request.query_params:
        logger.debug(f"    Query params: {dict(request.query_params)}")
    
    # Выполняем запрос
    response = await call_next(request)
    
    # Логируем ответ
    elapsed = time.time() - start_time
    status_emoji = "✅" if response.status_code < 400 else "❌"
    logger.info(f"{status_emoji} {request.method} {request.url.path} -> {response.status_code} ({elapsed:.3f}s)")
    
    return response


# === События жизненного цикла ===

@app.on_event("startup")
async def startup_event():
    """Событие при запуске сервера"""
    logger.info("=" * 60)
    logger.info("🟢 СЕРВЕР ЗАПУЩЕН")
    logger.info(f"  Адрес: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"  Документация: http://localhost:{settings.api_port}/docs")
    logger.info(f"  Модель текста: {settings.openai_model}")
    logger.info(f"  Модель vision: {settings.openai_vision_model}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Закрытие ресурсов при остановке сервера"""
    logger.info("=" * 60)
    logger.info("🔴 ОСТАНОВКА СЕРВЕРА")
    logger.info("  Закрытие Parser сервиса...")
    await parser_service.close()
    logger.info("  ✓ Все ресурсы освобождены")
    logger.info("=" * 60)


# === Эндпоинты ===

@app.get("/")
async def root():
    """Главная страница - отдаём фронтенд"""
    logger.debug("Запрос главной страницы")
    return FileResponse(os.path.join(settings.project_root, "frontend", "index.html"))


@app.post("/analyze_text", response_model=TextAnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    """
    Анализ текста конкурента
    """
    logger.info("=" * 50)
    logger.info("📝 API: АНАЛИЗ ТЕКСТА")
    logger.info(f"  Длина текста: {len(request.text)} символов")
    logger.info(f"  Превью: {request.text[:80]}...")
    
    try:
        start_time = time.time()
        
        analysis = await openai_service.analyze_text(request.text)
        
        elapsed = time.time() - start_time
        logger.info(f"  ✓ Анализ завершён за {elapsed:.2f} сек")
        
        # Сохраняем в историю
        logger.info("  💾 Сохранение в историю...")
        history_service.add_entry(
            request_type="text",
            request_summary=(f"[{request.shop}] " if request.shop else "") + (request.text[:100] + "..." if len(request.text) > 100 else request.text),
            response_summary=analysis.summary
        )
        # Привязка к конкуренту (вложенный latest)
        shop_id = competitors_service.resolve_shop(request.shop)
        if shop_id:
            competitors_service.save_analysis(shop_id, "text", analysis.model_dump(), {"source": "text"})
        
        logger.info("  ✅ УСПЕХ: Анализ текста завершён")
        logger.info("=" * 50)
        
        return TextAnalysisResponse(
            success=True,
            analysis=analysis
        )
    except Exception as e:
        logger.error(f"  ❌ ОШИБКА: {e}")
        logger.error("=" * 50)
        return TextAnalysisResponse(
            success=False,
            error=str(e)
        )


@app.post("/analyze_image", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    mode: str = Query("site", description="site: скриншот сайта, bouquet: карточка букета"),
    shop: str = Query("", description="Конкурент (выбор или свое название)"),
):
    """
    Анализ изображения конкурента (mode=site|bouquet)
    """
    if mode not in ("site", "bouquet"):
        raise HTTPException(status_code=400, detail="mode должен быть site или bouquet")
    logger.info("=" * 50)
    logger.info(f"🖼️ API: АНАЛИЗ ИЗОБРАЖЕНИЯ (mode={mode})")
    logger.info(f"  Имя файла: {file.filename}")
    logger.info(f"  Тип: {file.content_type}")
    
    # Проверяем тип файла
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        logger.warning(f"  ⚠ Неподдерживаемый тип файла: {file.content_type}")
        logger.info("=" * 50)
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed_types)}"
        )
    
    try:
        start_time = time.time()
        
        # Читаем и кодируем изображение
        logger.info("  📥 Чтение файла...")
        content = await file.read()
        file_size_kb = len(content) / 1024
        logger.info(f"  Размер файла: {file_size_kb:.1f} KB")
        
        image_base64 = base64.b64encode(content).decode('utf-8')
        logger.info(f"  Base64 размер: {len(image_base64)} символов")
        
        # Анализируем
        logger.info("  🔍 Отправка на анализ...")
        analysis = await openai_service.analyze_image(
            image_base64=image_base64,
            mime_type=file.content_type,
            mode=mode
        )

        elapsed = time.time() - start_time
        logger.info(f"  ✓ Анализ завершён за {elapsed:.2f} сек")

        # Сохраняем в историю
        entity = "bouquet" if mode == "bouquet" else "image"
        logger.info("  💾 Сохранение в историю...")
        history_service.add_entry(
            request_type=entity,
            request_summary=(f"[{shop}] " if shop else "") + f"Изображение ({mode}): {file.filename}",
            response_summary=analysis.description[:200] if analysis.description else "Анализ изображения"
        )
        shop_id = competitors_service.resolve_shop(shop)
        if shop_id:
            competitors_service.save_analysis(shop_id, entity, analysis.model_dump(), {"mode": mode, "filename": file.filename})
        
        logger.info("  ✅ УСПЕХ: Анализ изображения завершён")
        logger.info("=" * 50)
        
        return ImageAnalysisResponse(
            success=True,
            analysis=analysis
        )
    except Exception as e:
        logger.error(f"  ❌ ОШИБКА: {e}")
        logger.error("=" * 50)
        return ImageAnalysisResponse(
            success=False,
            error=str(e)
        )


@app.post("/parse_demo", response_model=ParseDemoResponse)
async def parse_demo(request: ParseDemoRequest):
    """
    Парсинг и анализ сайта конкурента через Chrome
    """
    logger.info("=" * 50)
    logger.info("🌐 API: ПАРСИНГ САЙТА")
    logger.info(f"  URL: {request.url}")
    
    try:
        total_start = time.time()
        
        # Открываем страницу в Chrome и делаем скриншот
        logger.info("  🔍 Запуск парсинга...")
        parse_start = time.time()
        title, h1, first_paragraph, screenshot_bytes, error = await parser_service.parse_url(request.url)
        parse_elapsed = time.time() - parse_start
        logger.info(f"  ✓ Парсинг завершён за {parse_elapsed:.2f} сек")
        
        if error:
            logger.error(f"  ❌ Ошибка парсинга: {error}")
            logger.info("=" * 50)
            return ParseDemoResponse(
                success=False,
                error=error
            )
        
        logger.info(f"  📌 Title: {title[:50] if title else 'N/A'}...")
        logger.info(f"  📌 H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f"  📌 Screenshot: {len(screenshot_bytes) / 1024:.1f} KB" if screenshot_bytes else "  📌 Screenshot: N/A")
        
        # Конвертируем скриншот в base64
        screenshot_base64 = parser_service.screenshot_to_base64(screenshot_bytes) if screenshot_bytes else None
        
        # Анализируем сайт через Vision API (скриншот + контекст)
        logger.info("  🤖 Запуск AI анализа...")
        ai_start = time.time()
        
        if screenshot_base64:
            analysis = await openai_service.analyze_website_screenshot(
                screenshot_base64=screenshot_base64,
                url=request.url,
                title=title,
                h1=h1,
                first_paragraph=first_paragraph
            )
        else:
            logger.warning("  ⚠ Скриншот недоступен, fallback на текстовый анализ")
            analysis = await openai_service.analyze_parsed_content(
                title=title,
                h1=h1,
                paragraph=first_paragraph
            )
        
        ai_elapsed = time.time() - ai_start
        logger.info(f"  ✓ AI анализ завершён за {ai_elapsed:.2f} сек")
        
        parsed_content = ParsedContent(
            url=request.url,
            title=title,
            h1=h1,
            first_paragraph=first_paragraph,
            analysis=analysis
        )
        
        # Сохраняем в историю
        logger.info("  💾 Сохранение в историю...")
        history_service.add_entry(
            request_type="parse",
            request_summary=(f"[{request.shop}] " if request.shop else "") + f"URL: {request.url}",
            response_summary=analysis.summary[:100] if analysis.summary else f"Title: {title or 'N/A'}"
        )
        shop_id = competitors_service.resolve_shop(request.shop, url=request.url)
        if shop_id:
            competitors_service.save_analysis(shop_id, "site", analysis.model_dump(), {"url": request.url})
        
        total_elapsed = time.time() - total_start
        logger.info(f"  ✅ УСПЕХ: Парсинг и анализ завершён за {total_elapsed:.2f} сек")
        logger.info(f"    - Парсинг: {parse_elapsed:.2f} сек")
        logger.info(f"    - AI анализ: {ai_elapsed:.2f} сек")
        logger.info("=" * 50)
        
        return ParseDemoResponse(
            success=True,
            data=parsed_content
        )
    except Exception as e:
        logger.error(f"  ❌ ОШИБКА: {e}")
        logger.error("=" * 50)
        return ParseDemoResponse(
            success=False,
            error=str(e)
        )


@app.get("/history", response_model=HistoryResponse)
async def get_history():
    """
    Получить историю последних 10 запросов
    """
    logger.info("📋 API: Получение истории")
    items = history_service.get_history()
    logger.info(f"  Записей: {len(items)}")
    return HistoryResponse(
        items=items,
        total=len(items)
    )


@app.delete("/history")
async def clear_history():
    """
    Очистить историю запросов
    """
    logger.info("🗑️ API: Очистка истории")
    history_service.clear_history()
    logger.info("  ✓ История очищена")
    return {"success": True, "message": "История очищена"}


@app.get("/competitors", response_model=CompetitorsResponse)
async def get_competitors():
    """Список конкурентов (профили из data/competitors.json)"""
    items = competitors_service.list_profiles()
    return CompetitorsResponse(items=items, total=len(items))


@app.post("/competitors", response_model=CompetitorProfile, status_code=201)
async def add_competitor(request: CompetitorCreate):
    """Добавить конкурента вручную (id опционален)"""
    try:
        return competitors_service.add_profile(
            name=request.name, shop_id=request.id, url=request.url,
            price_min=request.price_min, price_max=request.price_max,
        )
    except KeyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/competitors/{shop_id}", response_model=CompetitorProfile)
async def update_competitor(shop_id: str, request: CompetitorUpdate):
    """Редактировать конкурента (id неизменен)"""
    try:
        return competitors_service.update_profile(
            shop_id, name=request.name, url=request.url,
            price_min=request.price_min, price_max=request.price_max,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/competitors/{shop_id}")
async def delete_competitor(shop_id: str):
    """Удалить конкурента вместе с анализами"""
    try:
        competitors_service.delete_profile(shop_id)
        return {"success": True, "message": f"Конкурент {shop_id} удален"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/competitors/full")
async def get_competitors_full():
    """Полное содержимое competitors.json (профили + анализы) для вкладки Конкуренты"""
    return competitors_service.get_for_compare([s.id for s in competitors_service.list_profiles()])


@app.post("/analyze_reviews", response_model=ReviewsAnalysisResponse)
async def analyze_reviews(request: ReviewsAnalysisRequest):
    """Анализ отзывов о конкуренте (вставленный текст)"""
    logger.info("=" * 50)
    logger.info("⭐ API: АНАЛИЗ ОТЗЫВОВ")
    try:
        analysis = await openai_service.analyze_reviews(request.text, shop=request.shop, source=request.source)
        history_service.add_entry(
            request_type="reviews",
            request_summary=(f"[{request.shop}] " if request.shop else "") + f"Отзывы ({request.source or 'н/д'}): {request.text[:80]}...",
            response_summary=analysis.summary[:200] if analysis.summary else f"sentiment={analysis.sentiment}",
        )
        shop_id = competitors_service.resolve_shop(request.shop)
        if shop_id:
            competitors_service.save_analysis(shop_id, "reviews", analysis.model_dump(), {"source": request.source})
        logger.info("  ✅ УСПЕХ: Анализ отзывов завершён")
        logger.info("=" * 50)
        return ReviewsAnalysisResponse(success=True, analysis=analysis)
    except Exception as e:
        logger.error(f"  ❌ ОШИБКА: {e}")
        logger.error("=" * 50)
        return ReviewsAnalysisResponse(success=False, error=str(e))


@app.post("/compare", response_model=CompareResponse)
async def compare(request: CompareRequest):
    """Сопоставление конкурентов: матрица + overall_summary"""
    logger.info("=" * 50)
    logger.info(f"📊 API: СРАВНЕНИЕ {request.shop_ids}")
    try:
        shops = competitors_service.get_for_compare(request.shop_ids)
        if len(shops) < 2:
            return CompareResponse(success=False, error="Нужно минимум 2 конкурента с данными. Сначала привяжите анализы к конкурентам.")
        payload = []
        for sid, s in shops.items():
            a = s.get("analyses", {})
            # Берем свежие скоринги: приоритет site -> text; букеты усредняем
            base = a.get("site") or a.get("text") or {}
            scores = dict((base.get("result") or {}))
            bouquets = a.get("bouquets", [])
            if bouquets:
                for c in ("bouquet_design_score", "color_harmony_score", "instagrammability_score"):
                    vals = [b["result"].get(c, 0) for b in bouquets if b.get("result", {}).get(c)]
                    if vals:
                        scores[c] = round(sum(vals) / len(vals))
            payload.append({
                "id": sid, "name": s.get("name", sid),
                "scores": scores,
                "price_min": s.get("price_min"), "price_max": s.get("price_max"),
                "summary": (base.get("result") or {}).get("summary", ""),
            })
        result = await openai_service.compare_shops(payload)
        rows = []
        # Направление критериев: цена — чем меньше, тем лучше; скоры — наоборот.
        # LLM winner для цен ставит по максимуму — пересчитываем детерминированно.
        lower_is_better = {"price_min", "price_max"}
        for r in result.get("matrix", []):
            values = r.get("values", {}) or {}
            winner = r.get("winner")
            crit = str(r.get("criterion", ""))
            if crit in lower_is_better:
                nums = {k: v for k, v in values.items() if isinstance(v, (int, float))}
                winner = min(nums, key=lambda k: nums[k]) if nums else None
            rows.append(ComparisonRow(criterion=crit, values=values, winner=winner))
        history_service.add_entry(
            request_type="compare",
            request_summary=f"Сравнение: {', '.join(request.shop_ids)}",
            response_summary=result.get("overall_summary", "")[:200],
        )
        logger.info("  ✅ УСПЕХ: Сравнение готово")
        logger.info("=" * 50)
        return CompareResponse(success=True, competitors=request.shop_ids, matrix=rows, overall_summary=result.get("overall_summary", ""))
    except Exception as e:
        logger.error(f"  ❌ ОШИБКА: {e}")
        logger.error("=" * 50)
        return CompareResponse(success=False, error=str(e))


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    logger.debug("❤️ Health check")
    return {
        "status": "healthy",
        "service": "Competitor Monitor",
        "version": "1.0.0"
    }


# Статические файлы для фронтенда (абсолютный путь от корня проекта, не зависит от cwd)
app.mount("/static", StaticFiles(directory=os.path.join(settings.project_root, "frontend")), name="static")
logger.info(f"Статические файлы подключены: /static -> {os.path.join(settings.project_root, 'frontend/')}")


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
