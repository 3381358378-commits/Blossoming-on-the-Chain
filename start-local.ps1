$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$nodeDir = Join-Path $projectRoot "middleware_node"
$pythonDir = Join-Path $projectRoot "backend_python"
$frontendDir = Join-Path $projectRoot "frontend"
$npmCache = Join-Path $env:TEMP "dachuang-npm-cache"

function Start-ServiceWindow($title, $workingDirectory, $command) {
    Start-Process powershell.exe -ArgumentList @("-NoExit","-NoProfile","-ExecutionPolicy","Bypass","-Command","cd `"$workingDirectory`"; `$Host.UI.RawUI.WindowTitle=`"$title`"; $command")
    Start-Sleep -Milliseconds 500
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dachuang Local Dev Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill any existing Hardhat process on port 8545
Write-Host "[1/6] Checking port 8545..." -ForegroundColor Cyan
$portProcess = Get-NetTCPConnection -LocalPort 8545 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($portProcess) {
    Write-Host "  Port 8545 occupied by PID $portProcess, stopping..." -ForegroundColor Yellow
    Stop-Process -Id $portProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Step 2: Start Hardhat
Write-Host "[2/6] Starting Hardhat local chain..." -ForegroundColor Cyan
Start-ServiceWindow "Hardhat-8545" $nodeDir "npx hardhat node"

Write-Host "  Waiting for RPC port 8545..." -ForegroundColor DarkGray
for ($attempt = 1; $attempt -le 30; $attempt++) {
    if (Test-NetConnection 127.0.0.1 -Port 8545 -InformationLevel Quiet -WarningAction SilentlyContinue) {
        Write-Host "  Port 8545 ready!" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
    if ($attempt -eq 30) {
        Write-Host "ERROR: Hardhat did not start within 30 seconds." -ForegroundColor Red
        exit 1
    }
}

# Step 3: Deploy contract
Write-Host "[3/6] Deploying contract..." -ForegroundColor Cyan
Push-Location $nodeDir
try {
    if (-not (Test-Path (Join-Path $nodeDir "node_modules"))) {
        npm install --legacy-peer-deps --cache $npmCache
    }
    node node_modules/hardhat/internal/cli/cli.js run scripts/deploy.js --network localhost
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Contract deployment failed!" -ForegroundColor Red
        exit 1
    }
}
finally {
    Pop-Location
}

# Step 4: Check .env
$envFile = Join-Path $nodeDir ".env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "CONTRACT_ADDRESS=") {
        Write-Host "[4/6] .env OK - contract address configured." -ForegroundColor Green
    }
    else {
        Write-Host "[4/6] WARNING: .env missing CONTRACT_ADDRESS!" -ForegroundColor Red
    }
}
else {
    Write-Host "[4/6] WARNING: .env file not found!" -ForegroundColor Red
}

# Step 5: Start services
Write-Host "[5/6] Starting Node, Python, and frontend..." -ForegroundColor Cyan
Start-ServiceWindow "Node-3000" $nodeDir "node server.js"
Start-ServiceWindow "Python-5000" $pythonDir "python BloomBackend.py"
Start-ServiceWindow "Frontend-8080" $frontendDir "python -m http.server 8080"

# Step 6: Wait and verify
Write-Host "[6/6] Waiting for services..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

$allOk = $true
foreach ($port in @(3000, 5000, 8080)) {
    $ready = Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
    $status = if ($ready) { "OK" } else { "NOT READY" }
    $color = if ($ready) { "Green" } else { "Red" }
    Write-Host "  Port $port : $status" -ForegroundColor $color
    if (-not $ready) { $allOk = $false }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allOk) {
    Write-Host "  All services ready!" -ForegroundColor Green
    Write-Host "  App:   http://localhost:8080/index.html" -ForegroundColor White
    Write-Host "  Admin: http://localhost:8080/admin.html" -ForegroundColor White
}
else {
    Write-Host "  Some services may not be ready." -ForegroundColor Yellow
    Write-Host "  Check the popup windows for errors." -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
