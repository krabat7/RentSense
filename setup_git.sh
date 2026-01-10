#!/bin/bash
# Скрипт для настройки Git репозитория

echo "=== Настройка Git репозитория ==="

# Проверяем, инициализирован ли уже Git
if [ -d .git ]; then
    echo "Git уже инициализирован"
else
    echo "Инициализация Git..."
    git init
fi

# Проверяем наличие удаленного репозитория
if git remote | grep -q origin; then
    echo "Удаленный репозиторий уже настроен:"
    git remote -v
    read -p "Хотите изменить URL? (y/n): " change
    if [ "$change" = "y" ]; then
        read -p "Введите URL репозитория GitHub: " repo_url
        git remote set-url origin "$repo_url"
    fi
else
    echo "Добавьте удаленный репозиторий командой:"
    echo "git remote add origin https://github.com/YOUR_USERNAME/RentSense.git"
fi

echo ""
echo "=== Статус файлов ==="
git status

echo ""
echo "=== Следующие шаги ==="
echo "1. git add ."
echo "2. git commit -m 'Initial commit'"
echo "3. git branch -M main"
echo "4. git push -u origin main"

