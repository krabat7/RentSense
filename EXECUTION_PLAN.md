# План выполнения задач для чекпоинта

## Этап 1: Подготовка инфраструктуры ML (1-2 часа)

### Задача 1.1: Инициализация DVC
**Файлы**: `.dvc/`, `.dvcignore`, `.dvc/config`

```bash
# 1. Инициализировать DVC
dvc init

# 2. Настроить remote (выбрать один вариант)
# Вариант A: S3
dvc remote add -d s3remote s3://rentsense-data/dvc

# Вариант B: MinIO (локальный)
dvc remote add -d minio s3://rentsense-data/dvc --endpoint-url http://minio:9000

# 3. Создать .dvcignore
echo "*.pyc
__pycache__/
*.log
.env
data/raw/*.csv
data/raw/*.json
ml/models/*.pkl" > .dvcignore

# 4. Добавить первые файлы под версионирование
dvc add data/raw/ -o data/raw.dvc
dvc push
```

**Проверка**: `dvc remote list`, `ls -la .dvc/`

---

### Задача 1.2: Настройка MLflow
**Файлы**: `ml/mlflow_config.py`, добавить в `requirements.txt` (уже есть)

```python
# ml/mlflow_config.py
import mlflow
import os

# Настройка tracking URI
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Создание эксперимента
EXPERIMENT_NAME = "rentsense-rent-prediction"
try:
    experiment_id = mlflow.create_experiment(EXPERIMENT_NAME)
except:
    experiment_id = mlflow.get_experiment_by_name(EXPERIMENT_NAME).experiment_id

mlflow.set_experiment(EXPERIMENT_NAME)
```

**Проверка**: Импорт работает без ошибок

---

## Этап 2: EDA и анализ данных (3-4 часа)

### Задача 2.1: Создать EDA ноутбук
**Файл**: `ml/eda/eda_v1.ipynb`

**Содержание**:
1. Загрузка данных из БД
2. Общий обзор датасета
3. Распределения:
   - Цены (гистограмма, boxplot)
   - Числовые признаки (площадь, этаж, возраст дома)
   - Категориальные признаки (район, тип ремонта, материал)
4. Анализ пропусков:
   - Heatmap пропусков
   - Процент пропусков по признакам
   - Стратегии заполнения
5. Выбросы:
   - IQR метод
   - Z-score метод
   - Визуализация выбросов
6. Утечка по времени:
   - Разделение на train/test по дате публикации
   - Проверка, что test позже train
   - Визуализация распределения по времени

**Шаблон начала**:
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from dotenv import dotenv_values
from datetime import datetime

# Подключение к БД
env = dotenv_values('.env')
engine = create_engine(
    f"mysql+pymysql://{env['DB_LOGIN']}:{env['DB_PASS']}"
    f"@{env['DB_IP']}:{env['DB_PORT']}/{env['DB_NAME']}"
)

# Загрузка данных
query = """
SELECT * FROM offers o
LEFT JOIN addresses a ON o.cian_id = a.cian_id
LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id
LEFT JOIN offers_details od ON o.cian_id = od.cian_id
"""

df = pd.read_sql(query, engine)
```

---

## Этап 3: Подготовка данных для обучения (2-3 часа)

### Задача 3.1: Создать скрипт подготовки данных
**Файл**: `ml/prepare_data.py`

**Функционал**:
1. Загрузка данных из БД
2. Очистка данных (на основе EDA)
3. Feature engineering:
   - Использовать `ml/features/geo_features.py`
   - Добавить новые признаки
4. Разделение на train/test по времени
5. Сохранение в форматы для обучения

**Структура**:
```python
# ml/prepare_data.py
from ml.features.geo_features import add_geo_features_v0
import pandas as pd
import dvc.api

def load_data():
    # Загрузка из БД
    pass

def clean_data(df):
    # Очистка на основе EDA
    pass

def engineer_features(df):
    # Добавление фичей
    df = add_geo_features_v0(df)
    # Другие фичи
    return df

def split_by_time(df, test_size_days=30):
    # Разделение по времени
    pass

if __name__ == "__main__":
    df = load_data()
    df = clean_data(df)
    df = engineer_features(df)
    train, test = split_by_time(df)
    # Сохранить
```

---

## Этап 4: Обучение бейзлайн моделей (3-4 часа)

### Задача 4.1: Создать скрипт обучения
**Файл**: `ml/models/train_baseline.py`

**Функционал**:
1. Загрузка подготовленных данных
2. Подготовка фичей и таргета
3. Обучение CatBoost и LightGBM
4. Расчет метрик:
   - MSE, MAE, MAPE, R², RMSE
   - Квантили ошибок: P10, P50, P90
5. Логирование в MLflow
6. Сохранение моделей

**Структура**:
```python
# ml/models/train_baseline.py
import mlflow
from ml.mlflow_config import EXPERIMENT_NAME
from catboost import CatBoostRegressor
import lightgbm as lgb
import pandas as pd
import numpy as np
import pickle
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

