from typing import List, Optional
from .base_db import BaseDB


class BillingDAO(BaseDB):
    """计费数据访问对象"""

    def get_model_price(self, model_name: str) -> Optional[float]:
        """获取模型价格"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT price_per_call FROM model_pricing WHERE model_name = ?
            """, (model_name,))
            
            row = cursor.fetchone()
            return row[0] if row else None

    def get_all_model_pricing(self, page: int = 1, page_size: int = 10) -> List[dict]:
        """获取所有模型定价（分页）"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # 获取分页数据
            offset = (page - 1) * page_size
            cursor.execute("""
                SELECT id, model_name, price_per_call, description, created_at
                FROM model_pricing ORDER BY model_name
                LIMIT ? OFFSET ?
            """, (page_size, offset))
            
            rows = cursor.fetchall()
            return [{
                'id': row[0],
                'model_name': row[1],
                'price': row[2],
                'description': row[3] or "",
                'created_at': row[4]
            } for row in rows]

    def update_model_price(self, model_name: str, price: float, description: str = "") -> bool:
        """更新模型价格"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE model_pricing 
                SET price_per_call = ?, description = ?
                WHERE model_name = ?
            """, (price, description, model_name))
            
            self.conn.commit()
            return cursor.rowcount > 0

    def add_model_pricing(self, model_name: str, price: float, description: str = "") -> bool:
        """添加新模型定价"""
        with self.lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO model_pricing (model_name, price_per_call, description)
                    VALUES (?, ?, ?)
                """, (model_name, price, description))
                self.conn.commit()
                return True
            except Exception:
                return False

    def record_api_call(self, user_id: int, token: str, model_name: str, endpoint: str, 
                       cost: float, image_count: int = 1, status: str = 'success', 
                       inference_result_id: Optional[int] = None) -> int:
        """记录API调用"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO api_calls 
                (user_id, token, model_name, endpoint, image_count, cost, status, inference_result_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, token, model_name, endpoint, image_count, cost, status, inference_result_id))
            
            call_id = cursor.lastrowid
            self.conn.commit()
            return call_id or 0

    def get_user_api_calls(self, user_id: int, page: int = 1, page_size: int = 10) -> List[dict]:
        """获取用户API调用记录（分页）"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # 获取分页数据
            offset = (page - 1) * page_size
            cursor.execute("""
                SELECT id, model_name, cost, status, image_count, timestamp
                FROM api_calls 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (user_id, page_size, offset))
            
            rows = cursor.fetchall()
            return [{
                'id': row[0],
                'model_name': row[1],
                'cost': row[2],
                'status': row[3],
                'image_count': row[4],
                'created_at': row[5]
            } for row in rows]

    def get_all_api_calls(self, page: int = 1, page_size: int = 10) -> List[dict]:
        """获取所有API调用记录（分页）"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # 获取分页数据
            offset = (page - 1) * page_size
            cursor.execute("""
                SELECT a.id, a.user_id, u.name as user_name, a.model_name, 
                       a.cost, a.status, a.timestamp, a.image_count
                FROM api_calls a
                LEFT JOIN users u ON a.user_id = u.id
                ORDER BY a.timestamp DESC
                LIMIT ? OFFSET ?
            """, (page_size, offset))
            
            rows = cursor.fetchall()
            return [{
                'id': row[0],
                'user_id': row[1],
                'user_name': row[2] or "未知用户",
                'model_name': row[3],
                'cost': row[4],
                'status': row[5],
                'created_at': row[6],
                'image_count': row[7] if len(row) > 7 else 1
            } for row in rows]

    def get_user_billing_summary(self, user_id: int) -> dict:
        """获取用户账单摘要"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # 总调用次数
            cursor.execute("SELECT COUNT(*) FROM api_calls WHERE user_id = ?", (user_id,))
            total_calls = cursor.fetchone()[0]
            
            # 总花费
            cursor.execute("SELECT SUM(cost) FROM api_calls WHERE user_id = ?", (user_id,))
            total_cost = cursor.fetchone()[0] or 0.0
            
            # 本月花费
            cursor.execute("""
                SELECT SUM(cost) FROM api_calls 
                WHERE user_id = ? AND DATE(created_at) >= DATE('now', 'start of month')
            """, (user_id,))
            monthly_cost = cursor.fetchone()[0] or 0.0
            
            # 今日花费
            cursor.execute("""
                SELECT SUM(cost) FROM api_calls 
                WHERE user_id = ? AND DATE(created_at) = DATE('now')
            """, (user_id,))
            daily_cost = cursor.fetchone()[0] or 0.0
            
            # 按模型统计
            cursor.execute("""
                SELECT model_name, COUNT(*) as calls, SUM(cost) as cost
                FROM api_calls 
                WHERE user_id = ?
                GROUP BY model_name
                ORDER BY cost DESC
            """, (user_id,))
            
            model_stats = []
            for row in cursor.fetchall():
                model_stats.append({
                    'model_name': row[0],
                    'calls': row[1],
                    'cost': row[2]
                })
            
            return {
                'total_calls': total_calls,
                'total_cost': total_cost,
                'monthly_cost': monthly_cost,
                'daily_cost': daily_cost,
                'model_stats': model_stats
            }

    def get_recharge_records(self, user_id: int) -> List[dict]:
        """获取用户充值记录"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, amount, balance_before, balance_after, description, timestamp
                FROM recharge_records 
                WHERE user_id = ?
                ORDER BY timestamp DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            return [{
                'id': row[0],
                'amount': row[1],
                'balance_before': row[2],
                'balance_after': row[3],
                'description': row[4],
                'created_at': row[5]
            } for row in rows]

    def get_statistics_summary(self) -> dict:
        """获取统计摘要"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # 总用户数
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # 总调用次数
            cursor.execute("SELECT COUNT(*) FROM api_calls")
            total_calls = cursor.fetchone()[0]
            
            # 总收入
            cursor.execute("SELECT SUM(cost) FROM api_calls")
            total_revenue = cursor.fetchone()[0] or 0.0
            
            # 活跃用户数（有过调用记录的用户）
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM api_calls")
            active_users = cursor.fetchone()[0]
            
            # 按模型统计
            cursor.execute("""
                SELECT model_name, COUNT(*) as calls, SUM(cost) as revenue
                FROM api_calls 
                GROUP BY model_name
                ORDER BY revenue DESC
            """)
            
            model_stats = []
            for row in cursor.fetchall():
                model_stats.append({
                    'model_name': row[0],
                    'calls': row[1],
                    'revenue': row[2]
                })
            
            return {
                'total_users': total_users,
                'total_calls': total_calls,
                'total_revenue': total_revenue,
                'active_users': active_users,
                'model_stats': model_stats
            }

    def get_daily_statistics(self, days: int = 7) -> List[dict]:
        """获取每日统计（最近N天）"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT DATE(timestamp) as date, 
                       COUNT(*) as calls, 
                       SUM(cost) as revenue,
                       COUNT(DISTINCT user_id) as active_users
                FROM api_calls 
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """.format(days))
            
            return [{
                'date': row[0],
                'calls': row[1],
                'revenue': row[2],
                'active_users': row[3]
            } for row in cursor.fetchall()]

    def delete_model_pricing(self, model_name: str) -> bool:
        """删除模型定价"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM model_pricing WHERE model_name = ?", (model_name,))
            self.conn.commit()
            return cursor.rowcount > 0
