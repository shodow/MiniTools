param(
    [string]$Python = "C:\Users\ricar\miniconda3\envs\WinTools\python.exe"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path $PSScriptRoot).Path

if (-not (Test-Path $Python)) {
    throw "找不到 Python：$Python"
}

Push-Location $root
try {
    & $Python -m app.main
} finally {
    Pop-Location
}
