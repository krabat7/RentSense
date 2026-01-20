# RentSense

Сервис предсказания стоимости аренды недвижимости в Москве с использованием методов машинного обучения.

## Структура проекта

```
RentSense/
├── app/                    # Основное приложение
│   ├── api/               # FastAPI endpoints
│   ├── parser/            # Парсер ЦИАН
│   └── scheduler/         # Планировщик задач
├── ml/                    # Машинное обучение
│   ├── eda/              # EDA ноутбуки
│   ├── features/         # Генерация фичей
│   ├── models/           # Обученные модели
│   ├── prepare_data.py   # Подготовка данных
│   └── train_baseline.py # Обучение моделей
├── data/                  # Данные
│   ├── raw/              # Сырые данные
│   └── processed/        # Обработанные данные
├── tests/                 # Тесты
└── .github/workflows/     # CI/CD
```

## Требования

- Python 3.10+
- Docker и Docker Compose
- MySQL 8.0

## Установка

1. Клонируйте репозиторий
2. Создайте файл `.env` с настройками БД:
   ```
   DB_TYPE=mysql+pymysql
   DB_LOGIN=rentsense
   DB_PASS=rentsense
   DB_IP=89.110.92.128
   DB_PORT=3306
   DB_NAME=rentsense
   MLFLOW_TRACKING_URI=sqlite:///mlflow.db
   ```
3. Запустите через Docker Compose:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Использование

- API доступен на `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Парсер запускается автоматически через cron

## ML Pipeline

1. Подготовка данных:
   ```bash
   python ml/prepare_data.py
   ```

2. Обучение моделей:
   ```bash
   python ml/train_baseline.py
   ```

## База данных

Основные таблицы:
- `offers` - объявления
- `addresses` - адреса и геоданные
- `photos` - фотографии
- `realty_inside`, `realty_outside`, `realty_details` - характеристики недвижимости
- `offers_details` - детали объявлений
- `developers` - застройщики

## CI/CD

Проект использует GitHub Actions для автоматической проверки кода:
- black - форматирование кода
- flake8 - линтер
- pytest - тесты

