$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pratesBundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $pratesBundledPython) {
    & $pratesBundledPython (Join-Path $PSScriptRoot 'start.py')
    exit $LASTEXITCODE
}
$pratesPython = Get-Command python -ErrorAction SilentlyContinue
if ($pratesPython) {
    & $pratesPython.Source (Join-Path $PSScriptRoot 'start.py')
    exit $LASTEXITCODE
}
$pratesPy = Get-Command py -ErrorAction SilentlyContinue
if ($pratesPy) {
    & $pratesPy.Source -3 (Join-Path $PSScriptRoot 'start.py')
    exit $LASTEXITCODE
}
Write-Host 'Python nao foi encontrado. Instale Python 3.11 ou superior e tente novamente.'
exit 1
