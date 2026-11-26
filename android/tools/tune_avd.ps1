<#
.SYNOPSIS
    把现有 AVD 调成"低配可跑"：降低分辨率、限制内存、选 GPU 模式。

.DESCRIPTION
    直接改 config.ini。改之前会按约定备份成 config.ini.<yyyyMMdd-HHmmss>.bak。
    N100 + 8 GB 这类机器上，1080x2400 @420dpi 是主要瓶颈，降到 720x1280 @280dpi
    能显著减少渲染和内存压力。

.EXAMPLE
    .\tune_avd.ps1                      # 默认 720x1280 + host GPU
    .\tune_avd.ps1 -Gpu swiftshader_indirect
    .\tune_avd.ps1 -Avd Medium_Phone_API_36 -Width 540 -Height 960
#>
param(
    [string]$Avd = "Medium_Phone_API_36",
    [int]$Width = 720,
    [int]$Height = 1280,
    [int]$Density = 280,
    [int]$RamMb = 1536,
    [int]$HeapMb = 256,
    [ValidateSet("host", "swiftshader_indirect", "off")]
    [string]$Gpu = "host"
)

$ErrorActionPreference = "Stop"
$avdRoot = Join-Path $env:USERPROFILE ".android\avd"
$ini = Join-Path $avdRoot "$Avd.ini"
if (-not (Test-Path $ini)) { throw "找不到 AVD：$Avd（$ini）" }

$avdPath = (Get-Content $ini | Where-Object { $_ -match '^path=' }) -replace '^path=', ''
$config = Join-Path $avdPath "config.ini"
if (-not (Test-Path $config)) { throw "找不到 config.ini：$config" }

$backup = "$config.$(Get-Date -Format 'yyyyMMdd-HHmmss').bak"
Copy-Item $config $backup
Write-Host "已备份：$backup" -ForegroundColor Cyan

$values = [ordered]@{
    "hw.lcd.width"   = "$Width"
    "hw.lcd.height"  = "$Height"
    "hw.lcd.density" = "$Density"
    "skin.name"      = "$($Width)x$($Height)"
    "skin.path"      = "$($Width)x$($Height)"
    "hw.ramSize"     = "$RamMb"
    "vm.heapSize"    = "$HeapMb"
    "hw.cpu.ncore"   = "2"
    "hw.gpu.enabled" = if ($Gpu -eq "off") { "no" } else { "yes" }
    "hw.gpu.mode"    = $Gpu
}

$lines = Get-Content $config
$seen = @{}
$out = foreach ($line in $lines) {
    $matched = $false
    foreach ($key in $values.Keys) {
        if ($line -match "^\s*$([regex]::Escape($key))\s*=") {
            $seen[$key] = $true
            $matched = $true
            "$key = $($values[$key])"
        }
    }
    if (-not $matched) { $line }
}
foreach ($key in $values.Keys) {
    if (-not $seen.ContainsKey($key)) { $out += "$key = $($values[$key])" }
}

Set-Content -Path $config -Value $out -Encoding UTF8
Write-Host "已更新 $config" -ForegroundColor Green
Write-Host ("  {0}x{1} @{2}dpi, RAM {3} MB, heap {4} MB, GPU {5}" -f $Width, $Height, $Density, $RamMb, $HeapMb, $Gpu) -ForegroundColor Green
Write-Host "提示：改完先在 AVD Manager 里 Cold Boot 一次，之后用 Quick Boot 就会快很多。" -ForegroundColor Yellow
