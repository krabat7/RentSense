# Отчет по выполнению чекпоинта "Основная разработка" (20.01-10.03)

## Общая информация

Проект: RentSense - сервис предсказания стоимости аренды недвижимости в Москве с использованием методов машинного обучения.

Период: 20.01-10.03

Статус: Все основные пункты чекпоинта выполнены.

## Выполненные этапы

### 1. Фичи v2 (20.01 - 05.02)

#### 1.1 Travel-time фичи
**Файл:** `ml/features/travel_features.py`

Реализованы фичи:
- `metro_walking_time` - время пешком до метро
- `metro_transport_time` - время на транспорте до метро
- `has_metro_nearby` - бинарная фича (метро < 10 мин)
- `metro_accessibility_zone` - категоризация по зонам (0-5, 5-10, 10-15, >15 мин)
- `estimated_distance_to_metro_km` - приблизительное расстояние до метро

#### 1.2 Сезонные фичи
**Файл:** `ml/features/seasonal_features.py`

Реализованы фичи:
- `publication_month` - месяц публикации (1-12)
- `publication_day_of_week` - день недели (0-6)
- `is_weekend` - выходной день
- `publication_month_sin/cos` - циклическое кодирование месяца
- `publication_day_sin/cos` - циклическое кодирование дня недели
- `publication_season` - сезон (весна, лето, осень, зима)
- `publication_quarter` - квартал года (1-4)
- Агрегаты: `monthly_avg_price`, `seasonal_avg_price`, `quarterly_avg_price`

#### 1.3 Фичи этажности и типа дома
**Файл:** `ml/features/building_features.py`

Реализованы фичи:
- `floor_ratio` - соотношение этажа к общему количеству этажей
- `is_first_floor`, `is_last_floor`, `is_middle_floor` - бинарные фичи
- `building_type_category` - категория дома (низкоэтажный, среднеэтажный, высокоэтажный)
- `material_floor_interaction` - взаимодействие материала и этажа
- `floor_position_normalized` - нормализованная позиция на этаже (0.0-1.0)
- `floor_third` - треть этажа (bottom, middle, top)

#### 1.4 Интеракции
**Файл:** `ml/features/interaction_features.py`

Реализованы фичи:
- Полиномиальные: `total_area_squared`, `rooms_count_squared`, `kitchen_area_squared`
- Комбинации: `rooms_area_interaction`, `living_total_interaction`, `kitchen_total_interaction`
- Отношения: `living_area_ratio`, `kitchen_area_ratio`
- Взаимодействия: `price_sqm_district_interaction`, `area_repair_interaction`, `floor_area_interaction`

#### 1.5 Кластеризация районов
**Файл:** `ml/features/cluster_features.py`

Реализованы фичи:
- `district_cluster_kmeans` - кластер KMeans (по distance_from_center, price_per_sqm, build_year)
- `district_cluster_hdbscan` - кластер HDBSCAN (опционально, если библиотека доступна)
- `cluster_price_mean` - средняя цена в кластере

#### 1.6 Интеграция фичей v2
**Файл:** `ml/features/__init__.py`

Создана функция `add_features_v2()` объединяющая все новые фичи. Обновлен `ml/prepare_data.py` для использования v2.

### 2. Улучшение метрик (05.02 - 12.02)

#### 2.1 Квантильная регрессия
**Файл:** `ml/train_quantile.py`

Реализовано обучение CatBoost моделей с `loss_function='Quantile'` для квантилей [0.1, 0.5, 0.9]:
- 3 модели (P10, P50, P90)
- Метрики: MAE, RMSE, MAPE для каждого квантиля
- Метрики вилки: coverage_p10_p90, mean_interval_width
- Логирование в MLflow

#### 2.2 Логарифмирование цены
**Файл:** `ml/train_baseline.py` (обновлен)

Добавлена опция `use_log_price=True`:
- Трансформация: `y_log = np.log1p(y)`
- Обратная: `y_pred = np.expm1(y_pred_log)`
- Параметр логируется в MLflow

#### 2.3 Дополнительные метрики
**Файл:** `ml/metrics.py`

Реализованы метрики:
- R² (коэффициент детерминации)
- Median Absolute Error
- Symmetric MAPE
- Метрики по ценовым сегментам (дешевые <50k, средние 50-150k, дорогие >150k)
- Функция `calculate_all_metrics()` для вычисления всех метрик

