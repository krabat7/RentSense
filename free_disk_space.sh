#!/bin/bash
# Освобождение места на диске

cd /root/rentsense

echo "=========================================="
echo "ОСВОБОЖДЕНИЕ МЕСТА НА ДИСКЕ"
echo "=========================================="

echo ""
echo "1. Текущее использование диска:"
df -h

echo ""
echo "2. Остановка всех контейнеров:"
docker-compose -f docker-compose.prod.yml down

echo ""
echo "3. Удаление старых Docker volumes (включая mysql_data):"
docker volume ls | grep -E "rentsense|mysql" | awk '{print $2}' | xargs -r docker volume rm || echo "Volumes не найдены или уже удалены"

echo ""
echo "4. Очистка Docker системы (образы, контейнеры, volumes):"
docker system prune -a -f --volumes

echo ""
echo "5. Очистка Docker builder cache:"
docker builder prune -a -f

echo ""
echo "6. Поиск больших файлов в /root:"
du -sh /root/* 2>/dev/null | sort -rh | head -10

echo ""
echo "7. Очистка старых логов:"
find /root/rentsense/logs -type f -mtime +7 -delete 2>/dev/null || echo "Логи не найдены"
find /root/rentsense/backups -type f -mtime +7 -delete 2>/dev/null || echo "Бэкапы не найдены"

echo ""
echo "8. Очистка временных файлов:"
rm -rf /tmp/* 2>/dev/null || true
rm -rf /var/tmp/* 2>/dev/null || true

echo ""
echo "9. Очистка apt cache:"
apt-get clean 2>/dev/null || true
apt-get autoclean 2>/dev/null || true

echo ""
echo "10. Финальное использование диска:"
df -h

echo ""
echo "=========================================="
echo "ОЧИСТКА ЗАВЕРШЕНА"
echo "=========================================="

