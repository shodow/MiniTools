# MiniTools for Android

Kotlin + Jetpack Compose 实现的 Android 客户端，功能与 Windows 桌面版一致：

- **PDF 转图片**：用系统自带的 `PdfRenderer`（零第三方依赖）把每页渲染成 PNG / JPG，命名 `原文件名_页码`
- **图片加水印**：`Canvas` 平铺旋转文字水印，支持中文；透明度 / 字号 / 间距 / 角度 / 颜色 / 描边与桌面版同一套默认值，带实时预览

## 环境要求

| 项 | 版本 |
|---|---|
| JDK | 21（用 Android Studio 自带的 JBR） |
| Android SDK | platform 35、build-tools 35.x |
| Gradle | 8.11.1（`gradlew` 已带 wrapper） |
| AGP / Kotlin | 8.7.3 / 2.0.21 |
| minSdk / targetSdk | 24 / 35 |

`local.properties` 里的 `sdk.dir` 指向本机 SDK（不要提交到仓库）。

## 构建

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
cd android
.\gradlew.bat assembleDebug
# 产物：app\build\outputs\apk\debug\app-debug.apk
```

安装到模拟器或真机：

```powershell
adb install -r app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.ricar.minitools/.MainActivity
```

## 输出位置

- Android 10+：`相册 / Pictures/MiniTools`
- Android 7–9：`Android/data/com.ricar.minitools/files/Pictures/MiniTools`

## 目录

```
android/
├─ app/src/main/java/com/ricar/minitools/
│  ├─ MainActivity.kt
│  ├─ ui/            App 导航、首页卡片、主题
│  ├─ tools/         Pdf2Img.kt / Watermark.kt（引擎 + 页面）
│  └─ util/          MediaSaver（保存到相册 / 应用目录）
├─ app/src/main/res/ 图标、字符串、主题
└─ tools/make_icons.py  生成启动图标
```

## 真机调试（本机唯一验证方式）

一条命令装包 + 启动（可选截图）：

```powershell
cd android\tools
.\install_to_phone.ps1 -Screenshot
```

手动流程：

```powershell
# 1) 手机开启「开发者选项 → USB 调试」，插线后确认连接
adb devices

# 2) 装包并启动
adb install -r app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.ricar.minitools/.MainActivity

# 3) 需要截图时
adb exec-out screencap -p > shot.png

# 4) 无线调试（Android 11+，手机「无线调试」里拿 ip:port 和配对码）
adb pair <ip:port>
adb connect <ip:port>
```

## 验证记录

| 日期 | 平台 | 内容 | 结果 |
|---|---|---|---|
| 2026-11-26 | Windows 11 | 桌面版 2.0.0 自检 + 4 套测试（PDF 23 项 / 水印 28 项 / 2 个端到端） | 通过 |
| 2026-11-26 | 真机 Android | 安装 `app-debug.apk`，PDF 转图片 + 图片加水印 | 功能正常 |
| 2026-11-26 | 本机模拟器 | 多种配置尝试（含重装 Emulator、720×1280 轻量 AVD、headless） | 不可用，已放弃 |

## 已知取舍

- 图片解码上限 4096 px（长边），避免大图 OOM；需要原尺寸可后续改成分块流式处理
- 批量处理为串行（手机内存有限，串行最稳）
- 暂未做自定义输出目录 / 重名策略（统一输出到 Pictures/MiniTools，重名由系统自动加后缀）

## 低配机器（8 GB 内存 / N100 这类 4 核小主机）

Android Studio + 模拟器同时开，在这类机器上基本会把内存和 CPU 顶满。按下面的顺序调，能省一半资源：

### 1. Android Studio 本身

| 设置 | 位置 | 建议值 |
|---|---|---|
| 堆内存 | Help → Change Memory Settings | **1536 MB**（默认 2048 起，8 GB 机器别超 2 GB） |
| 省电模式 | File → Power Save Mode | 打开（关掉实时语法检查/高亮） |
| 关闭不用的插件 | Settings → Plugins | Firebase、Gemini/AI、Kotlin Notebook、CVS/SVN 等 |
| 关闭 Live Edit / Apply Changes | Settings → Build → Deployment | 关 |
| 不要内嵌模拟器 | Settings → Tools → Emulator | 取消 “Launch in a tool window” |
| 关闭 Gradle 常驻 | 命令行 `.\gradlew.bat --stop` | 构建完执行，能立刻回收 1–1.5 GB |

`gradle.properties` 已经按低配调过（堆 1.5 GB、worker 2、关闭并行工程构建），构建时**别同时开 Studio 跑索引**。

### 2. Windows 侧（收益很大）

- Windows 安全中心 → 病毒和威胁防护 → 排除项，加上：
  `MiniTools\android`、`%USERPROFILE%\.gradle`、`%LOCALAPPDATA%\Android\Sdk`、`%USERPROFILE%\.android`
- 虚拟内存（页面文件）调到固定 16 GB（在 SSD 上），避免 8 GB 物理内存被挤爆后卡死
- 电源计划用“平衡/高性能”，关掉窗口透明和动画
- 构建/启动模拟器时别开浏览器、微信这类常驻大户

### 3. 模拟器：本机已放弃使用

**结论（2026-11-26 记录，这台 Intel N100 / 8 GB 的机器）：**

- Android Studio 里能启动，但整机 CPU、内存瞬间打满，系统卡到无法操作，只能强杀；
- 命令行 / `-no-window` 启动直接失败（qemu 后端退出，错误码 `0xC0000135` DLL 加载失败），
  重装 Android Emulator 组件后依旧；
- AVD 已降到 720×1280 @280dpi + 1.5 GB RAM + 2 核，仍然不可用。

**所以本机开发流程固定为：一律真机 adb 验证，不再启动模拟器。**

`tools\tune_avd.ps1`、`tools\run_emulator.ps1` 保留在仓库里，换到内存更大的机器时可以直接用：

```powershell
cd android\tools
.\tune_avd.ps1                    # 720x1280 @280dpi / 1.5 GB / host GPU（会先备份 config.ini）
.\run_emulator.ps1 -Headless      # 无窗口启动，配合 adb 截图
```


### 4. 其实不需要 Studio

本项目用命令行 Gradle 就能编：

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
cd android
.\gradlew.bat assembleDebug --offline    # 依赖已缓存后加 --offline 更快
```

Studio 只在需要 AVD Manager 或布局预览时再开。