### 3. FastAPI сервис (12.02 - 22.02)

#### 3.1 Загрузка модели
**Файл:** `app/api/model_loader.py`

Реализовано:
- Функция `load_model()` для загрузки CatBoost моделей
- Кэширование моделей в памяти (`_models_cache`)
- Поддержка квантильных моделей через `load_quantile_models()`
- Поддержка baseline моделей через `load_baseline_model()`

#### 3.2 Предобработка для inference
**Файл:** `app/api/preprocess_inference.py`

Реализовано:
- Функция `prepare_features_for_prediction()` - применяет все фичи v2
- Функция `fill_missing_for_inference()` - заполнение пропусков значениями по умолчанию
- Использование тех же трансформаций, что и при обучении

#### 3.3 Endpoint /predict
**Файл:** `app/api/main.py` (обновлен)

Реализовано:
- Загрузка данных из `PredictReq`
- Применение предобработки
- Использование квантильных моделей (P10, P50, P90) или baseline модели
- Возврат `PredictResponse` с ценой и вилкой (price_p10, price_p90)
- Обработка ошибок и валидация

#### 3.4 Endpoint /search
**Файл:** `app/api/search.py`

Реализовано:
- Параметры поиска: district, price_min/max, area_min/max, rooms, metro, travel_time_max
- SQL запрос к БД с фильтрами
- Пагинация (limit, offset)
- Сортировка: relevance, price_asc, price_desc, date_desc
- Response модель: `SearchResponse` с списком объявлений

#### 3.5 Документация API
**Файл:** `app/api/main.py`

Добавлены:
- Описания к эндпоинтам (docstrings)
- OpenAPI схема автоматически через FastAPI
- Метаданные FastAPI (title, description, version)

### 4. Streamlit UI (22.02 - 01.03)

#### 4.1 Базовая структура
**Файл:** `app/ui/streamlit_app.py`

Реализовано:
- Главная страница с формой ввода параметров квартиры
- Секции: форма (боковая панель), карта, результаты

#### 4.2 Форма ввода
Реализованы поля:
- Район, улица, дом
- Этаж, этажей в доме
- Площади (общая, жилая, кухня)
- Количество комнат
- Тип ремонта, тип дома
- Год постройки
- Метро, время до метро
- Координаты (широта, долгота)

#### 4.3 Интеграция с API
- Вызов `/predict` при отправке формы
- Отображение предсказанной цены и вилки (P10-P90)
- Обработка ошибок

#### 4.4 Карта
- Использование `streamlit-folium`
- Отображение местоположения квартиры на карте Москвы
- Маркеры похожих объявлений из `/search` API
- Интерактивная карта с zoom/pan

#### 4.5 Визуализация вилки цен
- График с предсказанной ценой (P50) и доверительным интервалом (P10-P90) через Plotly
- Таблица похожих объявлений из БД

#### 4.6 Docker интеграция
**Файл:** `docker-compose.prod.yml` (обновлен)

Добавлен сервис `streamlit` на порт 8501 с зависимостью от `backend`.

### 5. Telegram бот (01.03 - 10.03)

#### 5.1 Базовая структура бота
**Файл:** `app/bot/telegram_bot.py`

Реализовано:
- Использование `python-telegram-bot`
- Команды: `/start`, `/help`, `/status`
- Обработка ошибок и логирование

#### 5.2 Сканирование новых объявлений
**Файл:** `app/bot/scanner.py`

Реализовано:
- Функция `scan_new_offers()` - запрос к БД за последние N часов
- Фильтрация по критериям (deal_type='rent', category != 'dailyFlatRent')
- Лимит 100 объявлений за запрос

#### 5.3 Логика алертов
**Файл:** `app/bot/alert_logic.py`

Реализовано:
- Функция `should_send_alert()` - проверка критериев и лимита
- Лимит 5 пушей в день на пользователя
- Функция `prioritize_offers()` - приоритизация (новые, дешевые)

#### 5.4 Шаблоны сообщений
**Файл:** `app/bot/templates.py`

Реализовано:
- Функция `format_offer_message()` - форматирование объявления
- Включение: адрес, цена, площадь, комнаты, метро, ссылка на Циан
- Эмодзи и форматирование Markdown

#### 5.5 Планировщик задач
**Файл:** `app/bot/scheduler.py`

