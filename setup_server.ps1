# Автоматическая настройка сервера через PowerShell
param(
    [string]$ServerIP = "89.110.92.128",
    [string]$ServerUser = "root",
    [string]$Password = "D68v9kz3mL21a!FRZm23"
)

$RemoteDir = "/root/rentsense"
$ProjectDir = "F:\hw_hse\Diploma\RentSense"

Write-Host "=== Автоматическая настройка сервера ===" -ForegroundColor Green
Write-Host "Сервер: $ServerUser@$ServerIP" -ForegroundColor Cyan

# Проверка SSH ключа (первый вход требует подтверждения)
Write-Host "`nПроверка подключения..." -ForegroundColor Yellow
$null = ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 ${ServerUser}@${ServerIP} "exit" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Требуется первый вход. Подключитесь вручную один раз:" -ForegroundColor Yellow
    Write-Host "ssh $ServerUser@$ServerIP" -ForegroundColor White
    Write-Host "Введите 'yes' для подтверждения, затем пароль" -ForegroundColor Yellow
    exit 1
}

# Создание временного SSH ключа для автоматического входа
Write-Host "`nШаг 1: Подготовка SSH ключа..." -ForegroundColor Yellow
$keyPath = "$env:USERPROFILE\.ssh\id_rsa_rentsense"
if (-not (Test-Path $keyPath)) {
    ssh-keygen -t rsa -f $keyPath -N '""' -q
}

# Копирование ключа на сервер (используя expect через WSL если доступно)
Write-Host "Копирование SSH ключа..." -ForegroundColor Cyan
$expectScript = @"
#!/usr/bin/expect -f
set timeout 30
spawn ssh-copy-id -i $keyPath ${ServerUser}@${ServerIP}
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$Password\r" }
    timeout { exit 1 }
}
expect eof
"@

if (Get-Command wsl -ErrorAction SilentlyContinue) {
    $expectScript | Out-File -FilePath "$env:TEMP\ssh_copy_id.exp" -Encoding ASCII
    wsl bash -c "chmod +x /mnt/c/Users/$env:USERNAME/AppData/Local/Temp/ssh_copy_id.exp && /mnt/c/Users/$env:USERNAME/AppData/Local/Temp/ssh_copy_id.exp" 2>&1 | Out-Null
    Remove-Item "$env:TEMP\ssh_copy_id.exp" -ErrorAction SilentlyContinue
} else {
    Write-Host "WSL не найден. Копирование ключа пропущено." -ForegroundColor Yellow
    Write-Host "Используется подключение с паролем..." -ForegroundColor Yellow
}

# Функция для выполнения команд через SSH
function Invoke-RemoteCommand {
    param([string]$Command)
    
    if (Test-Path $keyPath) {
        ssh -i $keyPath -o StrictHostKeyChecking=no ${ServerUser}@${ServerIP} $Command
    } else {
        # Альтернатива: использование plink или прямое подключение
        $Command | ssh ${ServerUser}@${ServerIP} 2>&1
    }
}

# Функция для копирования файлов
function Copy-RemoteFile {
    param([string]$LocalPath, [string]$RemotePath)
    
    if (Test-Path $keyPath) {
        scp -i $keyPath -o StrictHostKeyChecking=no -r $LocalPath ${ServerUser}@${ServerIP}:${RemotePath} 2>&1 | Out-Null
    } else {
        scp -o StrictHostKeyChecking=no -r $LocalPath ${ServerUser}@${ServerIP}:${RemotePath} 2>&1 | Out-Null
    }
}

Write-Host "`nШаг 2: Установка Docker..." -ForegroundColor Yellow
Invoke-RemoteCommand "command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh)"

Write-Host "`nШаг 3: Установка Docker Compose..." -ForegroundColor Yellow
Invoke-RemoteCommand "command -v docker-compose >/dev/null 2>&1 || (apt update -qq && apt install -y docker-compose)"

Write-Host "`nШаг 4: Установка системных зависимостей..." -ForegroundColor Yellow
Invoke-RemoteCommand "apt update -qq && apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 wget git"

Write-Host "`nШаг 5: Создание директорий..." -ForegroundColor Yellow
Invoke-RemoteCommand "mkdir -p $RemoteDir/logs $RemoteDir/backups $RemoteDir/data/raw $RemoteDir/data/processed"

Write-Host "`nШаг 6: Копирование файлов..." -ForegroundColor Yellow
Push-Location $ProjectDir

$items = @("app", "ml", "tests", "docker-compose.prod.yml", "Dockerfile", "requirements.txt", "create_database.py", ".env.server")
foreach ($item in $items) {
    if (Test-Path $item) {
        Write-Host "  Копирование: $item" -ForegroundColor Cyan
        Copy-RemoteFile $item "$RemoteDir/$item"
    }
}

Get-ChildItem -Filter "*.sh" | ForEach-Object {
    Write-Host "  Копирование: $($_.Name)" -ForegroundColor Cyan
    Copy-RemoteFile $_.FullName "$RemoteDir/$($_.Name)"
}

Pop-Location

Write-Host "`nШаг 7: Настройка прав доступа..." -ForegroundColor Yellow
Invoke-RemoteCommand "cd $RemoteDir && chmod +x *.sh && mv .env.server .env 2>/dev/null || true"

Write-Host "`n=== Подготовка завершена ===" -ForegroundColor Green
Write-Host "`n⚠️  ВАЖНО: Настройте пароли в .env на сервере!" -ForegroundColor Yellow
Write-Host "`nСледующие команды:" -ForegroundColor Cyan
Write-Host "ssh ${ServerUser}@${ServerIP}" -ForegroundColor White
Write-Host "cd $RemoteDir" -ForegroundColor White
Write-Host "nano .env  # Замените CHANGE_THIS_TO_STRONG_PASSWORD на надежный пароль" -ForegroundColor White
Write-Host "docker-compose -f docker-compose.prod.yml up -d --build" -ForegroundColor White
Write-Host "sleep 60 && docker-compose exec backend python -m app.parser.init_db" -ForegroundColor White

