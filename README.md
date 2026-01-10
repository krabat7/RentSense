# RentSense

Сервис прогнозирования рыночной стоимости аренды жилья и персонализированного подбора объявлений.

## Быстрый старт

См. [QUICKSTART.md](QUICKSTART.md) для пошаговой инструкции.

## Структура проекта

```
RentSense/
├── app/
│   ├── parser/          # Парсер Циана для аренды
│   ├── api/              # FastAPI endpoints
│   ├── streamlit/        # Streamlit UI
│   ├── scheduler/        # Планировщик задач
│   └── ml/               # ML компоненты
├── ml/
│   ├── eda/              # EDA ноутбуки
│   ├── models/           # Обученные модели
│   └── features/         # Генерация фичей
├── data/                 # Данные (DVC)
└── tests/                # Тесты
```

## Установка

1. Установить Docker Desktop (если нет)
2. Скопировать `.env.example` в `.env` (уже создан)
3. `pip install -r requirements.txt`
4. `docker compose up -d postgres` - запустить БД
5. `python app/parser/init_db.py` - инициализировать БД

## Тестирование парсера

1. `python test_cian_structure.py 12345678` - проверить структуру страницы
2. `python test_parser_single.py 12345678` - протестировать парсинг
3. `python test_list_pages.py` - проверить список объявлений

## Запуск

- API: `python app/main.py`
- Streamlit: `streamlit run app/streamlit/main.py`

## Про прокси

Для тестирования прокси не нужны. Для массового парсинга (1000+ объявлений) рекомендуется использовать прокси.
