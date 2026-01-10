# Автоматическая настройка сервера
param(
    [Parameter(Mandatory=$true)]
    [string]$ServerIP = "89.110.92.128",
    
    [Parameter(Mandatory=$true)]
    [string]$ServerPassword,
    
    [Parameter(Mandatory=$false)]
    [string]$ServerUser = "root"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Автоматическая настройка сервера ===" -ForegroundColor Green
Write-Host "Сервер: $ServerUser@$ServerIP" -ForegroundColor Cyan

# Функция для выполнения SSH команд с паролем
function Invoke-SSHCommand {
    param(
        [string]$Command,
        [string]$Password
    )
    
    # Проверка наличия sshpass или использование expect-подобного подхода
    if (Get-Command sshpass -ErrorAction SilentlyContinue) {
        sshpass -p $Password ssh -o StrictHostKeyChecking=no ${ServerUser}@${ServerIP} $Command
    } else {
        # Использование PowerShell для SSH (если доступен Posh-SSH)
        try {
            Import-Module Posh-SSH -ErrorAction Stop
            $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
            $Credential = New-Object System.Management.Automation.PSCredential($ServerUser, $SecurePassword)
            Invoke-SSHCommand -ComputerName $ServerIP -Credential $Credential -Command $Command
        } catch {
            Write-Host "Требуется установить Posh-SSH или sshpass" -ForegroundColor Yellow
            Write-Host "Установка Posh-SSH: Install-Module -Name Posh-SSH -Force" -ForegroundColor Yellow
            throw "SSH инструменты не найдены"
        }
    }
}

# Установка Posh-SSH если нужно
if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
    Write-Host "Установка Posh-SSH..." -ForegroundColor Yellow
    Install-Module -Name Posh-SSH -Force -Scope CurrentUser -AllowClobber
}

$SecurePassword = ConvertTo-SecureString $ServerPassword -AsPlainText -Force
$Credential = New-Object System.Management.Automation.PSCredential($ServerUser, $SecurePassword)

Write-Host "`nШаг 1: Проверка подключения..." -ForegroundColor Yellow
try {
    $Session = New-SSHSession -ComputerName $ServerIP -Credential $Credential -AcceptKey
    Write-Host "✓ Подключение установлено" -ForegroundColor Green
} catch {
    Write-Host "✗ Ошибка подключения: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`nШаг 2: Установка Docker..." -ForegroundColor Yellow
$dockerCheck = Invoke-SSHCommand -Index $Session.SessionId -Command "command -v docker"
if ($dockerCheck -notmatch "docker") {
    Invoke-SSHCommand -Index $Session.SessionId -Command "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh"
} else {
    Write-Host "✓ Docker уже установлен" -ForegroundColor Green
}

Write-Host "`nШаг 3: Установка Docker Compose..." -ForegroundColor Yellow
$composeCheck = Invoke-SSHCommand -Index $Session.SessionId -Command "command -v docker-compose"
if ($composeCheck -notmatch "docker-compose") {
    Invoke-SSHCommand -Index $Session.SessionId -Command "apt update && apt install -y docker-compose"
} else {
    Write-Host "✓ Docker Compose уже установлен" -ForegroundColor Green
}

Write-Host "`nШаг 4: Установка системных зависимостей..." -ForegroundColor Yellow
Invoke-SSHCommand -Index $Session.SessionId -Command "apt update && apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 wget git"

Write-Host "`nШаг 5: Создание директории проекта..." -ForegroundColor Yellow
Invoke-SSHCommand -Index $Session.SessionId -Command "mkdir -p /root/rentsense/logs /root/rentsense/backups /root/rentsense/data/raw /root/rentsense/data/processed"

Write-Host "`nШаг 6: Копирование файлов..." -ForegroundColor Yellow
$localPath = $PSScriptRoot
$remotePath = "/root/rentsense"

# Копирование основных файлов
$filesToCopy = @("app", "ml", "tests", "docker-compose.prod.yml", "Dockerfile", "requirements.txt", "create_database.py", ".env.server")
foreach ($file in $filesToCopy) {
    if (Test-Path "$localPath\$file") {
        Write-Host "  Копирование: $file" -ForegroundColor Cyan
        Set-SCPFile -ComputerName $ServerIP -Credential $Credential -LocalFile "$localPath\$file" -RemotePath "$remotePath/$file"
    }
}

# Копирование скриптов
Get-ChildItem -Path $localPath -Filter "*.sh" | ForEach-Object {
    Write-Host "  Копирование: $($_.Name)" -ForegroundColor Cyan
    Set-SCPFile -ComputerName $ServerIP -Credential $Credential -LocalFile $_.FullName -RemotePath "$remotePath/$($_.Name)"
}

Write-Host "`nШаг 7: Настройка .env..." -ForegroundColor Yellow
Invoke-SSHCommand -Index $Session.SessionId -Command "cd /root/rentsense && mv .env.server .env"

Write-Host "`n=== Настройка завершена ===" -ForegroundColor Green
Write-Host "`nСледующие шаги (выполните на сервере):" -ForegroundColor Cyan
Write-Host "1. Настройте пароли в .env: nano /root/rentsense/.env" -ForegroundColor White
Write-Host "2. Запустите: cd /root/rentsense && docker-compose -f docker-compose.prod.yml up -d --build" -ForegroundColor White
Write-Host "3. Инициализируйте БД: docker-compose exec backend python -m app.parser.init_db" -ForegroundColor White

Remove-SSHSession -SessionId $Session.SessionId | Out-Null

