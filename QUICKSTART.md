# Быстрый старт

## Что нужно сделать сейчас

### 1. Установить Docker (если нет)
Скачать с https://www.docker.com/products/docker-desktop/
После установки перезапустить компьютер.

### 2. Запустить PostgreSQL локально
```powershell
docker compose up -d postgres
```

Или если установлен старый docker-compose:
```powershell
docker-compose up -d postgres
```

### 3. Установить зависимости Python
```powershell
pip install -r requirements.txt
```

### 4. Инициализировать БД
```powershell
python app/parser/init_db.py
```

### 5. Проверить парсер

**Шаг 1: Проверить структуру страницы Циана**
```powershell
python test_cian_structure.py 12345678
```
(Замените 12345678 на реальный ID объявления с cian.ru/rent/flat/...)

**Шаг 2: Протестировать парсинг одного объявления**
```powershell
python test_parser_single.py 12345678
```

**Шаг 3: Проверить парсинг списка**
```powershell
python test_list_pages.py
```

## Про прокси

**Для тестирования прокси НЕ нужны!** 
- Можно парсить 1-2 объявления без прокси
- Для массового парсинга (1000+ объявлений) нужны прокси
- Прокси можно купить на proxy-seller.com, proxy6.net и т.д.
- Формат в .env: `PROXY1=http://user:pass@ip:port`

## Если парсер не работает

1. Проверьте структуру страницы: `python test_cian_structure.py`
2. Если структура изменилась - нужно обновить `app/parser/pagecheck.py`
3. Проверьте логи в файле `rentsense.log`

## Следующие шаги

После успешного тестирования:
1. Запустить парсинг на 100-200 объявлениях
2. Провести EDA
3. Создать гео-фичи
4. Обучить baseline модель