def calculate_metrics(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    r2 = r2_score(y_true, y_pred)
    
    # Квантили ошибок
    errors = np.abs(y_true - y_pred)
    p10 = np.percentile(errors, 10)
    p50 = np.percentile(errors, 50)
    p90 = np.percentile(errors, 90)
    
    return {
        'mse': mse,
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2,
        'p10': p10,
        'p50': p50,
        'p90': p90
    }

def train_catboost(X_train, y_train, X_val, y_val):
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.1,
        depth=6,
        loss_function='RMSE',
        eval_metric='RMSE',
        verbose=100
    )
    model.fit(X_train, y_train, eval_set=(X_val, y_val))
    return model

def train_lightgbm(X_train, y_train, X_val, y_val):
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
    
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9
    }
    
    model = lgb.train(
        params,
        train_data,
        valid_sets=[val_data],
        num_boost_round=1000,
        callbacks=[lgb.early_stopping(50)]
    )
    return model

if __name__ == "__main__":
    # Загрузка данных
    # Обучение моделей
    # Логирование в MLflow
    # Сохранение моделей
    pass
```

---

## Этап 5: Интеграция ML в API (2-3 часа)

### Задача 5.1: Обновить preprocess.py
**Файл**: `app/api/preprocess.py`

**Добавить функции**:
1. `prepredict()` - подготовка данных для предсказания
2. `predict()` - загрузка модели и предсказание
3. Адаптировать под аренду (не продажу)

### Задача 5.2: Обновить main.py
**Файл**: `app/api/main.py`

**Изменить endpoint `/predict`**:
```python
@router.post('/predict', response_model=PredictResponse)
async def prediction(request: PredictReq):
    from .preprocess import prepredict, predict
    
    # Подготовка данных
    data = prepredict(request.data)
    
    # Предсказание
    price = await to_thread(predict, data, request.sysmodel)
    
    return {'price': price}
```

### Задача 5.3: Загрузить модели в репозиторий
**Файлы**: `ml/models/catboost.pkl`, `ml/models/lightgbm.pkl`

---

## Этап 6: Дополнительные улучшения (1-2 часа)

### Задача 6.1: Создать таблицы geo_poi и snapshots
**Файл**: `app/parser/database.py`

Добавить модели:
```python
class GeoPOI(Base):
    __tablename__ = 'geo_poi'
    # Поля: id, name, type, lat, lng, distance_to_metro, etc.

class Snapshots(Base):
    __tablename__ = 'snapshots'
    # Поля: id, cian_id, price, created_at, snapshot_date
```

### Задача 6.2: Создать схемы raw/core/features (опционально)
Если требуется разделение схем - создать миграцию

---

## Этап 7: CI/CD (1 час)

### Задача 7.1: Настроить GitHub Actions
**Файл**: `.github/workflows/ci.yml`

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install black flake8
      - run: black --check .
      - run: flake8 .
  
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest
```

---

## Итоговая проверка чекпоинта

### Чеклист перед чекпоинтом:
- [ ] DVC инициализирован и настроен
- [ ] MLflow настроен и работает
- [ ] EDA ноутбук создан с полным анализом
- [ ] Данные подготовлены для обучения
- [ ] Модели обучены (CatBoost и LightGBM)
- [ ] Метрики рассчитаны (MSE, MAE, MAPE, R², квантили)
- [ ] API работает с реальными предсказаниями
- [ ] Модели сохранены и загружаются
- [ ] Все файлы закоммичены в репозиторий

---

## Временная оценка

- **Этап 1**: 1-2 часа
- **Этап 2**: 3-4 часа
- **Этап 3**: 2-3 часа
- **Этап 4**: 3-4 часа
- **Этап 5**: 2-3 часа
- **Этап 6**: 1-2 часа (опционально)
- **Этап 7**: 1 час

**Итого**: 13-19 часов работы

---

## Порядок выполнения

Рекомендуемый порядок:
1. **Этап 1** - подготовка инфраструктуры
2. **Этап 2** - анализ данных (EDA)
3. **Этап 3** - подготовка данных
4. **Этап 4** - обучение моделей
5. **Этап 5** - интеграция в API
6. **Этап 6** - дополнительные улучшения
7. **Этап 7** - CI/CD

Можно выполнять параллельно: Этап 1 + Этап 2, Этап 3 + Этап 4

