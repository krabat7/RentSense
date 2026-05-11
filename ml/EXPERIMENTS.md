# ML-эксперименты

Основной экспериментальный контур вынесен в скрипты, а не в отдельный notebook. Это позволяет повторить подготовку данных, обучение и логирование метрик в одном pipeline.

## Входные данные

- Источник: MySQL, таблицы объявлений и связанных характеристик.
- Сборка датасета: `ml/prepare_data.py`.
- Целевая переменная: `price_actual` из `price_changes`, иначе `offers.price`.
- Split: последние 30 дней по `publication_at` идут в test, остальная история идет в train.

## Baseline-модели

Скрипт: `ml/train_baseline.py`.

Обучаются три модели:

- CatBoost
- LightGBM
- XGBoost

Для сравнения используются:

- MAE
- RMSE
- MAPE
- P10, P50, P90 абсолютной ошибки

Метрики и параметры логируются в MLflow. Артефакты сохраняются в `ml/models`.

## Зафиксированный запуск для ВКР

В тексте ВКР приведен baseline-запуск с такими test-метриками:

| Модель | MAE | RMSE | MAPE |
| --- | ---: | ---: | ---: |
| CatBoost | 2230.27 | 13273.52 | 1.47 |
| LightGBM | 3009.59 | 16638.13 | 2.02 |
| XGBoost | 4166.01 | 28075.23 | 2.10 |

Основная модель для backend - CatBoost.

## Интерпретация признаков

Скрипт: `ml/eda/run_shap_db_cutoff.py`.

Он считает TreeSHAP через `CatBoostRegressor.get_feature_importance(..., type="ShapValues")` и сохраняет таблицу mean absolute SHAP в `ml/eda/shap_out`.

## Повторный запуск

Подготовка данных:

```bash
python ml/prepare_data.py
```

Обучение baseline:

```bash
python ml/train_baseline.py
```

Полный retrain из контейнера:

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/monthly_model_retrain.py
```

## Подбор гиперпараметров

Отдельный GridSearch, RandomizedSearch или Optuna в текущей версии не используется. ВКР сравнивает несколько baseline-моделей на едином наборе признаков и одном временном split.
