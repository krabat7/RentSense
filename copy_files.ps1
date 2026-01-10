# Скрипт для копирования файлов на сервер
# Пароль будет запрашиваться для каждого SCP вызова

$ServerIP = "89.110.92.128"
$ServerUser = "root"
$RemoteDir = "/root/rentsense"
$ProjectDir = "F:\hw_hse\Diploma\RentSense"

Write-Host "=== Копирование файлов на сервер ===" -ForegroundColor Green
Write-Host "Сервер: $ServerUser@$ServerIP" -ForegroundColor Cyan
Write-Host "Пароль будет запрошен для каждого файла" -ForegroundColor Yellow
Write-Host "Пароль: D68v9kz3mL21a!FRZm23" -ForegroundColor Cyan
Write-Host ""

Push-Location $ProjectDir

$files = @(
    "app",
    "ml", 
    "tests",
    "docker-compose.prod.yml",
    "Dockerfile",
    "requirements.txt",
    "create_database.py",
    ".env.server"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "Копирование: $file" -ForegroundColor Yellow
        Write-Host "Введите пароль: D68v9kz3mL21a!FRZm23" -ForegroundColor Cyan
        scp -r $file ${ServerUser}@${ServerIP}:${RemoteDir}/
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK" -ForegroundColor Green
        } else {
            Write-Host "  FAILED" -ForegroundColor Red
        }
        Write-Host ""
    }
}

# Копирование скриптов
Get-ChildItem -Filter "*.sh" | ForEach-Object {
    Write-Host "Копирование: $($_.Name)" -ForegroundColor Yellow
    Write-Host "Введите пароль: D68v9kz3mL21a!FRZm23" -ForegroundColor Cyan
    scp $_.FullName ${ServerUser}@${ServerIP}:${RemoteDir}/$($_.Name)
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK" -ForegroundColor Green
    } else {
        Write-Host "  FAILED" -ForegroundColor Red
    }
    Write-Host ""
}

Pop-Location

Write-Host "=== Копирование завершено ===" -ForegroundColor Green
Write-Host ""
Write-Host "Теперь на сервере выполните:" -ForegroundColor Cyan
Write-Host "cd $RemoteDir" -ForegroundColor White
Write-Host "mv .env.server .env" -ForegroundColor White
Write-Host "nano .env  # Замените CHANGE_THIS_TO_STRONG_PASSWORD" -ForegroundColor White

