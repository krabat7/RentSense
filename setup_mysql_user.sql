-- Скрипт для настройки пользователя MySQL для внешних подключений
-- Выполнить на сервере: docker exec -i <mysql_container> mysql -uroot -prootpassword < setup_mysql_user.sql

-- Создать или обновить пользователя rentsense с доступом из любого хоста
CREATE USER IF NOT EXISTS 'rentsense'@'%' IDENTIFIED BY 'rentsense';
GRANT ALL PRIVILEGES ON rentsense.* TO 'rentsense'@'%';

-- Также дать root доступ с вашего IP (95.24.34.218) - опционально
-- GRANT ALL PRIVILEGES ON *.* TO 'root'@'95.24.34.218' IDENTIFIED BY 'rootpassword';

FLUSH PRIVILEGES;

-- Проверка созданных пользователей
SELECT User, Host FROM mysql.user WHERE User IN ('root', 'rentsense');

