# MiniTools

Windows 桌面小工具集合：一个主窗口、一组功能卡片，点进去就是对应功能。
目前包含 **PDF 转图片**、**图片加水印**（都支持整目录批量）。

- UI：Python 3.12 + PySide6（Qt 6）
- PDF 渲染：pypdfium2（PDFium，Apache-2.0 / BSD-3）
- 图片处理：Pillow
- 打包：PyInstaller（onedir）+ Inno Setup 6（安装包、桌面快捷方式）

## 界面

主窗口是卡片网格，点卡片进入功能页，按 `← 返回` 或 `Esc` 回到首页。
首页搜索框可以按名称 / 关键词过滤卡片。

## 功能：PDF 转图片

- 拖拽或选择 PDF 文件，也可以直接选整个文件夹（可选是否含子文件夹）
- 每页导出为 PNG 或 JPG，文件名格式 `原文件名_页码`（默认补 3 位：`报告_001.png`）
- 分辨率可调（默认 200 DPI），JPG 质量可调
- 页面范围：留空为全部，支持 `1-5,8,10-`
- 输出位置：PDF 原目录 / 同名子文件夹（默认）/ 自定义目录
- 已存在文件：覆盖 / 跳过 / 自动重命名
- 后台转换（PDFium 全局串行，最稳），实时进度、可取消、失败文件单独提示
- 单个文件失败不会中断整批任务

## 安装

运行 `dist\MiniTools-Setup-1.1.0.exe`（约 26 MB）：

- 默认按当前用户安装，**不需要管理员权限**，目录 `%LOCALAPPDATA%\Programs\MiniTools`
- 向导里勾选“创建桌面快捷方式”（默认已勾选），同时创建开始菜单项
- 卸载走“设置 → 应用”或安装目录里的 `unins000.exe`

### 遇到这两种提示怎么办

1. **“Windows 已保护你的电脑”**（SmartScreen）
   安装包没有代码签名证书，属于正常提示。点「更多信息」→「仍要运行」即可。
   想彻底消掉需要代码签名证书或 Azure Trusted Signing 之类的签名服务。

2. **“安装程序无法创建目录 …is-xxxx.tmp。错误 5: 拒绝访问”**
   运行位置受限导致的：从受沙箱 / 受控目录（例如项目里的 `dist\`）直接双击，
   安装程序无权在 `%TEMP%` 或 `%LOCALAPPDATA%\Programs` 下建目录。
   **把安装包复制到桌面或“下载”文件夹再运行即可**；
   `build\build_installer.ps1` 打完包会自动复制一份到 `%USERPROFILE%\Downloads`。

## 功能：图片加水印

- 拖拽或选择 PNG / JPG 图片，也可以直接选整个文件夹（可选是否含子文件夹）
- 平铺文字水印，**支持中文**（自动调用系统里的微软雅黑 / 黑体等字体）
- 可调参数：透明度（默认 75%）、文字大小（默认 20 px）、水印间距（默认 60 px）、倾斜角度（默认 45°）
- 文字颜色：白色 / 黑色 / 浅灰 / 深灰 / 自定义色；可开关描边（浅色背景上也看得清）
- 右侧实时预览（用第一张图片按比例缩放渲染，所见即所得）
- 输出格式：保持原格式 / PNG / JPG（JPG 质量可调）
- 输出位置：原目录 / 同名子文件夹（默认 `<图片名>_watermark/`）/ 自定义目录
- 已存在文件：覆盖 / 跳过 / 自动重命名；后台多线程处理、进度条、可取消、失败单独提示

## 目录结构

```
app/
  main.py                 入口
  core/
    registry.py           工具注册表（自动扫描 app/tools/*/tool.py）
    settings.py           QSettings 封装（记住上次参数）
    tasks.py              QThread 后台任务基类
    paths.py              资源路径（源码 / 打包两种模式）
  ui/
    main_window.py        主窗口 + 页面栈
    home_page.py          卡片首页 + 搜索
    card_widget.py        卡片控件
    flow_layout.py        自动换行布局
    tool_page.py          工具页面外壳（返回按钮 + 标题）
    widgets.py            共用小部件（拖拽区、大小格式化）
    theme.py              全局 QSS
    icons.py              QPainter 现画图标
  tools/
    pdf2img/
      tool.py             卡片元信息（ToolSpec）
      page.py             功能页面
      converter.py        纯 Python 转换引擎（无 Qt 依赖，可单测）
    imgwatermark/
      tool.py             卡片元信息
      page.py             功能页面（含实时预览）
      converter.py        Pillow 水印引擎（无 Qt 依赖，可单测）
build/
  MiniTools.spec           PyInstaller 配置
  make_icon.py            生成 app.ico
  build.ps1               打包 exe
  build_installer.ps1     打包安装包
  installer/MiniTools.iss  Inno Setup 脚本
tests/
  test_converter.py       转换引擎自测
  test_watermark.py       水印引擎自测
  test_flow.py            PDF 页端到端流程
  test_flow_watermark.py  水印页端到端流程
  smoke_ui.py             离屏界面截图
```

## 开发运行

```powershell
# 安装依赖（用哪个环境就换成哪个 python）
C:\Users\ricar\miniconda3\envs\WinTools\python.exe -m pip install -r requirements.txt

# 启动
.\run.ps1
```

## 测试

```powershell
$py = "C:\Users\ricar\miniconda3\envs\WinTools\python.exe"
& $py tests\test_converter.py          # PDF 转换引擎用例
& $py tests\test_watermark.py          # 水印引擎用例
& $py tests\test_flow.py               # PDF 页：点按钮转换 / 取消
& $py tests\test_flow_watermark.py     # 水印页：预览 + 批量处理
& $py tests\smoke_ui.py                # 界面截图 → tests\_out\
```

打包后的自检（确认 exe 里 Qt / PDFium / Pillow 都能加载）：

```powershell
.\dist\MiniTools\MiniTools.exe --selftest
# 结果同时写入 %TEMP%\MiniTools-selftest.log
```

## 打包

需要先装 [Inno Setup 6](https://jrsoftware.org/isdl.php)（`winget install -e --id JRSoftware.InnoSetup`）。

```powershell
.\build\build.ps1             # 只出 dist\MiniTools\MiniTools.exe（onedir，约 73 MB）
.\build\build_installer.ps1   # 出 dist\MiniTools-Setup-1.1.0.exe
```

安装包默认按用户安装（不需要管理员权限），安装目录 `%LOCALAPPDATA%\Programs\MiniTools`，
安装向导里勾选 “创建桌面快捷方式” 即创建桌面快捷方式（默认勾选）。
`build\installer\ChineseSimplified.isl` 是 Inno 官方简体中文语言文件（随仓库附带，离线也能编译中文向导）。

## 新增一个工具

1. 新建 `app/tools/<id>/tool.py`，参考 `pdf2img/tool.py` 声明一个 `ToolSpec`；
2. 页面类继承 `app.ui.tool_page.ToolPage`，把控件放进 `self.body`；
3. 在 `app/tools/__init__.py` 的 `TOOL_MODULES` 里加一行模块路径（PyInstaller 靠它把模块打进 exe）。

不需要改主窗口，也不需要改注册表 —— 卡片会按 `order` 自动排版。

## 许可

本项目代码可自行使用与修改。第三方组件：PySide6（LGPLv3）、PDFium / pypdfium2（Apache-2.0 / BSD-3）、
Pillow（HPND）、PyInstaller（GPLv2 + bootloader 例外）。若要分发安装包，请保留以上第三方许可声明。
