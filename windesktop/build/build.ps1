param(
    [string]$Python = "C:\Users\ricar\miniconda3\envs\WinTools\python.exe"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not (Test-Path $Python)) {
    throw "找不到 Python：$Python（用 -Python 指定解释器路径）"
}

Write-Host "==> 生成应用图标" -ForegroundColor Cyan
& $Python (Join-Path $root "build\make_icon.py")
if ($LASTEXITCODE -ne 0) { throw "图标生成失败" }

Write-Host "==> PyInstaller 打包（onedir）" -ForegroundColor Cyan
& $Python -m PyInstaller `
    --noconfirm --clean `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build\work") `
    (Join-Path $root "build\MiniTools.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }

$exe = Join-Path $root "dist\MiniTools\MiniTools.exe"
if (-not (Test-Path $exe)) { throw "打包完成但没找到 $exe" }

$size = (Get-ChildItem (Join-Path $root "dist\MiniTools") -Recurse -File |
    Measure-Object -Property Length -Sum).Sum
Write-Host ("==> 完成：{0}（目录 {1:N1} MB）" -f $exe, ($size / 1MB)) -ForegroundColor Green
