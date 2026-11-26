"""最小复现：只创建应用与主窗口，检查偶发崩溃。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import create_app  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "full"
    print(f"[{stage}] start", flush=True)
    app = create_app([])
    print("app ok", flush=True)
    if stage in ("window", "full"):
        window = MainWindow()
        print("window ok", flush=True)
        window.show()
        app.processEvents()
        print("show ok", flush=True)
        if stage == "full":
            window.open_tool("pdf2img")
            app.processEvents()
            print("tool ok", flush=True)
        window.close()
    app.processEvents()
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
