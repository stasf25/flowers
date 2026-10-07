"""
Pydantic схемы для API
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# === Запросы ===

class TextAnalysisRequest(BaseModel):
    """Запрос на анализ текста"""
    text: str = Field(..., min_length=10, description="Текст для анализа")
    shop: str = Field("", description="Конкурент: выбор из списка или свое название (необязательно)")


class ParseDemoRequest(BaseModel):
    """Запрос на парсинг URL"""
    url: str = Field(..., description="URL для парсинга")
    shop: str = Field("", description="Конкурент: выбор из списка или свое название (необязательно)")


class ReviewsAnalysisRequest(BaseModel):
    """Запрос на анализ отзывов (вставленный текст, без скрапинга)"""
    text: str = Field(..., min_length=10, description="Текст отзывов для анализа")
    shop: str = Field("", description="Конкурент: выбор из списка или свое название (необязательно)")
    source: str = Field("", description="Источник отзывов (напр. Яндекс.Карты)")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Средняя оценка, если известна")


class CompareRequest(BaseModel):
    """Запрос на сопоставление конкурентов"""
    shop_ids: List[str] = Field(..., min_length=2, description="ID конкурентов для сравнения (мин. 2)")


# === Ответы: цветочная ниша (шаг 3) ===

class CompetitorAnalysis(BaseModel):
    """Структурированный анализ конкурента (цветочная ниша)"""
    strengths: List[str] = Field(default_factory=list, description="Сильные стороны")
    weaknesses: List[str] = Field(default_factory=list, description="Слабые стороны")
    unique_offers: List[str] = Field(default_factory=list, description="Уникальные предложения")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")
    summary: str = Field("", description="Общее резюме")
    # --- Шаг 3: флористические скоринги ---
    design_score: int = Field(0, ge=0, le=10, description="Дизайн сайта 0-10")
    bouquet_design_score: int = Field(0, ge=0, le=10, description="Качество фото/дизайн букетов 0-10")
    animation_potential: int = Field(0, ge=0, le=10, description="Потенциал анимаций/интерактива 0-10")
    freshness_guarantee_score: int = Field(0, ge=0, le=10, description="Гарантии свежести 0-10")
    delivery_clarity_score: int = Field(0, ge=0, le=10, description="Понятность доставки 0-10")
    promo_offer_strength: int = Field(0, ge=0, le=10, description="Сила акций/промо 0-10")
    price_segment: str = Field("", description="Ценовой сегмент: бюджет/средний/премиум/люкс")


class ImageAnalysis(BaseModel):
    """Анализ изображения (режим site: скриншот сайта; bouquet: карточка букета)"""
    description: str = Field("", description="Описание изображения")
    marketing_insights: List[str] = Field(default_factory=list, description="Маркетинговые инсайты")
    visual_style_score: int = Field(0, ge=0, le=10, description="Оценка визуального стиля (0-10)")
    visual_style_analysis: str = Field("", description="Анализ визуального стиля")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")
    # --- Шаг 3: общие ---
    design_score: int = Field(0, ge=0, le=10, description="Оценка дизайна 0-10")
    instagrammability_score: int = Field(0, ge=0, le=10, description="Виральность для соцсетей 0-10")
    # --- Шаг 3: только режим bouquet ---
    bouquet_composition_analysis: str = Field("", description="Разбор композиции букета")
    dominant_flowers: List[str] = Field(default_factory=list, description="Распознанные цветы")
    color_harmony_score: int = Field(0, ge=0, le=10, description="Гармония цвета 0-10")
    styling_elements: List[str] = Field(default_factory=list, description="Упаковка/ленты/фон/декор")
    occasion_fit: List[str] = Field(default_factory=list, description="Подходящие поводы")


class ReviewsAnalysis(BaseModel):
    """Анализ отзывов о конкуренте"""
    sentiment: float = Field(0.0, ge=-1, le=1, description="Тональность -1..1")
    positive_themes: List[str] = Field(default_factory=list, description="За что хвалят")
    negative_themes: List[str] = Field(default_factory=list, description="На что жалуются")
    delivery_complaints_ratio: float = Field(0.0, ge=0, le=1, description="Доля жалоб на доставку")
    freshness_complaints_ratio: float = Field(0.0, ge=0, le=1, description="Доля жалоб на свежесть")
    photo_mismatch_mentions: int = Field(0, ge=0, description="Упоминания несоответствия фото")
    summary: str = Field("", description="Резюме по отзывам")


class ComparisonRow(BaseModel):
    """Строка сравнительной матрицы"""
    criterion: str = Field(..., description="Критерий")
    values: Dict[str, Any] = Field(default_factory=dict, description="Значения по shop_id")
    winner: Optional[str] = Field(None, description="ID лидера по критерию")


class ParsedContent(BaseModel):
    """Результат парсинга страницы"""
    url: str
    title: Optional[str] = None
    h1: Optional[str] = None
    first_paragraph: Optional[str] = None
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class TextAnalysisResponse(BaseModel):
    """Ответ на анализ текста"""
    success: bool
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    """Ответ на анализ изображения"""
    success: bool
    analysis: Optional[ImageAnalysis] = None
    error: Optional[str] = None


class ReviewsAnalysisResponse(BaseModel):
    """Ответ на анализ отзывов"""
    success: bool
    analysis: Optional[ReviewsAnalysis] = None
    error: Optional[str] = None


class ParseDemoResponse(BaseModel):
    """Ответ на парсинг"""
    success: bool
    data: Optional[ParsedContent] = None
    error: Optional[str] = None


class CompareResponse(BaseModel):
    """Ответ на сопоставление"""
    success: bool
    competitors: List[str] = Field(default_factory=list)
    matrix: List[ComparisonRow] = Field(default_factory=list)
    overall_summary: str = ""
    error: Optional[str] = None


# === Конкуренты (файл data/competitors.json) ===

class CompetitorProfile(BaseModel):
    """Профиль конкурента"""
    id: str
    name: str
    url: str = ""
    price_min: Optional[int] = None
    price_max: Optional[int] = None


class CompetitorsResponse(BaseModel):
    """Список конкурентов"""
    items: List[CompetitorProfile]
    total: int


class CompetitorCreate(BaseModel):
    """Новый конкурент (id опционален — генерируется из имени)"""
    id: str = Field("", description="ID (пусто = автогенерация из имени)")
    name: str = Field(..., min_length=1, description="Название")
    url: str = Field("", description="Сайт")
    price_min: Optional[int] = Field(None, ge=0, description="Нижняя граница цен, ₽")
    price_max: Optional[int] = Field(None, ge=0, description="Верхняя граница цен, ₽")


class CompetitorUpdate(BaseModel):
    """Редактирование конкурента (id в пути, неизменен)"""
    name: Optional[str] = Field(None, min_length=1, description="Название")
    url: Optional[str] = Field(None, description="Сайт")
    price_min: Optional[int] = Field(None, ge=0, description="Нижняя граница цен, ₽")
    price_max: Optional[int] = Field(None, ge=0, description="Верхняя граница цен, ₽")


# === История ===

class HistoryItem(BaseModel):
    """Элемент истории"""
    id: str
    timestamp: datetime
    request_type: str  # "text", "image", "bouquet", "parse", "reviews", "compare"
    request_summary: str
    response_summary: str


class HistoryResponse(BaseModel):
    """Ответ со списком истории"""
    items: List[HistoryItem]
    total: int
