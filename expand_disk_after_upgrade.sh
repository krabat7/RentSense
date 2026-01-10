#!/bin/bash
# Проверка и расширение диска после повышения тарифа

cd /root/rentsense

echo "=========================================="
echo "ПРОВЕРКА ДИСКА ПОСЛЕ ПОВЫШЕНИЯ ТАРИФА"
echo "=========================================="

echo ""
echo "1. Текущее использование диска:"
df -h

echo ""
echo "2. Информация о дисках:"
lsblk

echo ""
echo "3. Размер физического диска /dev/vda:"
fdisk -l /dev/vda | grep -E "Disk /dev/vda|sectors"

echo ""
echo "4. Если диск увеличился, но файловая система нет - расширяем:"
# Для ext4 файловой системы
if mount | grep -q "/dev/vda1.*ext4"; then
    echo "Файловая система ext4 обнаружена"
    echo "Расширяем раздел (если нужно):"
    # Раскомментируйте следующие строки, если нужно расширить раздел
    # growpart /dev/vda 1
    # resize2fs /dev/vda1
    echo "Выполните вручную после увеличения диска в панели:"
    echo "  growpart /dev/vda 1"
    echo "  resize2fs /dev/vda1"
fi

echo ""
echo "5. Финальное использование диска:"
df -h

echo ""
echo "=========================================="
echo "ПОСЛЕ РАСШИРЕНИЯ - ПЕРЕЗАПУСК СЕРВИСОВ"
echo "=========================================="
echo "После расширения диска выполните:"
echo "  docker-compose -f docker-compose.prod.yml down"
echo "  docker-compose -f docker-compose.prod.yml up -d mysql"
echo "  sleep 30"
echo "  docker-compose -f docker-compose.prod.yml ps -a"

