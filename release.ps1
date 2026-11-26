#requires -Version 7.0
<#
.SYNOPSIS
    一条命令发布 MiniTools：同步版本号 → 打包 exe/apk → 提交打 tag → 推送 → 建 GitHub Release 并上传发行物。

.EXAMPLE
    .\release.ps1 -Version 2.1.0

.EXAMPLE
    .\release.ps1 -Version 2.1.0 -Title "MiniTools 2.1.0：新增批量重命名" -NotesFile .\notes.md

.EXAMPLE
    .\release.ps1 -Version 2.1.0 -DryRun     # 只做检查并打印计划，不改文件、不打包、不推送
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,

    [string]$Title,
    [string]$NotesFile,

    # 不传则取当前 versionCode + 1
    [int]$VersionCode = 0,

    [string]$Python = 'C:\Users\ricar\miniconda3\envs\WinTools\python.exe',
    [string]$JavaHome = 'C:\Program Files\Android\Android Studio\jbr',

    [switch]$SkipBuild,
    [switch]$Prerelease,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Write-Step { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Ok { param([string]$Message) Write-Host "OK  $Message" -ForegroundColor Green }
function Write-Warn2 { param([string]$Message) Write-Host "!!  $Message" -ForegroundColor Yellow }

function Invoke-Checked {
    param([string]$Label, [scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Label 失败（exit=$LASTEXITCODE）" }
}

function Get-GitHubToken {
    $env:GIT_TERMINAL_PROMPT = '0'
    $env:GCM_INTERACTIVE = 'Never'
    $lines = "protocol=https`nhost=github.com`n`n" | git credential fill 2>&1
    $line = $lines | Where-Object { $_ -match '^password=' } | Select-Object -First 1
    if (-not $line) { throw '取不到 GitHub 凭据：请先在本机登录过 GitHub（Git Credential Manager）或设置 GH_TOKEN' }
    return ($line -replace '^password=', '')
}

function Get-RepoSlug {
    $url = (git -C $root remote get-url origin).Trim()
    if ($url -match 'github\.com[:/](?<owner>[^/]+)/(?<repo>[^/]+?)(\.git)?$') {
        return "$($Matches.owner)/$($Matches.repo)"
    }
    throw "无法从 origin 解析 owner/repo：$url"
}

function Get-FileSha256 {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower()
}

function Get-GradleValue {
    param([string]$Pattern)
    $text = Get-Content -LiteralPath $script:gradlePath -Raw
    if ($text -match $Pattern) { return $Matches[1] }
    throw "在 android/app/build.gradle.kts 里找不到 $Pattern"
}

# ---------------------------------------------------------------- 路径与前置检查

$issPath = Join-Path $root 'windesktop\build\installer\MiniTools.iss'
$gradlePath = Join-Path $root 'android\app\build.gradle.kts'
$buildPs1 = Join-Path $root 'windesktop\build\build.ps1'
$installerPs1 = Join-Path $root 'windesktop\build\build_installer.ps1'
$gradlew = Join-Path $root 'android\gradlew.bat'

foreach ($p in @($issPath, $gradlePath, $buildPs1, $installerPs1, $gradlew)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "缺少文件：$p" }
}

$tag = "v$Version"
$title = if ($Title) { $Title } else { "MiniTools $Version" }
$exePath = Join-Path $root "windesktop\dist\MiniTools-Setup-$Version.exe"
$apkPath = Join-Path $root "android\dist\MiniTools-$Version-release.apk"

Write-Step "检查 git 状态"
if (-not (git -C $root rev-parse --is-inside-work-tree 2>$null)) { throw '当前目录不是 git 仓库' }
$branch = (git -C $root rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne 'main') { throw "当前分支是 $branch，发版要求 main" }
$dirty = git -C $root status --porcelain
if ($dirty) {
    throw ("工作区不干净，先提交或还原：`n" + ($dirty -join "`n"))
}
if ((git -C $root tag -l $tag)) { throw "本地已存在标签 $tag" }
if ((git -C $root ls-remote --tags origin "refs/tags/$tag")) { throw "远程已存在标签 $tag" }

$slug = Get-RepoSlug
$currentIssVersion = (Select-String -LiteralPath $issPath -Pattern '^#define MyAppVersion "([\d\.]+)"' | Select-Object -First 1).Matches.Groups[1].Value
$currentGradleVersion = Get-GradleValue 'versionName\s*=\s*"([\d\.]+)"'
$currentCode = [int](Get-GradleValue 'versionCode\s*=\s*(\d+)')
if ($VersionCode -le 0) { $VersionCode = $currentCode + 1 }

Write-Host ("    仓库      : " + $slug)
Write-Host ("    当前版本  : iss=$currentIssVersion gradle=$currentGradleVersion versionCode=$currentCode")
Write-Host ("    目标版本  : $Version  versionCode=$VersionCode")
Write-Host ("    标签      : $tag")

if (-not $SkipBuild) {
    if (-not (Test-Path -LiteralPath $Python)) { throw "找不到 Python：$Python" }
    if (-not (Test-Path -LiteralPath (Join-Path $JavaHome 'bin\java.exe'))) { throw "找不到 JDK：$JavaHome" }
}

if ($DryRun) {
    Write-Warn2 'DryRun：以下动作不会真正执行'
    Write-Host "  1. 改 $issPath → MyAppVersion `"$Version`""
    Write-Host "  2. 改 $gradlePath → versionName `"$Version`"，versionCode $VersionCode"
    Write-Host "  3. 打包 windesktop（PyInstaller + Inno Setup）→ $exePath"
    Write-Host "  4. 打包 android（assembleRelease）→ $apkPath"
    Write-Host "  5. commit + tag $tag + push origin main/tag"
    Write-Host "  6. 建 GitHub Release（$slug）并上传两个发行物"
    return
}

# ---------------------------------------------------------------- 1. 同步版本号

Write-Step "同步版本号"
$issText = Get-Content -LiteralPath $issPath -Raw
$issText = [regex]::Replace($issText, '(?m)^#define MyAppVersion "[\d\.]+"', "#define MyAppVersion `"$Version`"")
Set-Content -LiteralPath $issPath -Value $issText -NoNewline -Encoding utf8

$gradleText = Get-Content -LiteralPath $gradlePath -Raw
$gradleText = [regex]::Replace($gradleText, '(?m)^(\s*)versionCode = \d+', "`${1}versionCode = $VersionCode")
$gradleText = [regex]::Replace($gradleText, '(?m)^(\s*)versionName = "[\d\.]+"', "`${1}versionName = `"$Version`"")
Set-Content -LiteralPath $gradlePath -Value $gradleText -NoNewline -Encoding utf8

Write-Ok "MyAppVersion = $Version；versionName = $Version；versionCode = $VersionCode"

# ---------------------------------------------------------------- 2. 打包

if ($SkipBuild) {
    Write-Warn2 '跳过打包，直接使用已有发行物'
    foreach ($p in @($exePath, $apkPath)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "缺少发行物：$p" }
    }
} else {
    Write-Step '打包 Windows 安装包'
    Invoke-Checked 'PyInstaller' { & $buildPs1 -Python $Python }
    Invoke-Checked 'Inno Setup' { & $installerPs1 -Python $Python -SkipBuild }
    if (-not (Test-Path -LiteralPath $exePath)) { throw "打包完成但没找到 $exePath" }
    Write-Ok "生成 $exePath"

    Write-Step '打包 Android release APK'
    $env:JAVA_HOME = $JavaHome
    Push-Location (Join-Path $root 'android')
    try {
        Invoke-Checked 'gradlew assembleRelease' { & $gradlew assembleRelease --console=plain }
    } finally {
        Pop-Location
    }
    $builtApk = Join-Path $root 'android\app\build\outputs\apk\release\app-release.apk'
    if (-not (Test-Path -LiteralPath $builtApk)) { throw "打包完成但没找到 $builtApk" }
    New-Item -ItemType Directory -Path (Split-Path $apkPath) -Force | Out-Null
    Copy-Item -LiteralPath $builtApk -Destination $apkPath -Force
    Write-Ok "生成 $apkPath"
}

$exeHash = Get-FileSha256 $exePath
$apkHash = Get-FileSha256 $apkPath

# ---------------------------------------------------------------- 3. 提交、打标签、推送

Write-Step '提交版本号并打标签'
git -C $root add -- $issPath $gradlePath
Invoke-Checked 'git commit' { git -C $root commit -m "chore(release): $tag" }
Invoke-Checked 'git tag' { git -C $root tag -a $tag -m "MiniTools $Version" }
Invoke-Checked 'git push main' { git -C $root push origin main }
Invoke-Checked 'git push tag' { git -C $root push origin $tag }
Write-Ok "已推送 main 与 $tag"

# ---------------------------------------------------------------- 4. 建 Release 并上传

Write-Step '创建 GitHub Release'
if ($NotesFile) {
    if (-not (Test-Path -LiteralPath $NotesFile)) { throw "找不到说明文件：$NotesFile" }
    $notes = Get-Content -LiteralPath $NotesFile -Raw
    $notes = $notes.Replace('{{VERSION}}', $Version).Replace('{{EXE}}', (Split-Path $exePath -Leaf)).Replace('{{APK}}', (Split-Path $apkPath -Leaf)).Replace('{{EXE_SHA256}}', $exeHash).Replace('{{APK_SHA256}}', $apkHash)
} else {
    $notes = @"
## MiniTools $Version

跨平台小工具集合，Windows 桌面版与 Android 客户端功能与参数保持一致。

### 功能

- **PDF 转图片**：每页导出 PNG / JPG，文件名固定 ``原文件名_页码``（默认补 3 位），支持整文件夹批量、页面范围（``1-5,8,10-``）、渲染 DPI 可调
- **图片加水印**：平铺文字水印，支持中文，透明度 / 字号 / 间距 / 角度可调，右侧实时预览
- 双端统一参数：透明度 75%、字号 20 px、间距 60 px、角度 45°、PDF 渲染 200 DPI

### 下载

| 平台 | 文件 | 说明 |
|---|---|---|
| Windows 10/11 | ``$(Split-Path $exePath -Leaf)`` | Inno Setup 安装包，按当前用户安装，无需管理员权限 |
| Android 7.0+ (API 24) | ``$(Split-Path $apkPath -Leaf)`` | 已签名 release 包 |

### 校验值

``````
SHA256  $(Split-Path $exePath -Leaf)  $exeHash
SHA256  $(Split-Path $apkPath -Leaf)  $apkHash
``````

### 安装提示

- Windows 安装包未做代码签名，首次运行会出现 SmartScreen 提示，点「更多信息 → 仍要运行」。
- 请先把安装包复制到桌面或「下载」目录再运行，从受控目录直接双击可能报「错误 5: 拒绝访问」。
- Android 包用本仓库自签名密钥签名；装过 debug 版需先卸载（签名不同，卸载会清数据）。
"@
}

$token = Get-GitHubToken
$headers = @{
    Authorization         = "Bearer $token"
    Accept                = 'application/vnd.github+json'
    'User-Agent'          = 'MiniTools-release-script'
    'X-GitHub-Api-Version' = '2022-11-28'
}

$payload = @{
    tag_name         = $tag
    target_commitish = 'main'
    name             = $title
    body             = $notes
    draft            = $false
    prerelease       = [bool]$Prerelease
} | ConvertTo-Json -Depth 5

$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$slug/releases" -Headers $headers -Method Post `
    -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
Write-Ok "Release 已创建：$($release.html_url)"

foreach ($asset in @(
        @{ Path = $exePath; Name = (Split-Path $exePath -Leaf) },
        @{ Path = $apkPath; Name = (Split-Path $apkPath -Leaf) })) {
    Write-Step ("上传 " + $asset.Name)
    $uri = "https://uploads.github.com/repos/$slug/releases/$($release.id)/assets?name=" + [uri]::EscapeDataString($asset.Name)
    $uploaded = Invoke-RestMethod -Uri $uri -Headers $headers -Method Post -ContentType 'application/octet-stream' -InFile $asset.Path
    Write-Ok ("{0}  {1:N1} MB  {2}" -f $uploaded.name, ($uploaded.size / 1MB), $uploaded.browser_download_url)
}

Write-Host ''
Write-Host "发布完成：$($release.html_url)" -ForegroundColor Green
Write-Warn2 '提醒：根 README / 各平台 README 里写死的版本号与验证记录可能需要手动更新（脚本不自动改文档）。'
