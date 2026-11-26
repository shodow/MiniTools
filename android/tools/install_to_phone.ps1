<#
.SYNOPSIS
    一键装到真机并启动（可选截图）。本机不用模拟器，这是唯一验证通道。

.EXAMPLE
    .\install_to_phone.ps1
    .\install_to_phone.ps1 -Screenshot
#>
param(
    [string]$Apk = (Join-Path $PSScriptRoot "..\app\build\outputs\apk\debug\app-debug.apk"),
    [string]$Package = "com.ricar.minitools",
    [string]$Activity = "com.ricar.minitools/.MainActivity",
    [switch]$Screenshot,
    [string]$ShotPath = (Join-Path $PSScriptRoot "..\shots\screen.png")
)

$ErrorActionPreference = "Stop"
$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { throw "找不到 adb：$adb" }
if (-not (Test-Path $Apk)) { throw "找不到 APK：$Apk（先运行 gradlew.bat assembleDebug）" }

$devices = (& $adb devices) | Select-Object -Skip 1 | Where-Object { $_ -match '\sdevice$' }
if (-not $devices) {
    throw "没有检测到设备。请开启「开发者选项 → USB 调试」，插线后重新运行；或先执行 adb pair / adb connect 走无线调试。"
}
Write-Host ("设备：{0}" -f (($devices | ForEach-Object { ($_ -split '\s+')[0] }) -join ', ')) -ForegroundColor Cyan

Write-Host "==> 安装 APK" -ForegroundColor Cyan
& $adb install -r $Apk
if ($LASTEXITCODE -ne 0) { throw "安装失败（exit $LASTEXITCODE）" }

Write-Host "==> 启动应用" -ForegroundColor Cyan
& $adb shell am start -n $Activity | Out-Null

if ($Screenshot) {
    Start-Sleep -Seconds 3
    $dir = Split-Path $ShotPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    # 用 cmd 的重定向，避免 PowerShell 把二进制截图写坏
    & cmd /c "`"$adb`" exec-out screencap -p > `"$ShotPath`""
    if (Test-Path $ShotPath) {
        Write-Host ("==> 截图：{0}（{1:N0} KB）" -f $ShotPath, ((Get-Item $ShotPath).Length / 1KB)) -ForegroundColor Green
    }
}
