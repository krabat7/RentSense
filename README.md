# RentSense

Сервис предсказания стоимости аренды недвижимости в Москве с использованием методов машинного обучения.

## Структура проекта

```
RentSense/
├── app/                    # Основное приложение
│   ├── api/               # FastAPI endpoints
│   │   ├── main.py        # API роуты
│   │   ├── models.py      # Pydantic модели
│   │   ├── preprocess.py  # Предобработка данных
│   │   └── theards.py     # Утилиты для потоков
│   ├── parser/            # Парсер ЦИАН
│   │   ├── database.py    # Модели БД (SQLAlchemy)
│   │   ├── main.py        # Основной парсер
│   │   ├── pagecheck.py   # Парсинг страниц
│   │   └── tools.py       # Утилиты (прокси, логирование)
│   ├── scheduler/         # Планировщик задач
│   │   ├── crontab.py     # Cron конфигурация
│   │   └── tasks.py       # Задачи парсинга
│   └── main.py           # Точка входа приложения
├── ml/                    # Машинное обучение
│   ├── eda/              # EDA ноутбуки (будут добавлены)
│   ├── features/         # Генерация фичей
│   │   └── geo_features.py  # Географические фичи
│   └── models/           # Обученные модели (будут добавлены)
├── data/                  # Данные
│   ├── raw/              # Сырые данные
│   └── processed/        # Обработанные данные
├── docker-compose.prod.yml  # Docker Compose конфигурация
├── Dockerfile            # Docker образ
├── requirements.txt      # Python зависимости
└── create_database.py    # Скрипт инициализации БД
```

## Требования

- Python 3.10+
- Docker и Docker Compose
- MySQL 8.0 (или использование через Docker)

## Установка

1. Клонируйте репозиторий
2. Создайте файл `.env` с настройками БД:
   ```
   DB_TYPE=mysql+pymysql
   DB_LOGIN=root
   DB_PASS=your_password
   DB_IP=localhost
   DB_PORT=3306
   DB_NAME=rentsense
   ```
3. Запустите через Docker Compose:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Использование

- API доступен на `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Парсер запускается автоматически через cron
- Adminer для управления БД: `http://localhost:8080`

## API Endpoints

- `GET /api/getparams?url=<cian_url>` - Получить параметры объявления
- `POST /api/predict` - Предсказать цену (в разработке)

## База данных

Проект использует MySQL с следующими основными таблицами:
- `offers` - объявления
- `addresses` - адреса
- `photos` - фотографии
- `realty_inside` - внутренние характеристики
- `realty_outside` - внешние характеристики
- `realty_details` - детали недвижимости
- `offers_details` - детали объявлений
- `developers` - застройщики

