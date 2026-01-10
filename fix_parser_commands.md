# Исправление parser на сервере

## Проблема
Parser в состоянии `Restarting` - нет точки входа для запуска модуля.

## Решение

### ШАГ 1: Получить более детальные логи parser
```bash
cd /root/rentsense

# Остановить parser
docker-compose -f docker-compose.prod.yml stop parser

# Удалить контейнер
docker-compose -f docker-compose.prod.yml rm -f parser

# Попробовать запустить в foreground для просмотра ошибок
docker-compose -f docker-compose.prod.yml run --rm parser python -m app.scheduler.crontab
```

### ШАГ 2: Скопировать исправленный файл на сервер

**С локального компьютера (PowerShell):**
```powershell
cd F:\hw_hse\Diploma\RentSense

# Скопировать исправленный crontab.py
scp app/scheduler/crontab.py root@89.110.92.128:/root/rentsense/app/scheduler/crontab.py
```

**Или на сервере вручную отредактировать:**
```bash
cd /root/rentsense
nano app/scheduler/crontab.py
```

**Добавить в конец файла:**
```python
if __name__ == "__main__":
    asyncio.run(cron())
```

**Сохранить:** `Ctrl+O`, `Enter`, `Ctrl+X`

### ШАГ 3: Перезапустить parser
```bash
cd /root/rentsense

# Запустить parser
docker-compose -f docker-compose.prod.yml up -d parser

# Подождать 10 секунд
sleep 10

# Проверить статус
docker-compose -f docker-compose.prod.yml ps parser

# Проверить логи
docker-compose -f docker-compose.prod.yml logs parser | tail -30
```

### ШАГ 4: Проверить все сервисы
```bash
docker-compose -f docker-compose.prod.yml ps
```

