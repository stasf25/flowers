"""
Сервис для работы с ProxyAPI (OpenAI-совместимый API)
https://proxyapi.ru/docs/openai-text-generation
"""
import base64
import json
import re
import time
import logging
from typing import Optional

from openai import OpenAI

from backend.config import settings
from backend.models.schemas import CompetitorAnalysis, ImageAnalysis

# Логгер для сервиса
logger = logging.getLogger("competitor_monitor.openai")


class OpenAIService:
    """Сервис для анализа через ProxyAPI"""
    
    def __init__(self):
        logger.info("=" * 50)
        logger.info("Инициализация OpenAI сервиса")
        logger.info(f"  Base URL: {settings.proxy_api_base_url}")
        logger.info(f"  Модель текста: {settings.openai_model}")
        logger.info(f"  Модель vision: {settings.openai_vision_model}")
        logger.info(f"  API ключ: {'*' * 10}...{settings.proxy_api_key[-4:] if settings.proxy_api_key else 'НЕ ЗАДАН'}")
        
        # ProxyAPI - OpenAI-совместимый API для России
        self.client = OpenAI(
            api_key=settings.proxy_api_key,
            base_url=settings.proxy_api_base_url
        )
        self.model = settings.openai_model
        self.vision_model = settings.openai_vision_model
        
        logger.info("OpenAI сервис инициализирован успешно ✓")
        logger.info("=" * 50)
    
    def _parse_json_response(self, content: str) -> dict:
        """Извлечь JSON из ответа модели"""
        logger.debug(f"Парсинг JSON ответа, длина: {len(content)} символов")
        
        # Пробуем найти JSON в markdown блоке
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)
            logger.debug("JSON найден в markdown блоке")
        
        # Пробуем найти JSON объект
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)
            logger.debug("JSON объект извлечён")
        
        try:
            result = json.loads(content)
            logger.debug(f"JSON успешно распарсен, ключей: {len(result)}")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"Ошибка парсинга JSON: {e}")
            logger.debug(f"Проблемный контент: {content[:200]}...")
            return {}
    
    async def analyze_text(self, text: str) -> CompetitorAnalysis:
        """Анализ текста конкурента"""
        logger.info("=" * 50)
        logger.info("📝 АНАЛИЗ ТЕКСТА КОНКУРЕНТА")
        logger.info(f"  Длина текста: {len(text)} символов")
        logger.info(f"  Превью: {text[:100]}...")
        logger.info(f"  Модель: {self.model}")
        
        system_prompt = """Ты — опытный флорист-маркетолог с 10-летним стажем в российском цветочном ритейле. Проанализируй текст конкурента (онлайн-магазин цветов) и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
    "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
    "unique_offers": ["уникальное предложение 1", "уникальное предложение 2", ...],
    "recommendations": ["рекомендация 1", "рекомендация 2", ...],
    "summary": "Краткое резюме анализа",
    "design_score": 7,
    "bouquet_design_score": 7,
    "animation_potential": 5,
    "freshness_guarantee_score": 7,
    "delivery_clarity_score": 7,
    "promo_offer_strength": 6,
    "price_segment": "средний"
}

Оценивай с точки зрения цветочной ниши: свежесть и подача продукта, сезонность, логистика и гарантии (критично для живых цветов), эмоциональный маркетинг (цветы = эмоции), цена/воспринимаемая ценность.
Важно:
- Каждый массив должен содержать 3-5 пунктов
- Все скоры — целые 0-10 (0, если по тексту оценить нельзя)
- price_segment — одно из: бюджет / средний / премиум / люкс
- Пиши на русском языке
- Длина всего ответа — не более 5000 токенов
- Будь конкретен и практичен в рекомендациях"""

        start_time = time.time()
        logger.info("  Отправка запроса к API...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Проанализируй текст конкурента:\n\n{text}"}
                ],
                temperature=0.7,
                max_tokens=6000
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.choices[0].message.content
            logger.info(f"  Длина ответа: {len(content)} символов")
            logger.debug(f"  Использовано токенов: {response.usage.total_tokens if response.usage else 'N/A'}")
            
            data = self._parse_json_response(content)
            
            result = CompetitorAnalysis(
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                unique_offers=data.get("unique_offers", []),
                recommendations=data.get("recommendations", []),
                summary=data.get("summary", ""),
                design_score=int(data.get("design_score", 0) or 0),
                bouquet_design_score=int(data.get("bouquet_design_score", 0) or 0),
                animation_potential=int(data.get("animation_potential", 0) or 0),
                freshness_guarantee_score=int(data.get("freshness_guarantee_score", 0) or 0),
                delivery_clarity_score=int(data.get("delivery_clarity_score", 0) or 0),
                promo_offer_strength=int(data.get("promo_offer_strength", 0) or 0),
                price_segment=str(data.get("price_segment", "") or ""),
            )

            logger.info(f"  Результат: {len(result.strengths)} сильных, {len(result.weaknesses)} слабых сторон")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise
    
    async def analyze_image(self, image_base64: str, mime_type: str = "image/jpeg", mode: str = "site") -> ImageAnalysis:
        """Анализ изображения. mode=site (скриншот сайта) или bouquet (карточка букета)."""
        logger.info("=" * 50)
        logger.info(f"🖼️ АНАЛИЗ ИЗОБРАЖЕНИЯ (mode={mode})")
        logger.info(f"  Размер base64: {len(image_base64)} символов")
        logger.info(f"  MIME тип: {mime_type}")
        logger.info(f"  Модель: {self.vision_model}")

        if mode == "bouquet":
            system_prompt = """Ты — опытный флорист-маркетолог с 10-летним стажем в российском цветочном ритейле. Проанализируй карточку букета конкурента (фото товара) и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
    "description": "Детальное описание букета: состав, упаковка, фон",
    "marketing_insights": ["инсайт 1", "инсайт 2", ...],
    "visual_style_score": 7,
    "visual_style_analysis": "Анализ подачи товара",
    "recommendations": ["рекомендация 1", "рекомендация 2", ...],
    "design_score": 7,
    "instagrammability_score": 7,
    "bouquet_composition_analysis": "Разбор композиции: форма, цветовые сочетания, флористические приемы",
    "dominant_flowers": ["розы", "эустома", ...],
    "color_harmony_score": 7,
    "styling_elements": ["крафт-упаковка", "лента", "студийный фон", ...],
    "occasion_fit": ["день рождения", "свадьба", ...]
}

Важно:
- Все скоры — целые 0-10
- Каждый массив должен содержать 3-5 пунктов (dominant_flowers — по факту)
- Пиши на русском языке
- Оценивай: реалистичность фото (живое vs сток/рендер), сложность композиции, цветовую гармонию, упаковку, фон
- Длина всего ответа — не более 5000 токенов"""
            user_text = "Проанализируй эту карточку букета конкурента как флорист-маркетолог:"
        else:
            system_prompt = """Ты — опытный флорист-маркетолог с 10-летним стажем в российском цветочном ритейле. Проанализируй скриншот сайта конкурента (онлайн-магазин цветов) и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
    "description": "Детальное описание того, что изображено",
    "marketing_insights": ["инсайт 1", "инсайт 2", ...],
    "visual_style_score": 7,
    "visual_style_analysis": "Анализ визуального стиля конкурента",
    "recommendations": ["рекомендация 1", "рекомендация 2", ...],
    "design_score": 7,
    "instagrammability_score": 6
}

Важно:
- Все скоры — целые 0-10
- Каждый массив должен содержать 3-5 пунктов
- Пиши на русском языке
- Оценивай: цветовую палитру, типографику, композицию, UX/UI элементы, удобство каталога и заказа
- Длина всего ответа — не более 5000 токенов"""
            user_text = "Проанализируй этот скриншот сайта цветочного конкурента с точки зрения маркетинга и дизайна:"

        start_time = time.time()
        logger.info("  Отправка запроса к Vision API...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.7,
                max_tokens=6000
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.choices[0].message.content
            logger.info(f"  Длина ответа: {len(content)} символов")
            
            data = self._parse_json_response(content)
            
            result = ImageAnalysis(
                description=data.get("description", ""),
                marketing_insights=data.get("marketing_insights", []),
                visual_style_score=int(data.get("visual_style_score", 5) or 0),
                visual_style_analysis=data.get("visual_style_analysis", ""),
                recommendations=data.get("recommendations", []),
                design_score=int(data.get("design_score", 0) or 0),
                instagrammability_score=int(data.get("instagrammability_score", 0) or 0),
                bouquet_composition_analysis=data.get("bouquet_composition_analysis", ""),
                dominant_flowers=data.get("dominant_flowers", []),
                color_harmony_score=int(data.get("color_harmony_score", 0) or 0),
                styling_elements=data.get("styling_elements", []),
                occasion_fit=data.get("occasion_fit", []),
            )
            
            logger.info(f"  Результат: оценка стиля {result.visual_style_score}/10")
            logger.info(f"  Инсайтов: {len(result.marketing_insights)}, рекомендаций: {len(result.recommendations)}")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка Vision API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise
    
    async def analyze_parsed_content(
        self, 
        title: Optional[str], 
        h1: Optional[str], 
        paragraph: Optional[str]
    ) -> CompetitorAnalysis:
        """Анализ распарсенного контента сайта"""
        logger.info("📄 Анализ распарсенного контента")
        logger.info(f"  Title: {title[:50] if title else 'N/A'}...")
        logger.info(f"  H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f"  Абзац: {paragraph[:50] if paragraph else 'N/A'}...")
        
        content_parts = []
        if title:
            content_parts.append(f"Заголовок страницы (title): {title}")
        if h1:
            content_parts.append(f"Главный заголовок (H1): {h1}")
        if paragraph:
            content_parts.append(f"Первый абзац: {paragraph}")
        
        combined_text = "\n\n".join(content_parts)
        
        if not combined_text.strip():
            logger.warning("  ⚠ Контент пустой, возвращаем пустой анализ")
            return CompetitorAnalysis(
                summary="Не удалось извлечь контент для анализа"
            )
        
        return await self.analyze_text(combined_text)
    
    async def analyze_website_screenshot(
        self,
        screenshot_base64: str,
        url: str,
        title: Optional[str] = None,
        h1: Optional[str] = None,
        first_paragraph: Optional[str] = None
    ) -> CompetitorAnalysis:
        """Комплексный анализ сайта конкурента по скриншоту"""
        logger.info("=" * 50)
        logger.info("🌐 КОМПЛЕКСНЫЙ АНАЛИЗ САЙТА")
        logger.info(f"  URL: {url}")
        logger.info(f"  Title: {title[:50] if title else 'N/A'}...")
        logger.info(f"  H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f"  Размер скриншота: {len(screenshot_base64)} символов base64")
        logger.info(f"  Модель: {self.vision_model}")
        
        # Формируем контекст из извлечённых данных
        context_parts = [f"URL сайта: {url}"]
        if title:
            context_parts.append(f"Title страницы: {title}")
        if h1:
            context_parts.append(f"Главный заголовок (H1): {h1}")
        if first_paragraph:
            context_parts.append(f"Текст на странице: {first_paragraph[:300]}")
        
        context = "\n".join(context_parts)
        logger.debug(f"  Контекст:\n{context}")
        
        system_prompt = """Ты — опытный флорист-маркетолог с 10-летним стажем в российском цветочном ритейле. Проанализируй скриншот сайта цветочного конкурента и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
    "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
    "unique_offers": ["уникальное предложение/фича 1", "уникальное предложение/фича 2", ...],
    "recommendations": ["рекомендация 1", "рекомендация 2", ...],
    "summary": "Комплексное резюме анализа сайта конкурента",
    "design_score": 7,
    "bouquet_design_score": 7,
    "animation_potential": 5,
    "freshness_guarantee_score": 7,
    "delivery_clarity_score": 7,
    "promo_offer_strength": 6,
    "price_segment": "средний"
}

При анализе обращай внимание на:
- Дизайн и визуальный стиль (цвета, шрифты, композиция)
- UX/UI: навигация, расположение элементов, CTA кнопки, удобство каталога и заказа
- Контент: заголовки, тексты, призывы к действию
- Уникальные торговые предложения (УТП)
- Целевая аудитория (на кого ориентирован сайт)
- Свежесть подачи, гарантии, доставка (критично для живых цветов)

Важно:
- Каждый массив должен содержать 4-6 конкретных пунктов
- Все скоры — целые 0-10; price_segment — бюджет / средний / премиум / люкс
- Пиши на русском языке
- Длина всего ответа — не более 5000 токенов
- Будь конкретен и практичен
- Давай actionable рекомендации"""

        start_time = time.time()
        logger.info("  Отправка скриншота в Vision API...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Проведи комплексный конкурентный анализ этого сайта:\n\n{context}"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.7,
                max_tokens=6000
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.choices[0].message.content
            logger.info(f"  Длина ответа: {len(content)} символов")
            
            data = self._parse_json_response(content)
            
            result = CompetitorAnalysis(
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                unique_offers=data.get("unique_offers", []),
                recommendations=data.get("recommendations", []),
                summary=data.get("summary", ""),
                design_score=int(data.get("design_score", 0) or 0),
                bouquet_design_score=int(data.get("bouquet_design_score", 0) or 0),
                animation_potential=int(data.get("animation_potential", 0) or 0),
                freshness_guarantee_score=int(data.get("freshness_guarantee_score", 0) or 0),
                delivery_clarity_score=int(data.get("delivery_clarity_score", 0) or 0),
                promo_offer_strength=int(data.get("promo_offer_strength", 0) or 0),
                price_segment=str(data.get("price_segment", "") or ""),
            )

            logger.info(f"  Результат:")
            logger.info(f"    - Сильных сторон: {len(result.strengths)}")
            logger.info(f"    - Слабых сторон: {len(result.weaknesses)}")
            logger.info(f"    - УТП: {len(result.unique_offers)}")
            logger.info(f"    - Рекомендаций: {len(result.recommendations)}")
            logger.info(f"  Резюме: {result.summary[:100]}...")
            logger.info("=" * 50)

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка Vision API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise

    async def analyze_reviews(self, text: str, shop: str = "", source: str = "") -> "ReviewsAnalysis":
        """Анализ отзывов о конкуренте (вставленный текст, без скрапинга)"""
        from backend.models.schemas import ReviewsAnalysis

        logger.info("=" * 50)
        logger.info("⭐ АНАЛИЗ ОТЗЫВОВ")
        logger.info(f"  Магазин: {shop or 'н/д'}, источник: {source or 'н/д'}")
        logger.info(f"  Длина текста: {len(text)} символов")

        system_prompt = """Ты — опытный флорист-маркетолог. Проанализируй отзывы клиентов цветочного магазина и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
    "sentiment": 0.3,
    "positive_themes": ["свежие цветы", ...],
    "negative_themes": ["опоздание курьера", ...],
    "delivery_complaints_ratio": 0.2,
    "freshness_complaints_ratio": 0.1,
    "photo_mismatch_mentions": 2,
    "summary": "Резюме по отзывам"
}

Важно:
- sentiment от -1 (все плохо) до 1 (все отлично)
- ratios — доля 0..1 от всех жалоб (0, если жалоб нет)
- photo_mismatch_mentions — целое число упоминаний несоответствия фото
- Длина всего ответа — не более 5000 токенов
- Пиши на русском языке"""

        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Магазин: {shop or 'н/д'}\nИсточник: {source or 'н/д'}\n\nОтзывы:\n\n{text}"}
                ],
                temperature=0.3,
                max_tokens=6000
            )
            elapsed = time.time() - start_time
            content = response.choices[0].message.content
            data = self._parse_json_response(content)
            result = ReviewsAnalysis(
                sentiment=float(data.get("sentiment", 0) or 0),
                positive_themes=data.get("positive_themes", []),
                negative_themes=data.get("negative_themes", []),
                delivery_complaints_ratio=float(data.get("delivery_complaints_ratio", 0) or 0),
                freshness_complaints_ratio=float(data.get("freshness_complaints_ratio", 0) or 0),
                photo_mismatch_mentions=int(data.get("photo_mismatch_mentions", 0) or 0),
                summary=data.get("summary", ""),
            )
            logger.info(f"  ✓ sentiment={result.sentiment} за {elapsed:.2f} сек")
            logger.info("=" * 50)
            return result
        except Exception as e:
            logger.error(f"  ✗ Ошибка анализа отзывов: {e}")
            logger.error("=" * 50)
            raise

    async def compare_shops(self, shops_data: list) -> dict:
        """Сопоставление 2+ конкурентов одним LLM-вызовом: матрица + overall_summary.
        shops_data: [{id, name, scores: {criterion: value}, price_min, price_max, summary}, ...]
        """
        logger.info("=" * 50)
        logger.info(f"📊 СРАВНЕНИЕ: {len(shops_data)} конкурентов")

        criteria = ["design_score", "bouquet_design_score", "animation_potential",
                    "freshness_guarantee_score", "delivery_clarity_score", "promo_offer_strength"]
        lines = []
        for s in shops_data:
            sc = s.get("scores", {})
            lines.append(
                f"- {s.get('name')} (id={s.get('id')}): "
                + ", ".join(f"{c}={sc.get(c, 0)}" for c in criteria)
                + f"; цены {s.get('price_min')}-{s.get('price_max')} руб"
                + f"; резюме: {(s.get('summary') or '')[:300]}"
            )
        system_prompt = """Ты — опытный флорист-маркетолог. Сопоставь цветочных конкурентов и верни строго JSON:
{
    "matrix": [{"criterion": "design_score", "values": {"id1": 7, "id2": 5}, "winner": "id1"}, ...],
    "overall_summary": "3-5 предложений: кто лидер, разрывы, что перенять"
}
Критерии: design_score, bouquet_design_score, animation_potential, freshness_guarantee_score, delivery_clarity_score, promo_offer_strength, price_min (меньше = лучше).
winner — id лидера по критерию.
Длина всего ответа — не более 5000 токенов."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Сопоставь конкурентов:\n" + "\n".join(lines)}
                ],
                temperature=0.3,
                max_tokens=6000
            )
            data = self._parse_json_response(response.choices[0].message.content)
            logger.info("  ✓ Сравнение готово")
            logger.info("=" * 50)
            return {"matrix": data.get("matrix", []), "overall_summary": data.get("overall_summary", "")}
        except Exception as e:
            logger.error(f"  ✗ Ошибка сравнения: {e}")
            logger.error("=" * 50)
            raise


# Глобальный экземпляр
logger.info("Создание глобального экземпляра OpenAI сервиса...")
openai_service = OpenAIService()
