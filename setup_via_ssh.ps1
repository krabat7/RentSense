# Автоматическая настройка сервера (упрощенная версия)
param(
    [Parameter(Mandatory=$true)]
    [string]$Password,
    
    [Parameter(Mandatory=$false)]
    [string]$ServerIP = "89.110.92.128"
)

$ServerUser = "root"
$ProjectDir = "F:\hw_hse\Diploma\RentSense"
$RemoteDir = "/root/rentsense"

Write-Host "=== Автоматическая настройка сервера ===" -ForegroundColor Green
Write-Host "Сервер: $ServerUser@$ServerIP" -ForegroundColor Cyan

# Функция для выполнения SSH команд (с использованием echo для пароля)
function Invoke-SSHCommand {
    param([string]$Command)
    
    # Используем sshpass через WSL если доступно, иначе создаем временный expect скрипт
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        $sshpassCmd = "echo '$Password' | sshpass -p '$Password' ssh -o StrictHostKeyChecking=no ${ServerUser}@${ServerIP} '$Command'"
        wsl bash -c $sshpassCmd
    } else {
        # Альтернатива: использовать Plink (PuTTY) если установлен
        if (Get-Command plink -ErrorAction SilentlyContinue) {
            $commandFile = "$env:TEMP\ssh_command.txt"
            $Command | Out-File -FilePath $commandFile -Encoding ASCII
            echo y | plink -ssh ${ServerUser}@${ServerIP} -pw $Password -m $commandFile 2>&1
            Remove-Item $commandFile -ErrorAction SilentlyContinue
        } else {
            Write-Host "Требуется WSL (для sshpass) или PuTTY (для plink)" -ForegroundColor Yellow
            Write-Host "Выполните команду вручную: ssh $ServerUser@$ServerIP" -ForegroundColor Yellow
            return $null
        }
    }
}

# Проверка доступности ssh
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Host "SSH не найден. Используйте WSL или установите OpenSSH для Windows" -ForegroundColor Red
    exit 1
}

Write-Host "`nПроверка подключения..." -ForegroundColor Yellow
$testConnection = ssh -o StrictHostKeyChecking=no -o BatchMode=yes ${ServerUser}@${ServerIP} "echo 'connected'" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Требуется первый вход. Подключитесь вручную один раз:" -ForegroundColor Yellow
    Write-Host "ssh $ServerUser@$ServerIP" -ForegroundColor White
    Write-Host "После этого запустите скрипт снова" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nШаг 1: Установка Docker и зависимостей..." -ForegroundColor Yellow
ssh ${ServerUser}@${ServerIP} @"
apt update -qq && apt install -y curl git
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
apt install -y docker-compose libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
mkdir -p $RemoteDir/logs $RemoteDir/backups $RemoteDir/data/raw $RemoteDir/data/processed
"@

Write-Host "`nШаг 2: Копирование файлов..." -ForegroundColor Yellow
Push-Location $ProjectDir

# Копирование основных файлов
scp -r app ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
scp -r ml ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
scp -r tests ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
scp docker-compose.prod.yml ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
scp Dockerfile ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
scp requirements.txt ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
scp create_database.py ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
scp .env.server ${ServerUser}@${ServerIP}:${RemoteDir}/.env 2>&1 | Out-Null

# Копирование скриптов
Get-ChildItem -Filter "*.sh" | ForEach-Object {
    scp $_.FullName ${ServerUser}@${ServerIP}:${RemoteDir}/$($_.Name) 2>&1 | Out-Null
}

Pop-Location
Write-Host "✓ Файлы скопированы" -ForegroundColor Green

Write-Host "`n=== Подготовка завершена ===" -ForegroundColor Green
Write-Host "`n⚠️  ВАЖНО: Настройте пароли в .env на сервере!" -ForegroundColor Yellow
Write-Host "`nВыполните на сервере:" -ForegroundColor Cyan
Write-Host "ssh $ServerUser@$ServerIP" -ForegroundColor White
Write-Host "cd $RemoteDir" -ForegroundColor White
Write-Host "nano .env  # Замените CHANGE_THIS_TO_STRONG_PASSWORD" -ForegroundColor White
Write-Host "docker-compose -f docker-compose.prod.yml up -d --build" -ForegroundColor White
Write-Host "sleep 60 && docker-compose exec backend python -m app.parser.init_db" -ForegroundColor White

