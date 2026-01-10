# Автоматическая настройка сервера через SSH
param(
    [Parameter(Mandatory=$true)]
    [string]$Password
)

$ServerIP = "89.110.92.128"
$ServerUser = "root"
$ProjectDir = "F:\hw_hse\Diploma\RentSense"
$RemoteDir = "/root/rentsense"

Write-Host "=== Автоматическая настройка сервера ===" -ForegroundColor Green
Write-Host "Сервер: $ServerUser@$ServerIP" -ForegroundColor Cyan

# Установка Posh-SSH если нужно
if (!(Get-Module -ListAvailable -Name Posh-SSH)) {
    Write-Host "Установка Posh-SSH..." -ForegroundColor Yellow
    Install-Module -Name Posh-SSH -Force -Scope CurrentUser -AllowClobber -SkipPublisherCheck
}

Import-Module Posh-SSH

try {
    Write-Host "`nПодключение к серверу..." -ForegroundColor Yellow
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $Credential = New-Object System.Management.Automation.PSCredential($ServerUser, $SecurePassword)
    
    $Session = New-SSHSession -ComputerName $ServerIP -Credential $Credential -AcceptKey -ErrorAction Stop
    Write-Host "✓ Подключение установлено" -ForegroundColor Green
    
    Write-Host "`nШаг 1: Проверка Docker..." -ForegroundColor Yellow
    $dockerCheck = (Invoke-SSHCommand -Index $Session.SessionId -Command "command -v docker" -ErrorAction SilentlyContinue).Output
    if ($dockerCheck -notmatch "docker") {
        Write-Host "  Установка Docker..." -ForegroundColor Cyan
        Invoke-SSHCommand -Index $Session.SessionId -Command "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh" | Out-Null
        Write-Host "  ✓ Docker установлен" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Docker уже установлен" -ForegroundColor Green
    }
    
    Write-Host "`nШаг 2: Установка Docker Compose..." -ForegroundColor Yellow
    $composeCheck = (Invoke-SSHCommand -Index $Session.SessionId -Command "command -v docker-compose" -ErrorAction SilentlyContinue).Output
    if ($composeCheck -notmatch "docker-compose") {
        Write-Host "  Установка Docker Compose..." -ForegroundColor Cyan
        Invoke-SSHCommand -Index $Session.SessionId -Command "apt update -qq && apt install -y docker-compose" | Out-Null
        Write-Host "  ✓ Docker Compose установлен" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Docker Compose уже установлен" -ForegroundColor Green
    }
    
    Write-Host "`nШаг 3: Установка системных зависимостей..." -ForegroundColor Yellow
    Invoke-SSHCommand -Index $Session.SessionId -Command "apt update -qq && apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 wget git" | Out-Null
    Write-Host "  ✓ Зависимости установлены" -ForegroundColor Green
    
    Write-Host "`nШаг 4: Создание директорий..." -ForegroundColor Yellow
    Invoke-SSHCommand -Index $Session.SessionId -Command "mkdir -p $RemoteDir/logs $RemoteDir/backups $RemoteDir/data/raw $RemoteDir/data/processed" | Out-Null
    Write-Host "  ✓ Директории созданы" -ForegroundColor Green
    
    Write-Host "`nШаг 5: Копирование файлов..." -ForegroundColor Yellow
    Push-Location $ProjectDir
    
    # Копирование директорий и файлов
    $items = @("app", "ml", "tests", "docker-compose.prod.yml", "Dockerfile", "requirements.txt", "create_database.py", ".env.server")
    foreach ($item in $items) {
        if (Test-Path $item) {
            Write-Host "  Копирование: $item" -ForegroundColor Cyan
            Set-SCPFile -ComputerName $ServerIP -Credential $Credential -LocalFile $item -RemotePath "$RemoteDir/$item" -Force
        }
    }
    
    # Копирование скриптов
    Get-ChildItem -Filter "*.sh" | ForEach-Object {
        Write-Host "  Копирование: $($_.Name)" -ForegroundColor Cyan
        Set-SCPFile -ComputerName $ServerIP -Credential $Credential -LocalFile $_.FullName -RemotePath "$RemoteDir/$($_.Name)" -Force
    }
    
    Pop-Location
    Write-Host "  ✓ Файлы скопированы" -ForegroundColor Green
    
    Write-Host "`nШаг 6: Настройка .env..." -ForegroundColor Yellow
    Invoke-SSHCommand -Index $Session.SessionId -Command "cd $RemoteDir && mv .env.server .env" | Out-Null
    Write-Host "  ⚠️  НЕ ЗАБУДЬТЕ заменить CHANGE_THIS_TO_STRONG_PASSWORD в .env!" -ForegroundColor Yellow
    Write-Host "  ✓ .env создан" -ForegroundColor Green
    
    Write-Host "`n=== Подготовка завершена ===" -ForegroundColor Green
    Write-Host "`nСледующие команды выполните на сервере:" -ForegroundColor Cyan
    Write-Host "1. cd $RemoteDir" -ForegroundColor White
    Write-Host "2. nano .env  # Замените пароли!" -ForegroundColor White
    Write-Host "3. docker-compose -f docker-compose.prod.yml up -d --build" -ForegroundColor White
    Write-Host "4. sleep 60 && docker-compose exec backend python -m app.parser.init_db" -ForegroundColor White
    
} catch {
    Write-Host "`n✗ Ошибка: $_" -ForegroundColor Red
    exit 1
} finally {
    if ($Session) {
        Remove-SSHSession -SessionId $Session.SessionId | Out-Null
    }
}

