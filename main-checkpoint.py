import sys
import threading
import os
import uvicorn
# from PyQt6.QtWidgets import QApplication

from api.fastapi_app import app as fastapi_app
# from app.main_window import MainWindow


def get_resource_path(relative_path):
    """获取资源的绝对路径，兼容PyInstaller打包后的情况"""
    try:
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS # type: ignore
            print(f"[DEBUG] 使用PyInstaller打包路径: {base_path}")
        else:
            base_path = os.path.abspath(os.path.dirname(__file__))
            print(f"[DEBUG] 使用正常运行路径: {base_path}")
    except Exception as e:
        base_path = os.path.abspath(os.path.dirname(__file__))
        print(f"[DEBUG] 路径解析异常: {e}, 使用默认路径: {base_path}")
    
    return os.path.join(base_path, relative_path)


def run_server():
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=6006, log_level="info")
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
   # 后台启动 FastAPI 服务器
   # server_thread = threading.Thread(target=run_server, daemon=True)
   # server_thread.start()

    # 启动 PyQt 应用
   # qt_app = QApplication(sys.argv)
   # window = MainWindow()
   # window.show()
   # ret = qt_app.exec()

    # PyQt 退出后，服务器线程会自动结束（daemon thread）
   # sys.exit(ret)
    
    run_server()
