import sqlite3

from app.models.database.base_db import BaseDB

"""
CREATE TABLE IF NOT EXISTS inference_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defect_count INTEGER,
    original_image BLOB NOT NULL,
    annotated_image BLOB,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class InferenceDAO:
    """
    InferenceDAO 类，用于管理 inference_results 表的数据库操作。
    继承自 BaseDB。
    """
    def __init__(self):
        self.db = BaseDB()

    def add_inference_result(self, defect_count, original_image, annotated_image=None):
        """
        添加一条新的推理结果记录。
        original_image 和 annotated_image 应该是 BLOB 数据 (bytes)。
        """
        self.db.lock.acquire()  # 获取锁
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO inference_results (defect_count, original_image, annotated_image) VALUES (?, ?, ?)",
                (defect_count, sqlite3.Binary(original_image), sqlite3.Binary(annotated_image) if annotated_image else None)
            )
            inference_result_id = cursor.lastrowid # 获取最后插入行的 ID
            conn.commit()
            return inference_result_id
        finally:
            self.db.lock.release()  # 释放锁

    def get_inference_result_by_id(self, inference_result_id):
        """
        根据 ID 获取推理结果记录。
        返回字典形式的结果。
        """
        self.db.lock.acquire()
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            cursor.execute("SELECT id, defect_count, original_image, annotated_image, timestamp FROM inference_results WHERE id = ?", (inference_result_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'defect_count': row[1],
                    'original_image': row[2],
                    'annotated_image': row[3],
                    'timestamp': row[4]
                }
            # original_image 和 annotated_image 都是 JPEG 图像的 bytes 数据
            return None
        finally:
            self.db.lock.release()

    def fetch_all_inference_results(self):
        """
        获取所有推理结果记录。
        返回一个包含字典的列表。
        """
        self.db.lock.acquire()
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            cursor.execute("SELECT id, defect_count, timestamp FROM inference_results ORDER BY id DESC") # 默认按时间倒序排列，最新的结果在前面
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'defect_count': row[1],
                    'timestamp': row[2]
                })
            return results
        finally:
            self.db.lock.release()

    def fetch_inference_results_by_page(self, page=1, page_size=10, from_time=None, to_time=None):
        """
        分页获取推理结果记录，支持时间筛选。
        """
        self.db.lock.acquire()
        try:
            conn = self.db.conn
            cursor = conn.cursor()
            
            # 构建查询条件
            where_clause = ""
            params = []
            if from_time and to_time:
                where_clause = "WHERE timestamp BETWEEN ? AND ?"
                params.extend([from_time, to_time])
            
            # 获取总记录数
            cursor.execute(f"SELECT COUNT(*) FROM inference_results {where_clause}", params)
            total = cursor.fetchone()[0]
            
            # 获取分页数据
            offset = (page - 1) * page_size
            params.extend([page_size, offset])
            cursor.execute(
                f"""
                SELECT id, defect_count, timestamp 
                FROM inference_results 
                {where_clause}
                ORDER BY id DESC     -- 修改为按 id 降序排列
                LIMIT ? OFFSET ?
                """, 
                params
            )
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'defect_count': row[1], 
                    'timestamp': row[2]
                })
            return total, results
        finally:
            self.db.lock.release()