# OllaCode PowerShell launcher
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Main = Join-Path $Root "main.py"

if (Test-Path $VenvPython) {
    & $VenvPython $Main @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $Main @args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py $Main @args
} else {
    Write-Error "Python not found. Please install Python 3.10+ from https://python.org"
    exit 1
}

exit $LASTEXITCODE
