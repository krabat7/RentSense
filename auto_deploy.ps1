# Автоматическая настройка сервера
$ServerIP = "89.110.92.128"
$ServerUser = "root"
$Password = "D68v9kz3mL21a!FRZm23"
$RemoteDir = "/root/rentsense"
$ProjectDir = "F:\hw_hse\Diploma\RentSense"

Write-Host "=== Автоматическая настройка сервера ===" -ForegroundColor Green
Write-Host "Сервер: $ServerUser@$ServerIP" -ForegroundColor Cyan

# Создание команд для выполнения через SSH
$installCommands = @"
apt update -qq
apt install -y curl git
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
apt install -y docker-compose libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 wget
mkdir -p $RemoteDir/logs $RemoteDir/backups $RemoteDir/data/raw $RemoteDir/data/processed
"@

$installScript = "$env:TEMP\install_docker.sh"
$installCommands | Out-File -FilePath $installScript -Encoding ASCII -NoNewline

Write-Host "`nШаг 1: Установка Docker и зависимостей..." -ForegroundColor Yellow
Write-Host "Выполняется через SSH (потребуется ввод пароля: $Password)" -ForegroundColor Cyan

# Копирование скрипта установки
$scpCommand = "scp -o StrictHostKeyChecking=no `"$installScript`" ${ServerUser}@${ServerIP}:/tmp/install_docker.sh"
Write-Host "Копирование скрипта установки..." -ForegroundColor Cyan
Invoke-Expression $scpCommand

# Выполнение скрипта на сервере
Write-Host "Выполнение установки на сервере..." -ForegroundColor Cyan
Write-Host "Пароль для SSH: $Password" -ForegroundColor Yellow
$sshCommand = "ssh -o StrictHostKeyChecking=no ${ServerUser}@${ServerIP} 'bash /tmp/install_docker.sh && rm /tmp/install_docker.sh'"
Invoke-Expression $sshCommand

Write-Host "`nШаг 2: Копирование файлов проекта..." -ForegroundColor Yellow
Push-Location $ProjectDir

$items = @("app", "ml", "tests", "docker-compose.prod.yml", "Dockerfile", "requirements.txt", "create_database.py", ".env.server")
foreach ($item in $items) {
    if (Test-Path $item) {
        Write-Host "  Копирование: $item" -ForegroundColor Cyan
        scp -o StrictHostKeyChecking=no -r $item ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
    }
}

Get-ChildItem -Filter "*.sh" | ForEach-Object {
    Write-Host "  Копирование: $($_.Name)" -ForegroundColor Cyan
    scp -o StrictHostKeyChecking=no $_.FullName ${ServerUser}@${ServerIP}:${RemoteDir}/$($_.Name) 2>&1 | Out-Null
}

Pop-Location

Write-Host "`nШаг 3: Настройка прав доступа и .env..." -ForegroundColor Yellow
$setupCommands = @"
cd $RemoteDir
mv .env.server .env 2>/dev/null || true
chmod +x *.sh
"@

$setupScript = "$env:TEMP\setup_env.sh"
$setupCommands | Out-File -FilePath $setupScript -Encoding ASCII -NoNewline

scp -o StrictHostKeyChecking=no $setupScript ${ServerUser}@${ServerIP}:/tmp/setup_env.sh | Out-Null
Write-Host "Пароль для SSH: $Password" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no ${ServerUser}@${ServerIP} "bash /tmp/setup_env.sh && rm /tmp/setup_env.sh"

Remove-Item $installScript, $setupScript -ErrorAction SilentlyContinue

Write-Host "`n=== Подготовка завершена ===" -ForegroundColor Green
Write-Host "`n⚠️  ВАЖНО: Настройте пароли в .env на сервере!" -ForegroundColor Yellow
Write-Host "`nСледующие команды (выполните на сервере):" -ForegroundColor Cyan
Write-Host "ssh ${ServerUser}@${ServerIP}" -ForegroundColor White
Write-Host "cd $RemoteDir" -ForegroundColor White
Write-Host "nano .env" -ForegroundColor White
Write-Host "# Замените CHANGE_THIS_TO_STRONG_PASSWORD (2 раза) на надежный пароль" -ForegroundColor White
Write-Host "docker-compose -f docker-compose.prod.yml up -d --build" -ForegroundColor White
Write-Host "sleep 60" -ForegroundColor White
Write-Host "docker-compose -f docker-compose.prod.yml exec backend python create_database.py" -ForegroundColor White
Write-Host "docker-compose -f docker-compose.prod.yml exec backend python -m app.parser.init_db" -ForegroundColor White

