#!/bin/bash
# Скрипт для удаления .env из истории Git (КРИТИЧЕСКИ ВАЖНО!)

cd /root/rentsense || exit 1

echo "=== УДАЛЕНИЕ .env И СЕКРЕТОВ ИЗ GIT ИСТОРИИ ==="
echo "ВНИМАНИЕ: Это удалит .env из истории Git!"
echo "Рекомендуется после этого сменить все пароли и токены!"

read -p "Продолжить? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Отменено"
    exit 1
fi

# 1. Удаляем .env из индекса
echo "1. Удаление .env из индекса..."
git rm --cached .env 2>/dev/null || echo "  .env уже удален из индекса"

# 2. Удаляем другие секретные файлы
echo "2. Удаление бэкапов и других секретных файлов..."
git rm --cached -r __pycache__/ 2>/dev/null || true
git rm --cached app/__pycache__/ 2>/dev/null || true
git rm --cached app/parser/__pycache__/ 2>/dev/null || true
git rm --cached app/scheduler/__pycache__/ 2>/dev/null || true
git rm --cached app/parser/*.backup* 2>/dev/null || true
git rm --cached app/parser/*.broken 2>/dev/null || true
git rm --cached *.backup 2>/dev/null || true
git rm --cached *.log 2>/dev/null || true

# 3. Проверяем .gitignore
echo "3. Проверка .gitignore..."
if ! grep -q "^\.env$" .gitignore; then
    echo "  Добавление .env в .gitignore..."
    echo ".env" >> .gitignore
fi

# 4. Добавляем обновленный .gitignore
git add .gitignore

# 5. Создаем новый коммит БЕЗ .env
echo "4. Создание нового коммита без секретов..."
git commit -m "Remove secrets: удалены .env и секретные файлы из репозитория"

# 6. Принудительный push (ПЕРЕЗАПИСЫВАЕТ ИСТОРИЮ!)
echo "5. Отправка исправленного коммита на GitHub..."
echo "ВНИМАНИЕ: Это перезапишет историю на GitHub!"
read -p "Продолжить с force push? (yes/no): " force_confirm
if [ "$force_confirm" = "yes" ]; then
    git push --force origin main
    echo "✓ История очищена от секретов"
    echo ""
    echo "КРИТИЧЕСКИ ВАЖНО:"
    echo "1. Смените все пароли в .env файле на сервере!"
    echo "2. Смените пароли БД MySQL!"
    echo "3. Обновите токены прокси (если они были в .env)!"
    echo "4. Проверьте, что репозиторий приватный: https://github.com/krabat7/RentSense/settings"
else
    echo "Force push отменен. Используйте 'git push --force origin main' вручную после проверки."
fi

