# Быстрое исправление на сервере

## Проблема
В cron задаче указан неправильный путь: `/root/RentSense`, а проект находится в `/root/rentsense`

## Решение

Выполните на сервере:

```bash
ssh root@89.110.92.128
cd /root/rentsense

# 1. Обновите скрипт (он теперь автоматически определяет путь)
git pull origin main

# 2. Исправьте cron задачу с правильным путем
crontab -e
# Замените строку:
# */5 * * * * /root/RentSense/git-pull-hook.sh >> /var/log/git-pull.log 2>&1
# На:
*/5 * * * * /root/rentsense/git-pull-hook.sh >> /var/log/git-pull.log 2>&1

# Или удалите старую и добавьте новую:
crontab -l | grep -v "git-pull-hook" | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /root/rentsense/git-pull-hook.sh >> /var/log/git-pull.log 2>&1") | crontab -

# 3. Проверьте
crontab -l

# 4. Добавьте SSH ключ в GitHub (если еще не добавили)
# Скопируйте ключ:
cat ~/.ssh/id_rsa.pub
# Добавьте в: https://github.com/settings/keys -> New SSH key
```

## Проверка работы

```bash
# Проверьте логи
tail -f /var/log/git-pull.log

# Или запустите скрипт вручную для теста
/root/rentsense/git-pull-hook.sh
```

