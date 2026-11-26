"""工具包集合。

新增工具时在这里登记模块路径（打包后 PyInstaller 只保留静态可分析的导入，
所以必须显式列出；开发模式另有一套 pkgutil 自动扫描作为补充）。
"""

TOOL_MODULES = [
    "app.tools.pdf2img.tool",
    "app.tools.imgwatermark.tool",
]
