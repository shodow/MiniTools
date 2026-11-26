param(
    [string]$Python = "C:\Users\ricar\miniconda3\envs\WinTools\python.exe",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# 1) 先打包应用
if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot "build.ps1") -Python $Python
    if ($LASTEXITCODE -ne 0) { throw "应用打包失败" }
}

# 2) 找 Inno Setup 编译器
$isccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "没有找到 ISCC.exe，请先安装 Inno Setup 6：https://jrsoftware.org/isdl.php"
}

# 3) 中文向导语言包（Inno 官方仓库里的简体中文，仓库内已附带一份）
$langFile = Join-Path $root "build\installer\ChineseSimplified.isl"
if (-not (Test-Path $langFile)) {
    $url = "https://raw.githubusercontent.com/jrsoftware/issrc/refs/heads/main/Files/Languages/ChineseSimplified.isl"
    try {
        Invoke-WebRequest -Uri $url -OutFile $langFile -TimeoutSec 30
        Write-Host "==> 已下载简体中文语言包" -ForegroundColor Cyan
    } catch {
        Write-Warning "中文语言包下载失败，回退为英文向导：$($_.Exception.Message)"
        $default = Join-Path (Split-Path $iscc) "Default.isl"
        if (Test-Path $default) { Copy-Item $default $langFile -Force }
    }
}

# 4) 编译安装包
Write-Host "==> 编译安装包" -ForegroundColor Cyan
& $iscc (Join-Path $root "build\installer\MiniTools.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup 编译失败" }

Get-ChildItem (Join-Path $root "dist") -Filter "MiniTools-Setup-*.exe" |
    ForEach-Object { Write-Host ("==> 安装包：{0}（{1:N1} MB）" -f $_.FullName, ($_.Length / 1MB)) -ForegroundColor Green }

# 5) 把最新安装包复制到“下载”目录
#    原因：在受限环境（沙箱 / 受控目录）里，从项目目录直接运行安装包会被拒绝写入
#    %TEMP% 与 Programs 目录，表现为“错误 5: 拒绝访问”。复制出去再运行即可。
$setup = Get-ChildItem (Join-Path $root "dist") -Filter "MiniTools-Setup-*.exe" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($setup) {
    $downloads = Join-Path $env:USERPROFILE "Downloads"
    if (-not (Test-Path $downloads)) { $downloads = $env:USERPROFILE }
    $target = Join-Path $downloads $setup.Name
    try {
        Copy-Item $setup.FullName $target -Force
        Write-Host "==> 已复制到：$target" -ForegroundColor Green
        Write-Host "    请从该位置双击运行（未签名程序首次运行会有 SmartScreen 提示：更多信息 → 仍要运行）" -ForegroundColor Yellow
    } catch {
        Write-Warning "复制到 Downloads 失败，请手动复制后再运行：$($_.Exception.Message)"
    }
}
