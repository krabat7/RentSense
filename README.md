# RentSense

RentSense - сервис оценки стоимости долгосрочной аренды квартир в Москве. Проект включает FastAPI backend, MySQL, парсер Циана, Streamlit UI, Telegram-бота, ML pipeline и MLflow.

## Сервисы

- `backend` - REST API, инференс модели, поиск по базе.
- `streamlit` - web UI для ручного прогноза, прогноза по ссылке и поиска объявлений.
- `telegram_bot` - подписка на новые объявления по фильтрам пользователя.
- `parser` - фоновый сбор и обновление объявлений.
- `mysql` - база объявлений, признаков и пользовательских настроек.
- `mlflow` - журнал ML-запусков и метрик.
- `adminer` - просмотр структуры и данных MySQL.

## REST API

Префикс прикладных методов - `/api`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | `/health` | Проверка доступности backend |
| GET | `/api/getparams` | Извлечение параметров объявления по URL Циана |
| POST | `/api/predict` | Прогноз стоимости по JSON с признаками |
| GET | `/api/search` | Поиск объявлений по фильтрам |
| GET | `/api/metro` | Список станций метро для UI |

Для `/api/*` включено мягкое ограничение частоты запросов. Для `/api/getparams` используется отдельный лимит, так как этот метод может запускать парсинг.

## Архитектура каталогов

- `app/api` - FastAPI, модели запросов, инференс, rate limit.
- `app/parser` - получение карточек объявлений и запись в БД.
- `app/scheduler` - цикл фонового парсинга.
- `app/ui` - Streamlit interface.
- `app/bot` - Telegram-бот, фильтры, алерты.
- `ml/features` - признаки для обучения и инференса.
- `ml/prepare_data.py` - сборка train/test из БД.
- `ml/train_baseline.py` - обучение CatBoost, LightGBM, XGBoost.
- `ml/train_quantile.py` - обучение квантильных моделей CatBoost.
- `ml/eda` - EDA и SHAP-анализ.
- `scripts` - служебные сценарии, включая retrain.
- `tests` - unit и smoke tests.

## Планировщик парсера

Сервис `parser` запускает `python -m app.scheduler.crontab`. В каждом цикле создается отдельный процесс `app.scheduler.run_parser_once`. Между циклами пауза 30 минут, лимит одного цикла - 2 часа. При превышении лимита процесс завершается.

Код: `app/scheduler/crontab.py`, `app/scheduler/run_parser_once.py`, `app/scheduler/tasks.py`.

## Переменные окружения

Переменные читаются из `.env` и из окружения контейнеров.

| Переменная | Назначение |
| --- | --- |
| `MYSQL_ROOT_PASSWORD` | пароль root MySQL |
| `MYSQL_PASSWORD` | пароль пользователя `rentsense` |
| `DB_TYPE`, `DB_LOGIN`, `DB_PASS`, `DB_IP`, `DB_PORT`, `DB_NAME` | подключение к БД |
| `TELEGRAM_BOT_TOKEN` | токен Telegram-бота |
| `API_BASE_URL` | базовый URL backend для клиентов |
| `YANDEX_GEOCODER_API_KEY` | геокодинг в Streamlit |
| `MLFLOW_TRACKING_URI` | MLflow tracking URI |
| `RENTSENSE_BASELINE_LOG_TARGET` | флаг `log1p` для baseline модели |
| `RS_RATE_LIMIT_ENABLED` | включение rate limit |
| `RS_RATE_LIMIT_API_PER_MINUTE` | лимит для `/api/*` |
| `RS_RATE_LIMIT_GETPARAMS_PER_MINUTE` | лимит для `/api/getparams` |
| `PROXY1`, `PROXY2`, ... | прокси для парсера |

## Запуск

```bash
docker compose -f docker-compose.prod.yml up -d
```

Проверка сервисов на развернутом хосте:

- API: `http://<host>:8000/health`
- Streamlit: `http://<host>:8501/`
- MLflow: `http://<host>:5000`
- Adminer: `http://<host>:8080`

## ML pipeline

Ретрейн:

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/monthly_model_retrain.py
```

Сценарий выполняет:

- сбор train/test из БД через `ml/prepare_data.py`;
- обучение baseline-моделей через `ml/train_baseline.py`;
- сохранение моделей в `ml/models`;
- логирование метрик и параметров в MLflow.

Подробности по экспериментам: `ml/EXPERIMENTS.md`.

## Тесты и CI

Локально:

```bash
python -m pytest tests/ -v --tb=short
```

CI в `.github/workflows/ci.yml` запускает `black`, `flake8`, `pytest`.

## Основные таблицы БД

- `offers`
- `addresses`
- `photos`
- `realty_inside`
- `realty_outside`
- `realty_details`
- `offers_details`
- `developers`
- `bot_users`
- `sent_alerts`

