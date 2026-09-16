$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root 'backend\.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    throw 'Crie o ambiente virtual: python -m venv backend/.venv'
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Node.js e npm são necessários para compilar o frontend.'
}

Push-Location (Join-Path $root 'frontend')
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependências do frontend.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar o frontend.' }
} finally {
    Pop-Location
}

& $python -m pip install -r (Join-Path $root 'backend\requirements-desktop.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependências do desktop.' }

Push-Location $root
try {
    & $python -m PyInstaller --noconfirm --clean --windowed --onefile --name ProjectBoard `
        --paths backend `
        --add-data 'frontend/dist;frontend/dist' `
        --collect-all webview `
        desktop.py
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar o executável.' }
} finally {
    Pop-Location
}

Write-Host "Executável: $root\dist\ProjectBoard.exe"
