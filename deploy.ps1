# Auto deployment script
$ServerIP = "89.110.92.128"
$ServerUser = "root"
$Password = "D68v9kz3mL21a!FRZm23"
$RemoteDir = "/root/rentsense"
$ProjectDir = "F:\hw_hse\Diploma\RentSense"

Write-Host "=== Auto deployment ===" -ForegroundColor Green
Write-Host "Server: $ServerUser@$ServerIP" -ForegroundColor Cyan
Write-Host "Password will be requested for each SSH connection" -ForegroundColor Yellow
Write-Host "Password: $Password" -ForegroundColor Cyan

$installScript = @"
apt update -qq && apt install -y curl git
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
apt install -y docker-compose libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 wget
mkdir -p $RemoteDir/logs $RemoteDir/backups $RemoteDir/data/raw $RemoteDir/data/processed
"@

$scriptFile = "$env:TEMP\install.sh"
$installScript | Out-File -FilePath $scriptFile -Encoding ASCII

Write-Host "`nStep 1: Installing Docker..." -ForegroundColor Yellow
Write-Host "Copying install script..." -ForegroundColor Cyan
scp -o StrictHostKeyChecking=no $scriptFile ${ServerUser}@${ServerIP}:/tmp/install.sh

Write-Host "Executing install script..." -ForegroundColor Cyan
Write-Host "Enter password when prompted: $Password" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no ${ServerUser}@${ServerIP} "bash /tmp/install.sh && rm /tmp/install.sh"

Write-Host "`nStep 2: Copying project files..." -ForegroundColor Yellow
Push-Location $ProjectDir

$files = @("app", "ml", "tests", "docker-compose.prod.yml", "Dockerfile", "requirements.txt", "create_database.py", ".env.server")
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  Copying: $file" -ForegroundColor Cyan
        scp -o StrictHostKeyChecking=no -r $file ${ServerUser}@${ServerIP}:${RemoteDir}/ 2>&1 | Out-Null
    }
}

Get-ChildItem -Filter "*.sh" | ForEach-Object {
    Write-Host "  Copying: $($_.Name)" -ForegroundColor Cyan
    scp -o StrictHostKeyChecking=no $_.FullName ${ServerUser}@${ServerIP}:${RemoteDir}/$($_.Name) 2>&1 | Out-Null
}

Pop-Location

Write-Host "`nStep 3: Setting up permissions..." -ForegroundColor Yellow
$setupCmd = "cd $RemoteDir && mv .env.server .env 2>/dev/null || true && chmod +x *.sh"
ssh -o StrictHostKeyChecking=no ${ServerUser}@${ServerIP} $setupCmd

Remove-Item $scriptFile -ErrorAction SilentlyContinue

Write-Host "`n=== Deployment completed ===" -ForegroundColor Green
Write-Host "`nIMPORTANT: Configure passwords in .env on server!" -ForegroundColor Yellow
Write-Host "`nNext steps (execute on server):" -ForegroundColor Cyan
Write-Host "ssh ${ServerUser}@${ServerIP}" -ForegroundColor White
Write-Host "cd $RemoteDir" -ForegroundColor White
Write-Host "nano .env" -ForegroundColor White
Write-Host "# Replace CHANGE_THIS_TO_STRONG_PASSWORD with strong password (2 times)" -ForegroundColor Gray
Write-Host "docker-compose -f docker-compose.prod.yml up -d --build" -ForegroundColor White
Write-Host "sleep 60" -ForegroundColor White
Write-Host "docker-compose -f docker-compose.prod.yml exec backend python create_database.py" -ForegroundColor White
Write-Host "docker-compose -f docker-compose.prod.yml exec backend python -m app.parser.init_db" -ForegroundColor White

