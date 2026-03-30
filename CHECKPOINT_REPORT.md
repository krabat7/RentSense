# CHECKPOINT REPORT

## Что сделано

- Собран рабочий стек в `docker-compose.prod.yml`: `backend`, `streamlit`, `telegram_bot`, `parser`, `mysql`, `adminer`, `mlflow`.
- Реализован ML pipeline:
  - подготовка данных в `ml/prepare_data.py`;
  - обучение baseline моделей в `ml/train_baseline.py`;
  - ежемесячный запуск в `scripts/monthly_model_retrain.py`.
- MLflow подключен в обучении и поднят как отдельный сервис в compose.
- API реализован в `app/api/main.py`, есть `/health`, `/api/predict`, `/api/search`.
- Telegram бот реализован в `app/bot/telegram_bot.py` с фильтрами, кнопками и планировщиком уведомлений.
- Добавлены и проходят тесты:
  - `tests/test_prepare_data_pipeline.py`;
  - `tests/test_model_loader.py`;
  - `tests/test_api_main.py`;
  - `tests/test_geo_features.py`;
  - `tests/test_mlflow_config.py`.

## Текущее состояние

- Данные и модели обновляются рабочим сценарием ретрейна.
- Артефакты MLflow пишутся в каталог `mlruns`.
- Модели сохраняются в `ml/models`.
- CI в `.github/workflows/ci.yml` запускает `black`, `flake8`, `pytest`.

## Что важно для проверки

- Основной запуск: `docker compose -f docker-compose.prod.yml up -d`
- Ретрейн: `docker compose -f docker-compose.prod.yml exec backend python scripts/monthly_model_retrain.py`
- MLflow UI: `http://<server-ip>:5000`

