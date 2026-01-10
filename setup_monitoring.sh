#!/bin/bash
# Установка скриптов мониторинга на сервере

cd /root/rentsense

# Делаем скрипты исполняемыми
chmod +x monitor_parser.sh parser_stats.sh quick_check.sh

echo "✓ Скрипты мониторинга установлены"
echo ""
echo "Доступные команды:"
echo "  ./quick_check.sh      - Быстрая проверка статуса"
echo "  ./parser_stats.sh     - Детальная статистика"
echo "  ./monitor_parser.sh   - Полные логи и мониторинг"
echo ""
echo "Для автоматической проверки каждые 30 минут добавьте в crontab:"
echo "  */30 * * * * cd /root/rentsense && ./quick_check.sh >> /root/rentsense/logs/parser_monitor.log 2>&1"

