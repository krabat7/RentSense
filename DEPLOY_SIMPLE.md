# 🚀 Простая инструкция по развертыванию

## Что нужно сделать ВАМ:

### 1. Подключиться к серверу

```bash
ssh root@89.110.92.128
# Введите пароль от VDSina
```

### 2. Загрузить проект на сервер

**На вашем компьютере (PowerShell):**

```powershell
cd F:\hw_hse\Diploma\RentSense

# Скопировать файлы на сервер
scp -r app ml tests docker-compose.prod.yml Dockerfile requirements.txt *.sh *.md create_database.py .env.server root@89.110.92.128:/root/rentsense/
```

### 3. На сервере запустить один скрипт

**На сервере:**

```bash
cd /root/rentsense
chmod +x auto_setup.sh
./auto_setup.sh
```

**Готово!** Скрипт сам установит всё необходимое.

## Что делает auto_setup.sh:

✅ Устанавливает Docker и Docker Compose  
✅ Устанавливает системные зависимости  
✅ Настраивает .env (генерирует пароли если нужно)  
✅ Запускает docker-compose  
✅ Инициализирует БД  
✅ Настраивает бэкапы  
✅ Проверяет что всё работает  

## После запуска скрипта:

Проверить что всё работает:

```bash
# Статус
docker-compose -f docker-compose.prod.yml ps

# Тест парсера
docker-compose -f docker-compose.prod.yml exec backend python -c "
from app.parser.main import apartPage
result = apartPage(['311739319'], dbinsert=True)
print('Result:', result)
"

# Проверка данных
docker-compose -f docker-compose.prod.yml exec mysql mysql -uroot -pYOUR_PASSWORD rentsense -e "SELECT COUNT(*) FROM offers;"
```

## ⚠️ Важно:

1. **Пароль MySQL** будет показан в конце скрипта - **СОХРАНИТЕ ЕГО!**
2. Если скрипт спросит про пароль - можете согласиться (он сгенерирует надежный)
3. Если будут ошибки - посмотрите логи: `docker-compose logs`

## 🆘 Если что-то пошло не так:

```bash
# Посмотреть логи
docker-compose -f docker-compose.prod.yml logs

# Перезапустить
docker-compose -f docker-compose.prod.yml restart

# Полная перезагрузка
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

