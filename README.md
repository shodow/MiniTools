# MiniTools

一个跨平台的小工具集合：主界面是一组功能卡片，点进去就是用对应功能的页面。
同一个仓库里放各平台的客户端，界面与功能保持一致。

## 现有平台

| 目录 | 平台 | 形态 | 状态 |
|---|---|---|---|
| [`windesktop/`](windesktop/README.md) | Windows 10/11 | Python + PySide6 桌面程序，Inno Setup 安装包 | ✅ 已发布 2.0.0 |
| [`android/`](android/README.md) | Android 7.0+ (API 24+) | Kotlin + Jetpack Compose，APK | ✅ 已在真机验证（2.0.0） |
| `harmonyos/`、`ios/` | — | — | 预留 |

每个平台目录都自带构建脚本和 README，互不影响。`windesktop` 有 PyInstaller + Inno Setup 打包流程；`android` 用 Gradle 直接出 APK，验证走真机 adb（本机模拟器不可用，原因见 [android/README.md](android/README.md)）。

## 功能（两平台对齐）

### 1. PDF 转图片
把 PDF 的每一页导出成 PNG / JPG，支持整个文件夹批量转换，输出命名 `原文件名_页码`。

### 2. 图片加水印
给 PNG / JPG 平铺文字水印，支持中文；可调透明度、字号、间距、倾斜角度，实时预览。

## 设计约定（两平台共用）

这些参数在两端必须保持一致，改动请同时更新两边：

| 参数 | 默认值 | 取值范围 |
|---|---|---|
| 水印透明度 | 75% | 0–100 |
| 水印字号 | 20 px | 6–400 |
| 水印间距 | 60 px | 0–1000 |
| 倾斜角度 | 45° | 0–90 |
| PDF 渲染 DPI | 200 | 48–1200 |
| 页码补零 | 3 位 | 0–6 |
| 输出目录 | 同名子文件夹（`<名字>_images/`、`<名字>_watermark/`） | 原目录 / 子文件夹 / 自定义 |
| 重名处理 | 覆盖 | 覆盖 / 跳过 / 自动重命名 |

配色：主色 `#2563EB`，PDF 卡 `#2563EB`、水印卡 `#0EA5E9`，背景 `#F4F6F9`，卡片白底圆角 14 px。

## 目录结构

```
MiniTools/
├─ README.md              本文件：总览、功能、共用设计约定
├─ .gitignore
├─ windesktop/            Windows 桌面版（详见该目录 README）
│  ├─ app/                程序源码
│  ├─ build/              PyInstaller / Inno Setup 打包脚本
│  ├─ tests/              引擎单测 + 端到端流程 + 界面截图
│  └─ dist/               打包产物（未提交）
└─ android/               Android 版（详见该目录 README）
```