Реализовано:
- Функция `send_alerts()` - основная логика отправки алертов
- Интеграция с `scanner`, `alert_logic`, `templates`, `database`
- Задержка между сообщениями (1 сек)
- Функция `run_alert_job()` для запуска из cron

#### 5.6 База данных для бота
**Файл:** `app/bot/database.py`

Реализованы таблицы:
- `bot_users` - пользователи бота (user_id, chat_id, preferences, alerts_today, is_active)
- `sent_alerts` - история отправленных алертов (user_id, cian_id, sent_at) для дедупликации
- Функции: `get_user()`, `create_user()`, `was_alert_sent()`, `mark_alert_sent()`, `reset_daily_alerts()`

#### 5.7 Конфигурация
**Файл:** `.env` (требуется обновление)

Необходимые переменные:
- `TELEGRAM_BOT_TOKEN` - токен бота
- `TELEGRAM_ALERT_LIMIT=5` - лимит алертов в день
- `TELEGRAM_SCAN_INTERVAL_HOURS=12` - интервал сканирования

#### 5.8 Документация эндпоинтов бота
**Файл:** `app/bot/README.md`

Создана документация:
- Описание команд
- Настройка уведомлений
- Примеры использования
- Инструкции по запуску

#### 5.9 Docker интеграция
**Файл:** `docker-compose.prod.yml` (обновлен)

Добавлен сервис `telegram_bot` с зависимостями от `mysql` и переменными окружения.

## Структура проекта

```
RentSense/
├── app/
│   ├── api/
│   │   ├── model_loader.py          # Загрузка моделей
│   │   ├── preprocess_inference.py  # Предобработка для inference
│   │   ├── search.py                # Endpoint /search
│   │   ├── main.py                  # Endpoint /predict (обновлен)
│   │   └── models.py                # Модели Pydantic (обновлен)
│   ├── bot/
│   │   ├── telegram_bot.py          # Основной бот
│   │   ├── scanner.py               # Сканирование объявлений
│   │   ├── alert_logic.py           # Логика алертов
│   │   ├── templates.py             # Шаблоны сообщений
│   │   ├── scheduler.py             # Планировщик задач
│   │   ├── database.py              # БД для бота
│   │   └── README.md                # Документация
│   ├── ui/
│   │   └── streamlit_app.py         # Streamlit UI
│   ├── parser/                      # Парсер ЦИАН
│   └── scheduler/                   # Планировщик парсера
├── ml/
│   ├── features/
│   │   ├── travel_features.py       # Travel-time фичи
│   │   ├── seasonal_features.py     # Сезонные фичи
│   │   ├── building_features.py     # Фичи этажности
│   │   ├── interaction_features.py   # Интеракции
│   │   ├── cluster_features.py      # Кластеризация
│   │   ├── geo_features.py          # Гео-фичи v0
│   │   └── __init__.py               # add_features_v2()
│   ├── train_quantile.py            # Квантильная регрессия
│   ├── train_baseline.py            # Baseline (обновлен)
│   ├── metrics.py                  # Дополнительные метрики
│   └── prepare_data.py              # Подготовка данных (обновлен)
└── docker-compose.prod.yml          # Docker Compose (обновлен)
```

## Технический стек

- Python 3.10+
- FastAPI для API
- Streamlit для UI
- python-telegram-bot для Telegram бота
- CatBoost, LightGBM для ML
- scikit-learn для кластеризации (KMeans, HDBSCAN опционально)
- MLflow для экспериментов
- MySQL 8.0 для БД
- Docker/Docker Compose для деплоя

## Новые зависимости

Добавлены в `requirements.txt`:
- `streamlit` - для UI
- `streamlit-folium` - для карт
- `plotly` - для визуализаций
- `python-telegram-bot` - для Telegram бота
- `scikit-learn` - для кластеризации
- `hdbscan` - опционально, для HDBSCAN кластеризации

## Результаты

Все 5 основных этапов чекпоинта выполнены:

1. Фичи v2 - реализованы и интегрированы
2. Улучшение метрик - квантильная регрессия, логарифмирование, дополнительные метрики
3. FastAPI сервис - endpoints /predict и /search работают
4. Streamlit UI - форма, карта, визуализация вилки цен
5. Telegram бот - сканирование, алерты, планировщик
