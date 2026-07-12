# model/database_manager.py
import sqlite3
import threading
import os
import sys

# 导入资源路径处理函数
try:
    from main import get_resource_path
except ImportError:
    # 如果无法导入，提供一个默认实现
    def get_resource_path(relative_path):
        try:
            # 使用hasattr检查_MEIPASS属性是否存在
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS # type: ignore
                print(f"[DEBUG] 使用PyInstaller打包路径: {base_path}")
            else:
                base_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
                print(f"[DEBUG] 使用正常运行路径: {base_path}")
        except Exception as e:

            base_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            print(f"[DEBUG] 路径解析异常: {e}, 使用默认路径: {base_path}")
        return os.path.join(base_path, relative_path)


class BaseDB:
    """
    数据库管理抽象基类，确保单例模式保证线程安全
    """
    _db_instance = None
    _lock = threading.Lock()

    def __init__(self):
        if not hasattr(self, 'conn'):
            with BaseDB._lock:
                if BaseDB._db_instance is None:
                    BaseDB._db_instance = self._create_db_connection()
                self.conn, self.lock = BaseDB._db_instance
    
    def _create_db_connection(self):
        # 使用跨平台的用户数据目录
        user_home = os.path.expanduser("~")
        app_data_dir = os.path.join(user_home, "SteelDefect", "data")
        os.makedirs(app_data_dir, exist_ok=True)
        
        db_path = os.path.join(app_data_dir, 'database.db')
        print(f"[INFO] 数据库路径: {db_path}")
        
        conn = sqlite3.connect(db_path, check_same_thread=False)        
        lock = threading.Lock()
        self._create_tables(conn)
        return conn, lock

    def _create_tables(self, conn):
        cursor = conn.cursor()
        sql_path = get_resource_path('resources/sql/init_database.sql')
        try:
            with open(sql_path, 'r', encoding='utf-8') as sql_file:
                sql_script = sql_file.read()
            cursor.executescript(sql_script)
            conn.commit()
        except Exception as e:
            print(f"[ERROR] 初始化数据库时出错: {e}")
            print(f"尝试读取的SQL文件路径: {sql_path}")
            raise

