# PowerShell скрипт для загрузки проекта на сервер

$SERVER_IP = "89.110.92.128"
$SERVER_USER = "root"
$PROJECT_DIR = "F:\hw_hse\Diploma\RentSense"
$REMOTE_DIR = "/root/rentsense"

Write-Host "=== Загрузка проекта на сервер ===" -ForegroundColor Green
Write-Host ""

# Создание списка файлов для исключения
$exclude = @(
    "ocenomet",
    "__pycache__",
    "*.pyc",
    "*.html",
    "*.log",
    ".env",
    "*.sql.gz",
    "rent_offer_full.json",
    "cian_*.html",
    ".git"
)

Write-Host "Создание архива проекта..." -ForegroundColor Yellow

# Переход в директорию проекта
Push-Location $PROJECT_DIR

# Создание временного списка файлов для включения
$includeFiles = @(
    "app/",
    "ml/",
    "tests/",
    "data/",
    "docker-compose.prod.yml",
    "Dockerfile",
    "requirements.txt",
    "*.md",
    "*.sh",
    "create_database.py",
    "pyproject.toml",
    ".env.example"
)

# Использование tar через WSL или Git Bash (если доступен)
$tarCommand = "tar"
if (-not (Get-Command $tarCommand -ErrorAction SilentlyContinue)) {
    Write-Host "tar не найден. Устанавливаем через WSL или используем альтернативу..." -ForegroundColor Yellow
    
    # Альтернатива: создать список файлов и скопировать через scp
    Write-Host "Копирование файлов через SCP..." -ForegroundColor Yellow
    
    # Создание директории на сервере
    ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${REMOTE_DIR}"
    
    # Копирование файлов
    $filesToCopy = @(
        "app",
        "ml",
        "tests",
        "data",
        "docker-compose.prod.yml",
        "Dockerfile",
        "requirements.txt",
        "create_database.py",
        "pyproject.toml",
        ".env.example"
    )
    
    foreach ($file in $filesToCopy) {
        if (Test-Path $file) {
            Write-Host "Копирование: $file" -ForegroundColor Cyan
            scp -r $file ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/
        }
    }
    
    # Копирование .md и .sh файлов
    Get-ChildItem -Path . -Include *.md,*.sh -Recurse | ForEach-Object {
        $relativePath = $_.FullName.Substring($PROJECT_DIR.Length + 1)
        $remotePath = "$REMOTE_DIR/$(Split-Path $relativePath -Parent)"
        ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p $remotePath"
        scp $_.FullName ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/$relativePath
    }
    
} else {
    # Использование tar (если доступен)
    Write-Host "Создание архива..." -ForegroundColor Yellow
    $archiveName = "rentsense.tar.gz"
    
    # Создание архива (исключая ненужные файлы)
    tar -czf $archiveName `
        --exclude='ocenomet' `
        --exclude='__pycache__' `
        --exclude='*.pyc' `
        --exclude='*.html' `
        --exclude='*.log' `
        --exclude='.env' `
        --exclude='*.sql.gz' `
        --exclude='rent_offer_full.json' `
        --exclude='cian_*.html' `
        --exclude='.git' `
        app/ ml/ tests/ data/ docker-compose.prod.yml Dockerfile requirements.txt *.md *.sh create_database.py pyproject.toml .env.example 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Загрузка архива на сервер..." -ForegroundColor Yellow
        scp $archiveName ${SERVER_USER}@${SERVER_IP}:/root/
        
        Write-Host "Распаковка на сервере..." -ForegroundColor Yellow
        ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${REMOTE_DIR} && cd /root && tar -xzf rentsense.tar.gz -C ${REMOTE_DIR} && rm rentsense.tar.gz"
        
        Write-Host "Удаление локального архива..." -ForegroundColor Yellow
        Remove-Item $archiveName -ErrorAction SilentlyContinue
    } else {
        Write-Host "Ошибка создания архива. Используйте ручное копирование." -ForegroundColor Red
    }
}

Pop-Location

Write-Host ""
Write-Host "=== Загрузка завершена ===" -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги:" -ForegroundColor Cyan
Write-Host "1. Подключитесь: ssh ${SERVER_USER}@${SERVER_IP}"
Write-Host "2. Перейдите: cd ${REMOTE_DIR}"
Write-Host "3. Настройте .env: cp .env.example .env && nano .env"
Write-Host "4. Запустите: docker-compose -f docker-compose.prod.yml up -d --build"

