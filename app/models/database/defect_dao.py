from app.models.database.base_db import BaseDB
"""
CREATE TABLE IF NOT EXISTS defect_counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inference_result_id INTEGER,
    defect_name TEXT,
    count INTEGER
);
"""

class DefectDAO:
    """
    DefectDAO 类，用于管理 defect_counts 表的数据库操作。
    继承自 BaseDB。
    """
    def __init__(self):
        self.db = BaseDB()

    def add_defect_count(self, inference_result_id, defect_name, count):
        """
        添加一条新的缺陷计数记录。
        """
        self.db.lock.acquire()  # 获取锁
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO defect_counts (inference_result_id, defect_name, count) VALUES (?, ?, ?)",
                (inference_result_id, defect_name, count)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            self.db.lock.release()  # 释放锁



    def get_defect_counts_by_inference_id(self, inference_result_id):
        """
        根据推理结果ID获取所有缺陷计数记录。
        返回一个包含字典的列表。
        """
        self.db.lock.acquire()
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, defect_name, count FROM defect_counts WHERE inference_result_id = ?",
                (inference_result_id,)
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'defect_name': row[1],
                    'count': row[2]
                })
            return results
        finally:
            self.db.lock.release()

    def get_defect_counts_by_name(self, defect_name):
        """
        根据缺陷名称获取所有缺陷计数记录。
        返回一个包含字典的列表。
        """
        self.db.lock.acquire()
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, inference_result_id, count FROM defect_counts WHERE defect_name = ?",
                (defect_name,)
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'inference_result_id': row[1],
                    'count': row[2]
                })
            return results
        finally:
            self.db.lock.release()

    def get_defect_statistics(self):
        """
        获取所有缺陷类型的统计信息。
        返回一个包含字典的列表，每个字典包含缺陷名称和总数。
        """
        self.db.lock.acquire()
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            cursor.execute(
                "SELECT defect_name, SUM(count) as total_count FROM defect_counts GROUP BY defect_name"
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    'defect_name': row[0],
                    'total_count': row[1]
                })
            return results
        finally:
            self.db.lock.release()

    def fetch_defect_counts_by_inference_id(self, inference_result_id):
        """
        根据 inference_result_id 获取缺陷计数记录。
        返回一个包含字典的列表。
        """
        self.db.lock.acquire()  # 获取锁
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, defect_name, count FROM defect_counts WHERE inference_result_id = ?",
                (inference_result_id,)
            )
            rows = cursor.fetchall()
            defect_counts = []
            for row in rows:
                defect_counts.append({
                    'id': row[0],
                    'defect_name': row[1],
                    'count': row[2]
                })
            return defect_counts
        finally:
            self.db.lock.release()  # 释放锁