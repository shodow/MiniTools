# MiniTools 工作区约定（给 AI 助手）

## 这是什么

跨平台小工具集合：主界面一组功能卡片，点进去是对应功能页。**同一仓库两套客户端**，功能与参数必须保持一致：

| 目录 | 技术栈 | 产物 | 状态 |
|---|---|---|---|
| `windesktop/` | Python 3.12 + PySide6 + pypdfium2 + Pillow | PyInstaller onedir + Inno Setup 安装包 | 已发布 2.0.0 |
| `android/` | Kotlin + Jetpack Compose（minSdk 24 / targetSdk 35） | APK | 已真机验证 2.0.0 |

动手前先读：根 [`README.md`](README.md)（功能 + 两平台共用的「设计约定」参数表）、[`windesktop/README.md`](windesktop/README.md)、[`android/README.md`](android/README.md)。这三个文件是事实来源，不要凭记忆改参数。

## 本机环境（绝对路径，不要重新探测或另建环境）

| 用途 | 路径 |
|---|---|
| windesktop 的唯一 Python 环境 | `C:\Users\ricar\miniconda3\envs\WinTools\python.exe` |
| Android 构建 JDK | `C:\Program Files\Android\Android Studio\jbr` |
| Inno Setup 编译器 | `C:\Users\ricar\AppData\Local\Programs\Inno Setup 6\ISCC.exe` |

conda 环境名仍叫 **WinTools**（历史名）。项目已改名 MiniTools，**不要因为名字对不上就重建环境或重装依赖**，直接用上表路径。

## 常用命令（在仓库根执行）

windesktop 开发与测试：

```powershell
$py = "C:\Users\ricar\miniconda3\envs\WinTools\python.exe"

.\windesktop\run.ps1                      # 启动应用
& $py windesktop\tests\test_converter.py  # PDF 转换引擎
& $py windesktop\tests\test_watermark.py  # 水印引擎
& $py windesktop\tests\test_flow.py       # PDF 页端到端
& $py windesktop\tests\test_flow_watermark.py
& $py windesktop\tests\smoke_ui.py        # 离屏截图 → windesktop\tests\_out\
```

windesktop 打包：

```powershell
.\windesktop\build\build.ps1              # → windesktop\dist\MiniTools\MiniTools.exe
.\windesktop\build\build_installer.ps1    # → dist\MiniTools-Setup-<版本>.exe，并自动复制到 Downloads
```

Android：

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
cd android
.\gradlew.bat assembleDebug               # → app\build\outputs\apk\debug\app-debug.apk
cd tools
.\install_to_phone.ps1 -Screenshot        # 装到真机 + 启动 + 截图
```

## 硬性约定

1. **双端参数必须同步**：透明度 75% / 字号 20 px / 间距 60 px / 角度 45° / PDF 渲染 DPI 200 / 页码补零 3 位 / 默认输出同名子文件夹 / 重名覆盖。改任何一端都要同步另一端，并更新根 README 的参数表。
2. **输出命名固定** `原文件名_页码`（默认补 3 位，如 `报告_001.png`），不要改格式。
3. **引擎层不依赖 Qt**：`windesktop/app/tools/*/converter.py` 必须能脱离 Qt 单测；Qt 相关逻辑放 `page.py`。
4. **改完必须验证**：引擎改动跑对应单测；UI 改动跑 `smoke_ui.py` 并看截图；Android 改动只能真机验证——本机模拟器跑不起来，别再尝试。
5. **安装包验证**：`build_installer.ps1` 打完包必须从 `Downloads`（或桌面）双击运行。从项目目录直接运行会报「错误 5: 拒绝访问」，这是路径受限不是 bug；未签名程序首次运行有 SmartScreen 提示属正常。
6. **版本号两处同步**：`windesktop/build/installer/MiniTools.iss` 的 `MyAppVersion` 与 `android/app/build.gradle.kts` 的 `versionName` / `versionCode`（当前 2.0.0）。
7. **不提交构建产物**：`.gitignore` 已忽略 `windesktop/dist/`、`windesktop/build/work/`、`windesktop/tests/_out/`、`android/app/build/`、`android/local.properties`。不要为了跑测试把大文件塞进仓库。
8. **不擅自删除或改名既有文件**：尤其 `windesktop/dist/` 里的历史安装包、`build/work/` 的旧产物。需要清理时先列清单（路径 / 原因 / 命令 / 可恢复性），由用户确认——沿用 `~/.dsh/AGENTS.md` 的删除规则。

## 历史遗留（避免困惑）

- 仓库前身叫 **WinTools**：`windesktop/dist/WinTools-*`、`build/work/WinTools/`、`build/install-test/WinTools.exe`、`wintools-selftest*` 都是旧名产物，保留即可；**新代码一律 MiniTools 命名**。
- Android 包名保持 `com.ricar.minitools`，桌面端 exe 名 `MiniTools.exe`；改名会破坏已发布版本的升级/数据路径。
- 模拟器在本机不可用（8 GB 内存机器，README 有完整尝试记录），Android 验证一律走真机 adb。

## 沟通

用中文。结论先给，再展开细节；改动完成后说明「改了什么、怎么验证的、还剩什么」。
