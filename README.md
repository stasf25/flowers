## 🔍 CompetitorAI — мультимодальный анализатор конкурентов

AI-приложение для анализа и сопоставления конкурентов цветочного онлайн-рынка  — тексты, отзывы, скриншоты и парсинг сайтов, карточки букетов.

![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-green.svg)
![Docker](https://img.shields.io/badge/Docker-compose-blue.svg)

---

## 📋 Ниша — онлайн-магазины цветов

Что умеет приложение:
- **Анализ текста** — досье конкурента: сильные/слабые стороны, УТП, рекомендации, резюме + 7 флористических скорингов (`design_score`, `bouquet_design_score`, `animation_potential`, `freshness_guarantee_score`, `delivery_clarity_score`, `promo_offer_strength`, `price_segment`)
- **Анализ изображений** — два режима: `site` (скриншот сайта) и `bouquet` (карточка букета: композиция, сорта, гармония цвета, виральность)
- **Парсинг сайтов** — рендеринг через headless-браузер, извлечение title/h1/абзаца + скриншот + AI-анализ (поп-апы закрываются по ESC)
- **Анализ отзывов** — тональность −1..1, похвалы/жалобы, доля жалоб на доставку и свежесть
- **Сравнение** — матрица по критериям с подсветкой лидера (у цен побеждает минимум) + радар-диаграмма + вывод
- **Конкуренты** — привязка каждого анализа к магазину, данные копятся в `data/competitors.json`

## 🚀 Быстрый старт

```bash
# 1. Переменные окружения
cp .env.example .env
# впишите PROXYAPI_KEY (https://proxyapi.ru/ / routerai)

# 2. Не с чистого листа (опционально): стартовый набор конкурентов
cp examples/competitors.example.json data/competitors.json

# 3. Старт
touch history.json  # если файла нет
sudo docker compose up --build -d

# 4. Проверка
curl localhost:8000/health
curl localhost:8000/competitors
```

- Веб-интерфейс: http://localhost:8000 (порт наружу — только на `HOST_DOMAIN`, по умолчанию `127.0.0.1`; задается в `.env`)
- Админка браузера: http://127.0.0.1:3000 (только локально)
- Swagger: http://localhost:8000/docs


## ⚙️ Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `PROXYAPI_KEY` | Ключ OpenAI-совместимого API | — |
| `PROXYAPI_BASE_URL` | Базовый URL API | — |
| `PROXYAPI_CHAT_MODEL` | Текстовая модель | `gpt-4o-mini` |
| `PROXYAPI_VL_MODEL` | Vision-модель | `gpt-4o-mini` |
| `HOST_DOMAIN` | Куда биндить 8000 наружу | `127.0.0.1` |
| `BROWSERLESS_URL` / `BROWSERLESS_TOKEN` | Браузерный сервис (задает compose) | `http://browser:3000` |


## 📁 Структура

```
├── backend/
│   ├── main.py              # FastAPI: analyze_text/image/reviews, parse_demo, compare, competitors
│   ├── config.py            # Настройки (корень через find_dotenv, fail-fast)
│   ├── models/schemas.py    # Pydantic-схемы цветочной ниши
│   └── services/
│       ├── openai_service.py       # Промпты «флорист-маркетолог», JSON-парсинг
│       ├── parser_service.py       # Browserless REST (/function: goto+ESC+html+скриншот)
│       ├── history_service.py      # Журнал последних 10 (history.json)
│       └── competitors_service.py  # data/competitors.json (вложенный latest)
├── frontend/                # Vanilla JS + Chart.js (радар)
├── desktop/                 # PyQt6-клиент
├── examples/                # Статика кейса:
│   ├── competitors/         # Досье 4 магазинов + competitors_urls.txt
│   ├── screenshots/         # 4 главных + 12 карточек букетов + manifest.csv
│   ├── prices_comparison.*   # Границы цен титульных
│   └── competitors.example.json  # Стартовый набор для data/competitors.json
├── data/                    # Только runtime (монтируется): competitors.json
└── Dockerfile / docker-compose.yml  # backend + browserless/chromium (256m, CONCURRENT=1)
```

## 🔧 Эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | Веб-интерфейс |
| `POST` | `/analyze_text` | `{text, shop}` — анализ досье |
| `POST` | `/analyze_image?mode=site\|bouquet&shop=` | Анализ скриншота / карточки букета |
| `POST` | `/parse_demo` | `{url, shop}` — парсинг + анализ сайта |
| `POST` | `/analyze_reviews` | `{text, shop, source, rating?}` — анализ отзывов |
| `POST` | `/compare` | `{shop_ids[]}` — сравнение конкурентов |
| `GET/POST` | `/competitors` | Список / добавление конкурентов |
| `PUT/DELETE` | `/competitors/{id}` | Правка / удаление конкурентов |
| `GET` | `/competitors/full` | Профили + все анализы |
| `GET/DELETE` | `/history` | Журнал последних 10 действий |

## 🛠️ Технологии

- **Backend**: FastAPI, Pydantic, Python 3.10
- **AI**: OpenAI-совместимый API (текст + vision), строгий JSON
- **Парсинг**: Browserless REST (headless Chromium в отдельном контейнере, Selenium-протокол не используется)
- **Frontend**: Vanilla JS, CSS, Chart.js (радар)
- **Хранение**: `history.json` (журнал) + `data/competitors.json` (привязки)

## ⚠️ Требования

- Docker + Docker Compose (пользователь в группе `docker`)
- ~1.5 GB свободной RAM (браузер: `shm 256m`, `CONCURRENT=1`)
- API-ключ с текстовой и vision-моделью
- Интернет для AI и парсинга

## 📝 Лицензия

MIT License
