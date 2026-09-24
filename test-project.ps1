$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root 'backend\.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    throw 'Crie o ambiente virtual do backend antes de executar os testes.'
}
$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
$bundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$node = if ($nodeCommand) { $nodeCommand.Source } elseif (Test-Path $bundledNode) { $bundledNode } else { $null }
if (-not $node) { throw 'Node.js é necessário para executar os testes do frontend.' }

Write-Host 'Backend'
Push-Location (Join-Path $root 'backend')
try {
    & $python -m unittest discover -s tests -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Os testes do backend falharam.' }
} finally {
    Pop-Location
}

Write-Host 'Frontend'
Push-Location (Join-Path $root 'frontend')
try {
    & $node 'node_modules\typescript\bin\tsc' --noEmit
    if ($LASTEXITCODE -ne 0) { throw 'A verificação do TypeScript falhou.' }
    & $node 'node_modules\typescript\bin\tsc' 'src\duration.ts' 'src\report.ts' --target ES2022 --module ES2022 --skipLibCheck --outDir .test-build
    if ($LASTEXITCODE -ne 0) { throw 'A preparação dos testes de duração falhou.' }
    & $node 'tests\duration.test.mjs'
    if ($LASTEXITCODE -ne 0) { throw 'Os testes do frontend falharam.' }
} finally {
    Pop-Location
}

Write-Host 'Todos os testes passaram.'
