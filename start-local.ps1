$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$nodeDir = Join-Path $projectRoot "middleware_node"
$pythonDir = Join-Path $projectRoot "backend_python"
$frontendDir = Join-Path $projectRoot "frontend"
$npmCache = Join-Path $env:TEMP "dachuang-npm-cache"

function Start-ServiceWindow($title, $workingDirectory, $command) {
    Start-Process powershell.exe -WorkingDirectory $workingDirectory -ArgumentList @(
        "-NoExit",
        "-Command",
        "`$Host.UI.RawUI.WindowTitle = '$title'; $command"
    )
}

Write-Host "[1/5] Starting Hardhat local chain..." -ForegroundColor Cyan
Start-ServiceWindow "Dachuang - Hardhat 8545" $nodeDir "npx hardhat node"

Write-Host "[2/5] Waiting for RPC port 8545..." -ForegroundColor Cyan
for ($attempt = 1; $attempt -le 30; $attempt++) {
    if (Test-NetConnection 127.0.0.1 -Port 8545 -InformationLevel Quiet) { break }
    Start-Sleep -Seconds 1
    if ($attempt -eq 30) { throw "Hardhat node did not start within 30 seconds." }
}

Write-Host "[3/5] Installing dependencies and deploying contract..." -ForegroundColor Cyan
Push-Location $nodeDir
try {
    if (-not (Test-Path (Join-Path $nodeDir "node_modules"))) {
        npm install --legacy-peer-deps --cache $npmCache
    }
    npx hardhat run scripts/deploy.js --network localhost
}
finally {
    Pop-Location
}

Write-Host "[4/5] Starting Node, Python, and frontend windows..." -ForegroundColor Cyan
Start-ServiceWindow "Dachuang - Node 3000" $nodeDir "npm start"
Start-ServiceWindow "Dachuang - Python 5000" $pythonDir "python BloomBackend.py"
Start-ServiceWindow "Dachuang - Frontend 8080" $frontendDir "python -m http.server 8080"

Write-Host "[5/5] Ready: http://localhost:8080/index.html" -ForegroundColor Green
Write-Host "Admin: http://localhost:8080/admin.html" -ForegroundColor Green