# RentSense

Сервис оценки стоимости аренды квартир в Москве. Проект включает API, парсер, [веб-интерфейс Streamlit](http://89.110.92.128:8501/), [Telegram-бот @RentSenseBot](https://t.me/RentSenseBot) и ML пайплайн с ретрейном.

## Сервисы и архитектура

- `backend` - FastAPI API (см. раздел «Эндпоинты API»).
- `streamlit` - web UI для ввода параметров и просмотра результата: [http://89.110.92.128:8501/](http://89.110.92.128:8501/).
- `telegram_bot` - бот с подпиской и фильтрами: [@RentSenseBot](https://t.me/RentSenseBot).
- `parser` - фоновый сбор объявлений в БД (см. «Планировщик парсера»).
- `mysql` - основная база.
- `mlflow` - UI и хранилище экспериментов.
- `adminer` - админка БД.

## Эндпоинты API

Префикс REST API: `/api` (кроме проверки живости).

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/health` | Проверка доступности сервиса |
| GET | `/api/getparams` | Параметры объявления по URL Циана (query `url`) |
| POST | `/api/predict` | Прогноз цены по JSON с признаками |
| GET | `/api/search` | Поиск похожих объявлений в БД (query-параметры) |
| GET | `/api/metro` | Список станций метро для UI |

## Планировщик парсера

Сервис `parser` в compose запускает `python -m app.scheduler.crontab`: бесконечный цикл, в каждой итерации поднимается отдельный процесс `app.scheduler.run_parser_once` (Playwright и логика парсинга внутри). Между циклами пауза 30 минут, на один цикл действует лимит 2 часа (константы `PARSE_INTERVAL` и `MAX_CYCLE_TIME` в `crontab.py`), при превышении процесс завершается принудительно.

Код: `app/scheduler/crontab.py`, `app/scheduler/run_parser_once.py`, `app/scheduler/tasks.py`.

## Переменные окружения

Подставляются из `.env` в корне (docker compose подхватывает их для сервисов).

**Compose / инфраструктура**

- `MYSQL_ROOT_PASSWORD` - пароль root MySQL (по умолчанию в compose: `rootpassword`).
- `MYSQL_PASSWORD` - пароль пользователя `rentsense` (по умолчанию: `rentsense`).
- `TELEGRAM_BOT_TOKEN` - токен Telegram-бота (обязателен для сервиса `telegram_bot`).
- `YANDEX_GEOCODER_API_KEY` - опционально, для геокодинга в Streamlit (Яндекс до fallback на Nominatim).

**Подключение к БД (в контейнерах задаются в `docker-compose.prod.yml`, при локальном запуске - те же имена в `.env`)**

- `DB_TYPE`, `DB_LOGIN`, `DB_PASS`, `DB_IP`, `DB_PORT`, `DB_NAME`

**Прочее**

- `API_BASE_URL` - в compose задан для `streamlit` и `telegram_bot` (базовый URL API).
- `MLFLOW_TRACKING_URI` - для backend при логировании в MLflow (в compose: `file:///app/mlruns`).
- `RENTSENSE_BASELINE_LOG_TARGET` - опционально, `true`/`false`: обучалась ли baseline на `log1p` цены (см. `app/api/model_loader.py`).
- `PROXY1`, `PROXY2`, ... - опционально, прокси для парсера (см. `app/parser/tools.py`).

## Структура репозитория

- `app/api` - API и инференс.
- `app/parser` - парсер и запись в БД.
- `app/scheduler` - цикл и разовый запуск парсера для compose.
- `app/bot` - логика бота и уведомлений.
- `app/ui` - Streamlit интерфейс.
- `ml` - подготовка данных, фичи, обучение.
- `scripts` - служебные скрипты, включая ретрейн.
- `tests` - unit и smoke тесты.

## Быстрый запуск

1. Создайте `.env` в корне (см. «Переменные окружения», минимум пароли MySQL и при необходимости `TELEGRAM_BOT_TOKEN`).
2. Поднимите сервисы:

```bash
docker compose -f docker-compose.prod.yml up -d
```

3. Проверьте (развёрнутый сервер `89.110.92.128`):
- API: `http://89.110.92.128:8000/health`
- UI (Streamlit): [http://89.110.92.128:8501/](http://89.110.92.128:8501/)
- MLflow: `http://89.110.92.128:5000`
- Adminer: `http://89.110.92.128:8080`

## ML пайплайн

Ретрейн выполняется скриптом:

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/monthly_model_retrain.py
```

Что делает скрипт:
- собирает train/test из БД (`ml/prepare_data.py`);
- обучает baseline модели (`ml/train_baseline.py`);
- пишет артефакты в `ml/models`;
- логирует прогоны в MLflow (`mlruns`).

## Тесты и CI

Локальный прогон:

```bash
python -m pytest tests/ -v --tb=short
```

CI в GitHub Actions (`.github/workflows/ci.yml`) запускает:
- `black`
- `flake8`
- `pytest`

## Основные таблицы БД

- `offers`
- `addresses`
- `photos`
- `realty_inside`
- `realty_outside`
- `realty_details`
- `offers_details`
- `developers`

