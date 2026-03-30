# RentSense

Сервис оценки стоимости аренды квартир в Москве. Проект включает API, парсер, UI, Telegram бот и ML пайплайн с ретрейном.

## Сервисы и архитектура

- `backend` - FastAPI API (`/health`, `/api/predict`, `/api/search`).
- `streamlit` - web UI для ввода параметров и просмотра результата.
- `telegram_bot` - бот с подпиской и фильтрами.
- `parser` - фоновый сбор объявлений в БД.
- `mysql` - основная база.
- `mlflow` - UI и хранилище экспериментов.
- `adminer` - админка БД.

## Структура репозитория

- `app/api` - API и инференс.
- `app/parser` - парсер и запись в БД.
- `app/bot` - логика бота и уведомлений.
- `app/ui` - Streamlit интерфейс.
- `ml` - подготовка данных, фичи, обучение.
- `scripts` - служебные скрипты, включая ретрейн.
- `tests` - unit и smoke тесты.

## Быстрый запуск

1. Создайте `.env` в корне (минимум БД и токен бота).
2. Поднимите сервисы:

```bash
docker compose -f docker-compose.prod.yml up -d
```

3. Проверьте (развёрнутый сервер `89.110.92.128`):
- API: `http://89.110.92.128:8000/health`
- UI: `http://89.110.92.128:8501`
- MLflow: `http://89.110.92.128:5000`
- Adminer: `http://89.110.92.128:8080`

На той же машине, где запущен compose, можно открыть те же сервисы с хоста `localhost` и теми же номерами портов.

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

