<#
.SYNOPSIS
    用省资源的参数启动模拟器，并在空闲内存不足时给出警告。

.EXAMPLE
    .\run_emulator.ps1                # 有窗口，方便手点
    .\run_emulator.ps1 -Headless      # 无窗口，只配合 adb 截图/装包
    .\run_emulator.ps1 -Gpu swiftshader_indirect
#>
param(
    [string]$Avd = "Medium_Phone_API_36",
    [switch]$Headless,
    [ValidateSet("auto", "host", "swiftshader_indirect")]
    [string]$Gpu = "host",
    [int]$MemoryMb = 1536,
    [int]$Cores = 2
)

$ErrorActionPreference = "Stop"
$sdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$emulator = Join-Path $sdk "emulator\emulator.exe"
if (-not (Test-Path $emulator)) { throw "找不到模拟器：$emulator" }

$freeMb = [int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1KB)
Write-Host ("当前空闲内存：{0} MB" -f $freeMb) -ForegroundColor Cyan
if ($freeMb -lt 2500) {
    Write-Warning "空闲内存不足 2.5 GB，模拟器很可能会把机器拖死。建议先关掉 Android Studio / 浏览器。"
}

$args = @(
    "-avd", $Avd,
    "-memory", "$MemoryMb",
    "-cores", "$Cores",
    "-gpu", $Gpu,
    "-no-audio",
    "-no-boot-anim",
    "-netdelay", "none",
    "-netspeed", "full"
)
if ($Headless) { $args += "-no-window" }

Write-Host ("启动：emulator {0}" -f ($args -join " ")) -ForegroundColor Green
& $emulator @args
